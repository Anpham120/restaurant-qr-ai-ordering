import type { CSSProperties } from "react";
import { Link } from "react-router-dom";
import heroImage from "../../apps/customer-web/src/assets/landing-hero.webp";
import qrDiningImage from "../../apps/customer-web/src/assets/qr-dining.webp";
import { menuItems } from "../mocks/menuItems";
import { useScrollReveal } from "../hooks/useScrollReveal";
import "../components/landing/customer-landing.css";

const revealAt = (index: number): CSSProperties =>
  ({ "--reveal-index": index } as CSSProperties);

const signatureItems = [menuItems[0], menuItems[4], menuItems[6]];
const currencyFormatter = new Intl.NumberFormat("vi-VN");

const experiences = [
  {
    icon: "qr",
    title: "Quét QR để gọi món",
    text: "Mở đúng thực đơn của nhà hàng ngay tại bàn, không cần cài thêm ứng dụng.",
  },
  {
    icon: "spark",
    title: "AI gợi ý theo khẩu vị",
    text: "Mô tả món bạn muốn, AI sẽ gợi ý từ thực đơn đang phục vụ.",
  },
  {
    icon: "pulse",
    title: "Theo dõi đơn realtime",
    text: "Biết món đang chờ, đang chế biến hay đã sẵn sàng để phục vụ.",
  },
];

const orderSteps = [
  ["Quét mã QR tại bàn", "Dùng camera điện thoại mở mã QR được đặt tại bàn."],
  ["Chọn món", "Xem thực đơn, tìm món phù hợp và thêm vào giỏ hàng."],
  ["Xác nhận đơn", "Kiểm tra món, số lượng và gửi yêu cầu tới bếp."],
  ["Nhận món", "Theo dõi trạng thái và thưởng thức khi món được phục vụ."],
];

