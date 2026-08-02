# Benchmark Giao Dien Va Tinh Nang Nha Hang

Tai lieu nay tong hop cac website nha hang dep trong nuoc va quoc te de lam
co so nang cap giao dien va tinh nang cho **CMC Restaurant**. Muc tieu khong
phai sao chep giao dien, ma rut ra pattern phu hop voi san pham QR ordering,
AI chat, bep, nhan vien va admin hien tai.

## Huong Thiet Ke Chot

- Phong cach: sang trong, am ap, hien dai, de dung cho moi lua tuoi.
- Mau chu dao: cam dat tuoi sang, kem/nga, nau dam, diem vang am.
- Trai nghiem uu tien: mobile-first, menu-first, thao tac it cham, anh mon an
  ro, CTA luon thay duoc.
- Cam giac thuong hieu: nha hang Viet hien dai, than thien, co cau chuyen,
  khong qua toi, khong qua cau ky.

## Website Tham Chieu

| Website | Diem dang hoc | Ap dung cho CMC Restaurant |
| --- | --- | --- |
| Pizza 4P's Vietnam | Navigation ro: reservation, delivery, location, menu; menu HTML co anh, gia va danh muc. | Lam menu khach hang thanh trai nghiem chinh, co anh lon, gia ro, danh muc ngang mobile. |
| Gia Hanoi | Storytelling manh: "family", van hoa Viet, giai thuong, dat ban, gio mo cua, lien he. | Bo sung brand story "CMC Restaurant - am thuc Viet hien dai", section ve cau chuyen va loi chao. |
| Sono Saigon | Hero co CTA "See Menu" va "Reservation"; ngon ngu fine dining Viet hien dai. | Trang chu can co hai CTA ro: xem thuc don va bat dau dat mon. |
| La Table Hoi An | Anh mon an/khong gian sang, chef story, award, review, reservation da ngon ngu. | Them khu vuc chef/quality promise, review, anh khong gian, giam cam giac app demo. |
| Vien Dining | Chef letter, tasting menu, local ingredients, reservation note. | Tao "goi y set/combo" va noi bat mon theo mua/thanh phan dia phuong. |
| NUE Vietnamese | Tap trung mon an chia se, family style set, order online, pickup, delivery, reservation. | Them combo theo so nguoi va luong khach: an trua 2 nguoi, gia dinh 4 nguoi, do uong mat. |
| Dishoom | Brand voice co ca tinh, menu/reservation lap lai dung cho nguoi dung, nhieu menu theo ngu canh. | Chatbot va menu nen co goi y theo ngu canh: breakfast/lunch/dinner/drinks/group. |
| noma | Minimal, editorial, tin tuc/season, reservation updates, gio mo cua va lien he ro. | Dung layout thoang, anh lon, section mon theo mua va newsletter/booking update neu can. |
| Eleven Madison Park | Gallery anh day cam xuc, navigation gon, booking/resy, gift card, FAQ. | Them thu vien anh mon an/khong gian, FAQ ngan cho dat ban/QR order tai ban. |
| Septime | Cuc ky toi gian: menu, reservation, hours, price, address. | Cac man hinh van hanh/admin nen toi gian va uu tien thong tin can hanh dong. |

## Pattern Nen Mang Ve

### 1. Trang chu menu-first

Nguoi dung vao website nha hang thuong can: xem mon, gia, dat ban/dat mon,
gio mo cua, dia chi. Trang chu CMC nen co:

- Hero anh mon an/khong gian nha hang, khong dat logo qua lon.
- CTA chinh: `Xem thuc don`, `Bat dau dat mon`.
- CTA phu: `Dat ban`, `Theo doi don`.
- 6-8 mon noi bat ngay man hinh dau hoac sau hero.
- Gio mo cua, hotline, dia chi o khu vuc de thay.

### 2. Menu HTML dep, khong phu thuoc PDF

Menu nen la thanh phan tuong tac:

- Danh muc ngang cuon duoc tren mobile.
- Card mon co anh, gia, mo ta ngan, tag cay/chay/hai san/new/bestseller.
- Bo loc: mon chinh, khai vi, do uong, trang mieng, combo, mon chay.
- Tim kiem nhanh theo ten mon.
- Trang thai mon: con/het, dang khuyen mai, goi y.

### 3. Dat mon theo ngu canh

CMC chi ho tro QR ordering tai ban nen nen tap trung luong:

- Khach tai ban: quet QR -> chon ban -> goi mon -> bep nhan real-time.
- Nhan vien: xem don moi, xac nhan, cap nhat trang thai.
- Bep: board theo trang thai mon, uu tien theo thoi gian.

### 4. Combo va goi y thong minh

Nen them cac goi de tang cam giac san pham that:

- Combo theo so nguoi: 2 nguoi, 4 nguoi, gia dinh.
- Combo theo dip: an trua nhanh, hen ho, sinh nhat, tiec nhe.
- Goi y do uong kem mon.
- AI chat chi de xuat va tao draft cart, khach tu xac nhan moi them vao gio.

### 5. Brand story va visual system

Thiet ke nen co mot ngon ngu nhat quan:

