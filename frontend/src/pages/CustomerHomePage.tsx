import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import "../components/customer/customer-menu.css";
import { getCustomerMenu } from "../services/menuService";
import type { MenuItem } from "../types";

export function CustomerHomePage() {
  const [featuredItems, setFeaturedItems] = useState<MenuItem[]>([]);

  useEffect(() => {
    let isMounted = true;

    getCustomerMenu()
      .then((menu) => {
        if (isMounted) {
          setFeaturedItems(menu.items.filter((item) => item.isAvailable).slice(0, 3));
        }
      })
      .catch(() => {
        if (isMounted) {
          setFeaturedItems([]);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <section className="cmc-customer-page">
      <header className="cmc-hero">
        <div>
          <p className="cmc-kicker">CMC Restaurant</p>
          <h2>
            Gọi món tại bàn <span>nhanh, rõ ràng và dễ dùng</span>
          </h2>
          <p>
            Khách có thể quét QR tại bàn, xem thực đơn đang bán, đặt món mang về hoặc theo dõi
            trạng thái đơn ngay trên điện thoại.
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
        {featuredItems.length > 0 ? (
          <div className="cmc-hero-collage" aria-label="Món nổi bật">
            {featuredItems.map((item) => (
              <img alt={item.name} key={item.id} src={item.imageUrl} />
            ))}
          </div>
        ) : null}
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
            <p>Thực đơn có ảnh, danh mục, tìm kiếm và chỉ cho đặt món còn bán.</p>
          </article>
          <article className="cmc-step-card">
            <span>Bước 3</span>
            <h3>Theo dõi đơn</h3>
            <p>Đơn sau khi gửi được theo dõi bằng mã đơn để khách biết tiến độ phục vụ.</p>
          </article>
        </div>
      </div>
    </section>
  );
}
