import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

from aio_pika import DeliveryMode, IncomingMessage, Message, connect_robust
from pydantic import ValidationError

from app.core.config import (
    DETECTOR_REQUEST_CMD,
    DETECTOR_RESPONSE_CMD,
    RABBITMQ_ENABLED,
    RABBITMQ_RECONNECT_SECONDS,
    RABBITMQ_RESPONSE_APP,
    RABBITMQ_URL,
    TOXIC_COMMENT_DETECTOR_QUEUE,
    UPDATE_VIDEO_QUEUE,
)
from app.schemas.rabbitmq import (
    DetectorCommentMessage,
    DoneDetectorCommentData,
    DoneDetectorCommentMessage,
)
from app.services.detector import extract_toxic_spans, run_inference

logger = logging.getLogger(__name__)

TOXIC_SPEECH_DETECTION_TASK = "toxic-speech-detection"
HATE_SPANS_DETECTION_TASK = "hate-spans-detection"


class RabbitMQCommentDetector:
    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._stop_event: Optional[asyncio.Event] = None
        self._connection: Optional[Any] = None
        self._channel: Optional[Any] = None

    async def start(self) -> None:
        if not RABBITMQ_ENABLED:
            logger.info("RabbitMQ consumer is disabled.")
            return

        if self._task is not None and not self._task.done():
            return

        logger.info("Starting RabbitMQ comment detector consumer.")
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(
            self._run(),
            name="rabbitmq-comment-detector",
        )

    async def stop(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()

        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        await self._close_resources()
        self._stop_event = None

    async def _run(self) -> None:
        while self._stop_event is not None and not self._stop_event.is_set():
            try:
                await self._connect_and_consume()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "RabbitMQ consumer failed. Reconnecting in %.1f seconds.",
                    RABBITMQ_RECONNECT_SECONDS,
                )
                await self._wait_before_reconnect()

    async def _connect_and_consume(self) -> None:
        stop_event = self._require_stop_event()

        try:
            logger.info("Connecting to RabbitMQ at %s.", self._safe_rabbitmq_endpoint())
            self._connection = await connect_robust(RABBITMQ_URL)
            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=1)

            request_queue = await self._channel.declare_queue(
                TOXIC_COMMENT_DETECTOR_QUEUE,
                durable=True,
            )
            await self._channel.declare_queue(UPDATE_VIDEO_QUEUE, durable=True)

            await request_queue.consume(self._handle_message)
            logger.info(
                "RabbitMQ consumer is listening on queue %s.",
                TOXIC_COMMENT_DETECTOR_QUEUE,
            )

            await stop_event.wait()
        finally:
            await self._close_resources()

    async def _handle_message(self, message: IncomingMessage) -> None:
        try:
            logger.info(
                "Received RabbitMQ message. queue=%s delivery_tag=%s",
                TOXIC_COMMENT_DETECTOR_QUEUE,
                message.delivery_tag,
            )
            payload = json.loads(message.body.decode("utf-8"))
            await self._process_payload(payload)
        except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
            logger.warning("Discarding invalid RabbitMQ message: %s", exc)
            await message.ack()
        except Exception:
            logger.exception("Failed to process RabbitMQ message.")
            await message.nack(requeue=True)
        else:
            await message.ack()
            logger.info(
                "Acknowledged RabbitMQ message. delivery_tag=%s",
                message.delivery_tag,
            )

    async def _process_payload(self, payload: Dict[str, Any]) -> None:
        detector_message = DetectorCommentMessage.model_validate(payload)
        if detector_message.cmd != DETECTOR_REQUEST_CMD:
            logger.info("Ignoring RabbitMQ cmd %s.", detector_message.cmd)
            return

        content = detector_message.data.content
        comment_id = detector_message.data.comment_id
        msg_type = detector_message.data.type
        logger.info("Detecting toxic comment. comment_id=%s type=%s", comment_id, msg_type)
        toxicity_result = await asyncio.to_thread(
            run_inference,
            content,
            TOXIC_SPEECH_DETECTION_TASK,
        )

        if toxicity_result.strip().lower() != "toxic":
            logger.info(
                "Comment %s detected as %s. No update message sent.",
                comment_id,
                toxicity_result,
            )
            return

        logger.info("Comment %s detected as toxic. Detecting hate spans.", comment_id)
        detected_content = await asyncio.to_thread(
            run_inference,
            content,
            HATE_SPANS_DETECTION_TASK,
        )
        toxic_spans = extract_toxic_spans(detected_content)
        await self._publish_detection_result(comment_id, toxic_spans, msg_type)

    async def _publish_detection_result(
        self,
        comment_id: Union[int, str],
        toxic_spans: List[Dict[str, int]],
        msg_type: int,
    ) -> None:
        if self._channel is None:
            raise RuntimeError("RabbitMQ channel is not available.")

        response_message = DoneDetectorCommentMessage(
            cmd=DETECTOR_RESPONSE_CMD,
            app=RABBITMQ_RESPONSE_APP,
            data=DoneDetectorCommentData(
                comment_id=comment_id,
                toxic_spans=toxic_spans,
                type=msg_type,
            ),
        )
        body = json.dumps(
            response_message.model_dump(mode="json"),
            ensure_ascii=False,
        ).encode("utf-8")
        message = Message(
            body=body,
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
        )
        await self._channel.default_exchange.publish(
            message,
            routing_key=UPDATE_VIDEO_QUEUE,
        )
        logger.info("Published toxic comment detection result for %s.", comment_id)

    async def _wait_before_reconnect(self) -> None:
        if self._stop_event is None:
            return

        try:
            await asyncio.wait_for(
                self._stop_event.wait(),
                timeout=RABBITMQ_RECONNECT_SECONDS,
            )
        except asyncio.TimeoutError:
            pass

    async def _close_resources(self) -> None:
        if self._channel is not None:
            try:
                await self._channel.close()
            except Exception:
                logger.warning("Failed to close RabbitMQ channel.", exc_info=True)
            finally:
                self._channel = None

        if self._connection is not None:
            try:
                await self._connection.close()
            except Exception:
                logger.warning("Failed to close RabbitMQ connection.", exc_info=True)
            finally:
                self._connection = None

    def _require_stop_event(self) -> asyncio.Event:
        if self._stop_event is None:
            raise RuntimeError("RabbitMQ consumer has not been started.")
        return self._stop_event

    def _safe_rabbitmq_endpoint(self) -> str:
        parsed_url = urlparse(RABBITMQ_URL)
        host = parsed_url.hostname or "unknown-host"
        port = parsed_url.port or 5672
        return f"{parsed_url.scheme}://{host}:{port}"


rabbitmq_comment_detector = RabbitMQCommentDetector()
