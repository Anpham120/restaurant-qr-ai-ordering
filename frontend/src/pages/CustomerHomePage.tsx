import heroImage from "../../apps/customer-web/src/assets/landing-hero.webp";
import "../components/landing/customer-landing.css";

export function CustomerHomePage() {
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
          <h1 id="landing-title">CMC Restaurant</h1>
          <p>
            Vui lòng quét mã QR được đặt tại bàn để mở phiên gọi món. Mỗi đơn sẽ được gắn với đúng bàn đang phục vụ.
          </p>
          <div className="landing-actions" aria-label="Trạng thái gọi món">
            <span className="landing-button primary">Chờ quét QR tại bàn</span>
          </div>
        </div>
      </section>
    </div>
  );
}