- Mau nen: ivory/cream, cam dat, nau cacao, vang am.
- Typography: heading co ca tinh, body de doc.
- Anh mon an that/gia lap chat luong cao, crop sang, anh khong gian am.
- Khong nen dung card long card qua nhieu; dung section rong va layout thoang.
- Logo CMC nho gon tren header, khong lay het tam nhin trang chu.

### 6. Mobile-first thuc dung

Mobile la man hinh quan trong nhat:

- Header gon, nav ngang cuon duoc neu nhieu muc.
- Category tabs sticky duoi header.
- Cart bar sticky duoi man hinh.
- Nut tang/giam so luong lon, de cham.
- Khong de modal qua cao; uu tien bottom sheet cho chi tiet mon.

### 7. Admin/staff/kitchen khac customer

Customer can dep va cam xuc; admin/staff/kitchen can nhanh va ro:

- Admin: dashboard doanh thu, don moi, mon ban chay, trang thai ban, quan ly menu.
- Staff: danh sach don theo thoi gian, loc theo ban/trang thai, nut cap nhat nhanh.
- Kitchen: board cot `Moi`, `Dang lam`, `San sang`, `Da phuc vu`.
- Mau van hanh nen cung tone cam dat nhung it trang tri, nhieu contrast hon.

## Tinh Nang De Nang Cap Theo Do Uu Tien

### Phase 1 - Nang cap cam giac giao dien

- Thiet ke lai trang chu theo huong menu-first.
- Them hero anh mon an/khong gian, CTA ro.
- Lam moi menu cards, category tabs mobile, sticky cart bar.
- Dong bo UI customer/admin/staff/kitchen theo cam dat.
- Them empty/loading/error states dep hon.

### Phase 2 - Nang cap luong dat mon tai ban

- Chi `Dine-in` qua QR/phiên bàn (khong pickup/online order).
- Bep nhan don dine-in tu moi ban.
- Theo doi don hang bang timeline real-time.
- Them trang chi tiet mon voi option/ghi chu.
- Them combo/set menu theo so nguoi.

### Phase 3 - Nang cap AI va ca nhan hoa

- AI de xuat combo dua tren gio, so nguoi, mon da chon, so thich.
- AI giai thich mon an, thanh phan, do cay, goi y do uong.
- RAG lay tu knowledge base: menu, FAQ, chinh sach, combo, gio mo cua.
- AI khong tu tao don; chi tao SuggestedCartAction cho khach xac nhan.

### Phase 4 - Nang cap thuong mai va van hanh

- Dat ban co ngay/gio/so khach/ghi chu.
- Voucher/gift card/membership neu can demo nang cao.
- Review/testimonial va thu vien anh.
- Bao cao admin: mon ban chay, gio cao diem, don theo ban.
- Monitoring UI cho health, deploy version, AI provider status.

## De Xuat Issue Moi

### Issue A - Redesign customer experience theo benchmark nha hang

Pham vi:

- Trang chu menu-first.
- Header/nav mobile moi.
- Menu card moi co anh, tag, gia, CTA.
- Sticky cart bar va category tabs ngang.
- Story/brand section ngan cho CMC Restaurant.

Evidence khi dong issue:

- Screenshot desktop/mobile trang chu.
- Screenshot desktop/mobile menu.
- Build frontend pass.
- Khong lam thay doi logic order ngoai scope.

### Issue B - Hoan thien luong dine-in (QR tai ban) den bep

Pham vi:

- Checkout gan voi `tableCode`/phiên bàn ro rang.
- Don dine-in hien tren staff/kitchen board.
- Trang thai don real-time.
- Smoke test: quet QR -> tao don -> bep nhan -> cap nhat san sang.

Evidence khi dong issue:

- API test hoac manual screenshot.
- Build/test backend/frontend pass.
- Ghi ro tai khoan/role dung de test.

### Issue C - AI recommendation UX + RAG content

Pham vi:

- Chat UI dep hon, co suggested chips.
- AI tra ve goi y mon/combo theo ngu canh.
- Them knowledge base ve combo, FAQ, chinh sach dat mon.
- Guardrail: AI chi goi y, khong tu them mon vao gio.

Evidence khi dong issue:

- Test AI service pass.
- Screenshot chat voi goi y combo.
- Log/payload SuggestedCartAction hop le.

### Issue D - Admin/staff/kitchen operational polish

Pham vi:

- Dong bo tone cam dat nhung layout dam chat dashboard.
- Staff order board co filter, badge, action nhanh.
- Kitchen board co cot trang thai va uu tien theo thoi gian.
- Admin menu/order/table ro rang hon.

Evidence khi dong issue:

- Screenshot tung role.
- Frontend build pass.
- Manual flow: customer order -> staff/kitchen nhan -> update status.

## Nguon Tham Khao

- Pizza 4P's Vietnam: https://pizza4ps.com/vn/
- Pizza 4P's menu: https://pizza4ps.com/vn/menu/
- Gia Hanoi: https://www.gia-hanoi.com/
- Sono Saigon: https://sonosaigon.com/en/
- La Table Hoi An: https://latablehoian.com/
- Vien Dining: https://viendining.vn/en/
- NUE Vietnamese: https://nuevietnamese.com/
- Dishoom: https://www.dishoom.com/
- noma: https://noma.dk/
- Eleven Madison Park: https://www.elevenmadisonpark.com/
- Septime: https://www.septime-charonne.fr/

