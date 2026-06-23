from typing import Dict, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class BaseMessage(BaseModel, Generic[DataT]):
    cmd: str
    app: Optional[str] = None
    data: DataT


class DetectorCommentData(BaseModel):
    content: str = Field(..., min_length=1)
    comment_id: Union[int, str]
    type: int = Field(..., description="Type code as integer")


class DoneDetectorCommentData(BaseModel):
    comment_id: Union[int, str]
    toxic_spans: List[Dict[str, int]]
    type: int = Field(..., description="Type code as integer")


class DetectorCommentMessage(BaseMessage[DetectorCommentData]):
    pass


class DoneDetectorCommentMessage(BaseMessage[DoneDetectorCommentData]):
    pass
