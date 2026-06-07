import { Link } from "react-router-dom";
import "../components/customer/customer-menu.css";
import { menuItems } from "../mocks/menuItems";

export function CustomerHomePage() {
  return (
    <section className="cmc-customer-page">
      <header className="cmc-hero">
        <div>
          <p className="cmc-kicker">CMC Restaurant</p>
          <h2>
            Gọi món tại bàn <span>nhanh, ấm & dễ dùng</span>
          </h2>
          <p>
            Trải nghiệm QR ordering phong cách cam đất sáng, thân thiện với mọi
            lứa tuổi và sẵn sàng nối API ở các issue sau.
          </p>
          <div className="cmc-hero-actions">
            <Link className="cmc-primary-link" to="/table/T-05">
              Quét mã QR
            </Link>
            <Link className="cmc-secondary-link" to="/menu">
              Xem thực đơn
            </Link>
          </div>
        </div>
        <div className="cmc-hero-collage" aria-label="Món nổi bật">
          <img alt="Bò lúc lắc" src={menuItems[5].imageUrl} />
          <img alt="Phở bò đặc biệt" src={menuItems[4].imageUrl} />
          <img alt="Trà đào cam sả" src={menuItems[10].imageUrl} />
        </div>
      </header>

      <div className="cmc-home-flow">
        <span className="cmc-table-badge">Gọi món chỉ trong 3 bước</span>
        <div className="cmc-home-steps">
          <article className="cmc-step-card">
            <span>Bước 1</span>
            <h3>Quét mã bàn</h3>
            <p>Khách vào đường dẫn QR của bàn để giữ đúng ngữ cảnh gọi món.</p>
          </article>
          <article className="cmc-step-card">
            <span>Bước 2</span>
            <h3>Chọn món</h3>
            <p>Thực đơn có ảnh thật, lọc danh mục và tìm kiếm.</p>
          </article>
          <article className="cmc-step-card">
            <span>Bước 3</span>
            <h3>Xem giỏ hàng</h3>
            <p>Cart summary mock hiển thị số món và tổng tiền.</p>
          </article>
        </div>
      </div>
    </section>
  );
}
