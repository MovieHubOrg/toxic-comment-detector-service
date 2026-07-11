# Toxic Comment Detector Service

## Mo ta ngan

Toxic Comment Detector Service la service phu trach tu dong phat hien va xu ly cac binh luan co dau hieu doc hai hoac khong phu hop trong he thong. Service su dung mo hinh ngon ngu ViHateT5 de phan tich noi dung tieng Viet va tra ve ket qua phan loai. Ket qua duoc cung cap qua REST API hoac xu ly bat dong bo thong qua RabbitMQ.

## Vai tro trong he thong

Service nay dong vai tro nhu mot thanh phan kiem duyet noi dung tu dong. Khi nguoi dung gui binh luan, he thong co the goi API truc tiep hoac gui message qua RabbitMQ de service kiem tra noi dung. Neu phat hien binh luan doc hai, service tra ve vi tri cac doan toxic de backend co the highlight, an, canh bao hoac xu ly theo nghiep vu.

## Chuc nang chinh

- Phat hien binh luan co tinh toxic hoac khong phu hop.
- Phan loai noi dung theo cac task cua mo hinh ViHateT5.
- Trich xuat vi tri cac cum tu toxic trong binh luan.
- Ho tro goi truc tiep qua REST API va xu ly bat dong bo qua RabbitMQ.
- Ho tro chay tren GPU CUDA neu moi truong co san.

## Luong xu ly tom tat

1. Nhan noi dung binh luan tu API hoac RabbitMQ.
2. Chuan hoa mot so tu viet khong dau hoac teencode.
3. Dua noi dung vao mo hinh ViHateT5 de du doan.
4. Neu phat hien toxic, trich xuat `toxic_spans` gom vi tri bat dau va ket thuc cua doan can xu ly.
5. Tra ket qua ve client hoac publish message cho backend.

## Cau hoi thuong gap khi trinh bay

**1. Service nay dung de lam gi?**  
Service dung de tu dong phat hien cac binh luan co dau hieu doc hai, cong kich hoac khong phu hop, giup he thong kiem duyet noi dung nhanh hon.

**2. Vi sao tach thanh service rieng?**  
Tac vu AI/ML co thoi gian xu ly va yeu cau tai nguyen rieng, nen tach service giup backend chinh nhe hon, de scale doc lap va de thay doi mo hinh khi can.

**3. Service phat hien toxic bang cach nao?**  
Service su dung mo hinh ViHateT5, mot mo hinh Transformer duoc fine-tune cho bai toan phat hien hate/toxic speech tieng Viet.

**4. API va RabbitMQ khac nhau the nao?**  
API phu hop cho kiem tra truc tiep theo request-response. RabbitMQ phu hop cho xu ly bat dong bo, khi backend gui job vao queue va nhan ket qua sau.

**5. `toxic_spans` co y nghia gi?**  
`toxic_spans` la danh sach cac khoang vi tri trong text goc ma model danh dau la toxic. Backend co the dung cac vi tri nay de highlight hoac xu ly rieng phan noi dung vi pham.

**6. Neu comment khong toxic thi RabbitMQ tra ve gi?**  
Theo thiet ke hien tai, neu comment khong toxic thi service khong publish message cap nhat, vi khong co noi dung can xu ly.

**7. Service co thay the hoan toan kiem duyet thu cong khong?**  
Khong hoan toan. Service giup tu dong loc va danh dau noi dung nghi ngo, nhung voi cac truong hop nhay cam hoac mo ho, van nen co co che kiem tra lai.

**8. Diem han che cua service la gi?**  
Ket qua phu thuoc vao do chinh xac cua mo hinh, ngu canh cau noi va du lieu huan luyen. Mot so cau mia mai, noi bong gio hoac viet bien the co the bi du doan sai.

## Comment demo phu hop bao cao

Cac cau ben duoi co sac thai tieu cuc/toxic nhe, phu hop demo ma khong dung tu chui tuc tho thien:

- "Phim nay qua te, xem ma that vong."
- "Noi dung rat nham chan, khong dang de mat thoi gian."
- "Dien vien dien qua go, lam ca bo phim mat cam xuc."
- "Tap nay kem hon mong doi, minh khong muon xem tiep."
- "Binh luan cua ban rat thieu ton trong nguoi khac."
- "Cach noi chuyen nay gay kho chiu va khong phu hop."
- "Video nay co noi dung tieu cuc, nen duoc kiem tra lai."
- "Nguoi nay lien tuc cong kich y kien cua nguoi khac."
- "Day la mot binh luan mang tinh che bai qua muc."
- "Noi dung nay de gay tranh cai va lam nguoi khac bi ton thuong."