export function CustomerHomePage() {
  const pageRef = useScrollReveal<HTMLDivElement>();

  return (
    <div className="landing-page" ref={pageRef}>
      <section className="landing-hero" aria-labelledby="landing-title">
        <img
          className="landing-hero-image"
          src={heroImage}
          alt="Bàn tiệc Việt Nam với gỏi cuốn, cá nướng, rau thơm và trà"
          width="1728"
          height="920"
          fetchPriority="high"
        />
        <div className="landing-hero-shade" aria-hidden="true" />
        <div className="landing-hero-copy">
          <h1 id="landing-title" data-reveal style={revealAt(0)}>
            Ẩm thực Việt, gọi món theo cách thông minh hơn
          </h1>
          <p data-reveal style={revealAt(1)}>
            Khám phá hương vị Việt được chuẩn bị chỉn chu, gọi món bằng QR và
            theo dõi hành trình từ bếp tới bàn ngay trên điện thoại.
          </p>
          <div className="landing-actions" data-reveal style={revealAt(2)}>
            <Link className="landing-button primary" to="/menu">
              Xem thực đơn <ArrowIcon />
            </Link>
            <a className="landing-button secondary" href="#cach-goi-mon">
              Cách gọi món <DownIcon />
            </a>
          </div>
        </div>
      </section>

      <section className="landing-section signature-section" aria-labelledby="signature-title">
        <div className="landing-section-heading">
          <div>
            <h2 id="signature-title">Món đặc trưng</h2>
            <p>Những hương vị quen thuộc được chọn từ thực đơn đang phục vụ.</p>
          </div>
          <Link className="landing-text-link" to="/menu">
            Xem tất cả món <ArrowIcon />
          </Link>
        </div>
        <div className="signature-list">
          {signatureItems.map((item, index) => (
            <article className="signature-dish" key={item.id} data-reveal style={revealAt(index)}>
              <img src={item.imageUrl} alt={item.name} width="640" height="480" loading="lazy" />
              <div>
                <p>{item.categoryName}</p>
                <h3>{item.name}</h3>
                <span>{item.description}</span>
                <strong>{currencyFormatter.format(item.price)}đ</strong>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-experience" id="trai-nghiem" aria-labelledby="experience-title">
        <div className="experience-image-wrap" data-reveal style={revealAt(0)}>
          <img
            src={qrDiningImage}
            alt="Khách dùng điện thoại quét mã QR cạnh món ăn tại nhà hàng"
            width="1728"
            height="1152"
            loading="lazy"
          />
        </div>
        <div className="experience-copy" data-reveal style={revealAt(1)}>
          <div className="landing-section-heading compact">
            <div>
              <h2 id="experience-title">Trải nghiệm liền mạch tại bàn</h2>
              <p>Công nghệ đứng phía sau để bữa ăn của bạn diễn ra tự nhiên hơn.</p>
            </div>
          </div>
          <div className="experience-list">
            {experiences.map((item) => (
              <article key={item.title}>
                <LandingIcon name={item.icon} />
                <div>
                  <h3>{item.title}</h3>
                  <p>{item.text}</p>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="landing-section journey-section" id="cach-goi-mon" aria-labelledby="journey-title">
        <div className="landing-section-heading">
          <div>
            <h2 id="journey-title">Cách gọi món</h2>
            <p>Bốn bước rõ ràng, từ lúc quét mã đến khi món được phục vụ.</p>
          </div>
        </div>
        <ol className="journey-list">
          {orderSteps.map(([title, text], index) => (
            <li key={title} data-reveal style={revealAt(index)}>
              <span aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
              <div>
                <h3>{title}</h3>
                <p>{text}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="landing-ai" aria-labelledby="ai-title">
        <div className="ai-copy" data-reveal style={revealAt(0)}>
          <h2 id="ai-title">Chưa biết chọn món gì?</h2>
          <p>
            Hãy nói về khẩu vị, số người hoặc món bạn đang muốn ăn. Trợ lý AI
            sẽ tìm trong thực đơn và gợi ý lựa chọn phù hợp.
          </p>
          <Link className="landing-button outline" to="/chat">
            Hỏi AI chọn món <ArrowIcon />
          </Link>
        </div>
        <div className="ai-preview" aria-label="Ví dụ hội thoại với trợ lý chọn món" data-reveal style={revealAt(1)}>
          <div className="ai-preview-head">
            <LandingIcon name="spark" />
            <div><strong>Trợ lý chọn món</strong><span>Gợi ý từ thực đơn CMC</span></div>
          </div>
          <div className="ai-message user">Tôi muốn một món Việt nhẹ, ít cay.</div>
          <div className="ai-message assistant">
            Bạn có thể thử gỏi cuốn tôm thịt: vị tươi, nhẹ và dùng cùng rau thơm.
          </div>
          <div className="ai-input" aria-hidden="true">
            <span>Nhập món bạn đang muốn ăn…</span><SendIcon />
          </div>
        </div>
      </section>

      <section className="landing-final-cta" aria-labelledby="final-cta-title">
        <div data-reveal style={revealAt(0)}>
          <h2 id="final-cta-title">Sẵn sàng khám phá thực đơn?</h2>
          <p>Xem món đang phục vụ hoặc quét QR tại bàn để bắt đầu gọi món.</p>
        </div>
        <Link className="landing-button light" to="/menu" data-reveal style={revealAt(1)}>
          Xem thực đơn <ArrowIcon />
        </Link>
      </section>

      <footer className="landing-footer">
        <strong translate="no">CMC Restaurant</strong>
        <p>Ẩm thực Việt và trải nghiệm gọi món thông minh.</p>
        <nav aria-label="Liên kết cuối trang">
          <Link to="/menu">Thực đơn</Link>
          <a href="#trai-nghiem">Trải nghiệm</a>
          <a href="#cach-goi-mon">Cách gọi món</a>
          <Link to="/chat">Hỏi AI</Link>
        </nav>
      </footer>
    </div>
  );
}

function LandingIcon({ name }: { name: string }) {
  if (name === "qr") {
    return <span className="landing-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM15 14h2v2h-2zM19 14h1v4h-3v2h-3v-4h2v2h2v-2h-3" /></svg></span>;
  }
  if (name === "pulse") {
    return <span className="landing-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"/><path d="M8 12h2l1.5-3 2 6 1.5-3h2"/></svg></span>;
  }
  return <span className="landing-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="m12 3 1.4 4.1L17.5 8.5l-4.1 1.4L12 14l-1.4-4.1-4.1-1.4 4.1-1.4zM18.5 14l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8z"/></svg></span>;
}

function ArrowIcon() {
  return <svg className="button-icon" viewBox="0 0 20 20" aria-hidden="true"><path d="M4 10h11M11 6l4 4-4 4" /></svg>;
}

function DownIcon() {
  return <svg className="button-icon" viewBox="0 0 20 20" aria-hidden="true"><path d="M10 4v11M6 11l4 4 4-4" /></svg>;
}

function SendIcon() {
  return <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m3 4 14 6-14 6 2-6zM5 10h7" /></svg>;
}
