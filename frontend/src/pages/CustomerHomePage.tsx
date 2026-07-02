import { useEffect, useMemo, useState } from "react";
import heroImage from "../../apps/customer-web/src/assets/landing-hero.webp";
import { loadOrderContext } from "../components/customer/customerMenuStorage";
import "../components/landing/customer-landing.css";
import { formatVnd } from "../components/menu/MenuItemCard";
import { fetchCustomerMenu, type CustomerMenuResponse } from "../services/menuService";

const initialMenu: CustomerMenuResponse = { categories: [], items: [] };

function getStoredTablePath() {
  if (typeof window === "undefined") {
    return "";
  }

  const context = loadOrderContext();
  if (!context.tableCode || !context.qrToken || !context.sessionId) {
    return "";
  }

  return `/table/${encodeURIComponent(context.tableCode)}?qr=${encodeURIComponent(context.qrToken)}`;
}

export function CustomerHomePage() {
  const [menu, setMenu] = useState(initialMenu);
  const [scanNotice, setScanNotice] = useState("");
  const [storedTablePath] = useState(getStoredTablePath);

  useEffect(() => {
    let isMounted = true;

    fetchCustomerMenu()
      .then((data) => {
        if (isMounted) {
          setMenu(data);
        }
      })
      .catch(() => {
        if (isMounted) {
          setMenu(initialMenu);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const featuredItems = useMemo(
    () => menu.items.filter((item) => item.isAvailable).slice(0, 6),
    [menu.items],
  );

  function showQrNotice(message = "Để đặt món, vui lòng quét mã QR đang đặt trên bàn của bạn.") {
    setScanNotice(message);
  }

  return (
    <div className="landing-page">
      <section className="landing-hero" aria-labelledby="landing-title">
        <img
          className="landing-hero-image"
          src={heroImage}
          alt="Bàn ăn tại CMC Restaurant"
          width="1728"
          height="920"
          fetchPriority="high"
        />
        <div className="landing-hero-shade" aria-hidden="true" />
        <div className="landing-hero-copy">
          <p className="landing-eyebrow">Nhà hàng Việt hiện đại</p>
          <h1 id="landing-title">CMC Restaurant</h1>
          <p>
            Không gian ẩm thực Việt hiện đại, phục vụ tại bàn bằng QR để món ăn
            được gửi đúng bàn, đúng phiên và đúng thời điểm.
          </p>
          <div className="landing-actions" aria-label="Hành động chính">
            <a className="landing-button primary" href="#mon-noi-bat">
              Xem món nổi bật
            </a>
            {storedTablePath ? (
              <a className="landing-button secondary" href={storedTablePath}>
                Tiếp tục gọi món
              </a>
            ) : (
              <button className="landing-button secondary" type="button" onClick={() => showQrNotice()}>
                Đặt món tại bàn
              </button>
            )}
          </div>
          {scanNotice ? (
            <p className="landing-scan-notice" role="status">
              {scanNotice}
            </p>
          ) : null}
        </div>
      </section>

      <section className="landing-section" id="mon-noi-bat" aria-labelledby="featured-menu-title">
        <div className="landing-section-heading">
          <div>
            <p className="landing-eyebrow">Thực đơn hôm nay</p>
            <h2 id="featured-menu-title">Món đang phục vụ</h2>
            <p>
              Khách có thể xem trước món ăn. Khi muốn thêm vào giỏ, hệ thống sẽ
              yêu cầu phiên bàn hợp lệ từ mã QR tại nhà hàng.
            </p>
          </div>
          <button className="landing-button outline" type="button" onClick={() => showQrNotice()}>
            Tôi muốn đặt món
          </button>
        </div>

        {featuredItems.length > 0 ? (
          <div className="signature-list">
            {featuredItems.map((item) => (
              <article className="signature-dish" key={item.id}>
                <img alt={item.name} src={item.imageUrl} />
                <div>
                  <p>{item.categoryName}</p>
                  <h3>{item.name}</h3>
                  <span>{item.description}</span>
                  <strong>{formatVnd(item.price)}</strong>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <p className="landing-empty-menu">
            Thực đơn đang được đồng bộ từ hệ thống. Vui lòng thử lại sau ít phút.
          </p>
        )}
      </section>

      <section className="landing-final-cta" aria-labelledby="qr-order-title">
        <div>
          <h2 id="qr-order-title">Đặt món bằng QR tại bàn</h2>
          <p>
            Mã QR mở phiên bàn riêng cho khách đang ngồi tại nhà hàng, giúp bếp
            và nhân viên nhận đúng đơn.
          </p>
        </div>
        <button
          className="landing-button light"
          type="button"
          onClick={() => showQrNotice("Hãy quét QR trên bàn để bắt đầu gọi món.")}
        >
          Cần quét QR để đặt
        </button>
      </section>
    </div>
  );
}
