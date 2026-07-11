import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faFacebook, faInstagram, faTiktok, faYoutube } from "@fortawesome/free-brands-svg-icons";
import { loadOrderContext } from "../components/customer/customerMenuStorage";
import "../components/landing/customer-landing.css";
import { formatVnd } from "../components/menu/MenuItemCard";
import { fetchCustomerMenu, type CustomerMenuResponse } from "../services/menuService";
import {
  Smartphone, UtensilsCrossed, Sparkles, MapPin, Phone, Mail, Globe,
  MessageCircle, Bot, Star, CheckCircle, X,
  ExternalLink, Camera, QrCode, ChevronLeft, ChevronRight, Flame,
  BookOpen, Layers, Truck, Coffee, Play,
} from "lucide-react";

/* ========================================================================
   Data & constants
   ======================================================================== */
const initialMenu: CustomerMenuResponse = { categories: [], items: [] };

const HERO_FALLBACK_SLIDES = [
  { src: "/menu-images/08-pho-bo-tai-nam.png", alt: "Phở bò tái nạm truyền thống" },
  { src: "/menu-images/11-bun-cha-ha-noi.png", alt: "Bún chả Hà Nội đặc trưng" },
  { src: "/menu-images/15-com-tam-suon-bi-cha.png", alt: "Cơm tấm sườn bì chả Sài Gòn" },
  { src: "/menu-images/33-lau-hai-san-chua-cay.png", alt: "Lẩu hải sản chua cay" },
];

const CUISINE_FALLBACK = [
  { id: "f1", name: "Phở bò tái nạm", description: "Nước dùng hầm xương 12 tiếng, thịt bò tái mềm, nạm giòn và hành lá tươi. Tinh hoa ẩm thực Hà Nội.", categoryName: "Phở & Bún", price: 65000, imageUrl: "/menu-images/08-pho-bo-tai-nam.png", isAvailable: true },
  { id: "f2", name: "Bún chả Hà Nội", description: "Chả viên và chả miếng nướng than hoa thơm lừng, ăn kèm bún tươi, rau sống và nước mắm chua ngọt.", categoryName: "Phở & Bún", price: 60000, imageUrl: "/menu-images/11-bun-cha-ha-noi.png", isAvailable: true },
  { id: "f3", name: "Cơm tấm sườn bì chả", description: "Sườn nướng mật ong giòn ngọt, bì heo sợi giòn dai và chả trứng hấp mềm mịn, đúng vị Sài Gòn.", categoryName: "Cơm", price: 55000, imageUrl: "/menu-images/15-com-tam-suon-bi-cha.png", isAvailable: true },
  { id: "f4", name: "Lẩu hải sản chua cay", description: "Tôm, mực, nghêu tươi sống trong nước lẩu Tom Yum chua cay đậm đà, ăn kèm rau sống và bún tươi.", categoryName: "Lẩu", price: 280000, imageUrl: "/menu-images/33-lau-hai-san-chua-cay.png", isAvailable: true },
];

const TESTIMONIALS = [
  { name: "Anh Công Vũ", role: "Food Blogger", avatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop", stars: 5, text: "Một nơi để tìm về đúng nghĩa với mâm cơm Việt, những món ngon mộc mạc của bà của mẹ. Mình gọi đĩa thịt rang cháy cạnh và bát canh cua mồng tơi nhiều gạch kèm cà pháo muối giòn mà ưng ý vô cùng!" },
  { name: "Chị Phương Anh", role: "Nhà báo", avatar: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop", stars: 5, text: "Đồ ăn đúng vị gia đình nhưng lại được bày biện bắt mắt như nhà hàng 5 sao. Không gian quán đẹp, thoáng đãng ngập ánh nắng tự nhiên, phục vụ rất dễ thương và lên món nhanh." },
  { name: "Anh Quyết", role: "Doanh nhân", avatar: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&h=100&fit=crop", stars: 5, text: "Nhà hàng cơm Việt CMC là nơi tôi tự tin rủ bạn bè, đối tác đi ăn những bữa cơm thân mật như tại nhà. Đặc biệt hệ thống quét QR đặt món tại bàn rất tiện lợi, thông minh." },
];

/* ========================================================================
   Helpers
   ======================================================================== */
function getStoredTablePath() {
  if (typeof window === "undefined") return "";
  const ctx = loadOrderContext();
  if (!ctx.tableCode || !ctx.qrToken || !ctx.sessionId || !ctx.sessionToken) return "";
  return `/table/${encodeURIComponent(ctx.tableCode)}?qr=${encodeURIComponent(ctx.qrToken)}`;
}

function hasActiveSession(): boolean {
  if (typeof window === "undefined") return false;
  const ctx = loadOrderContext();
  return Boolean(ctx.sessionId && ctx.sessionToken && ctx.tableCode);
}

/* ========================================================================
   Hooks
   ======================================================================== */
function useScrollReveal() {
  useEffect(() => {
    const els = document.querySelectorAll("[data-reveal]");
    if (!els.length) return;
    const observer = new IntersectionObserver(
      (entries) => entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("is-visible"); observer.unobserve(e.target); } }),
      { threshold: 0.1, rootMargin: "0px 0px -40px 0px" },
    );
    els.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);
}

function useHeroSlideshow(count: number, interval = 5000) {
  const [active, setActive] = useState(0);
  useEffect(() => {
    if (count <= 1) return;
    const id = setInterval(() => setActive((i) => (i + 1) % count), interval);
    return () => clearInterval(id);
  }, [count, interval]);
  return [active, setActive] as const;
}

/* ========================================================================
   Component
   ======================================================================== */
export function CustomerHomePage() {
  const [menu, setMenu] = useState(initialMenu);
  const [scanNotice, setScanNotice] = useState("");
  const storedTablePath = useMemo(getStoredTablePath, []);

  useScrollReveal();

  useEffect(() => {
    let mounted = true;
    fetchCustomerMenu()
      .then((d) => { if (mounted) setMenu(d); })
      .catch(() => { if (mounted) setMenu(initialMenu); });
    return () => { mounted = false; };
  }, []);

  const featuredItems = useMemo(
    () => menu.items.filter((i) => i.isAvailable).slice(0, 6),
    [menu.items],
  );

  // Pick diverse items for cuisine showcase (different categories)
  const cuisineShowcase = useMemo(() => {
    const items = menu.items.filter((i) => i.isAvailable && i.imageUrl);
    const seen = new Set<string>();
    const result: typeof items = [];
    for (const item of items) {
      if (!seen.has(item.categoryName) && result.length < 4) {
        seen.add(item.categoryName);
        result.push(item);
      }
    }
    return result.length > 0 ? result : CUISINE_FALLBACK as typeof items;
  }, [menu.items]);

  // Build hero slides from real menu images
  const heroSlides = useMemo(() => {
    const items = menu.items.filter((i) => i.isAvailable && i.imageUrl);
    if (items.length >= 4) {
      // Pick from different categories for variety
      const seen = new Set<string>();
      const picks: { src: string; alt: string }[] = [];
      for (const item of items) {
        if (!seen.has(item.categoryName) && picks.length < 4) {
          seen.add(item.categoryName);
          picks.push({ src: item.imageUrl!, alt: item.name });
        }
      }
      return picks.length >= 4 ? picks : HERO_FALLBACK_SLIDES;
    }
    return HERO_FALLBACK_SLIDES;
  }, [menu.items]);

  // Pick items for promotions section
  const promoItems = useMemo(() => {
    const items = menu.items.filter((i) => i.isAvailable && i.imageUrl);
    return {
      combo: items.find((i) => i.categoryName === "Lẩu") ?? items[0],
      drink: items.find((i) => i.categoryName === "Cà phê & Trà" || i.categoryName === "Nước ép & Sinh tố") ?? items[1],
      seasonal: items.find((i) => i.categoryName === "Đặc sản vùng miền") ?? items[2],
    };
  }, [menu.items]);

  function showQrNotice(msg = "Vui lòng quét mã QR tại bàn trong nhà hàng để đặt món.") {
    setScanNotice(msg);
    setTimeout(() => setScanNotice(""), 5000);
  }

  return (
    <div className="landing-page">
      {/* 1. HERO with slideshow */}
      <HeroSection
        storedTablePath={storedTablePath}
        scanNotice={scanNotice}
        onQrNotice={showQrNotice}
        slides={heroSlides}
      />

      {/* Section divider heading - Vian style */}
      <div className="landing-vian-section-title" data-reveal>
        <h2>Về chúng tôi</h2>
      </div>

      {/* 2. ABOUT */}
      <AboutSection />

      {/* 2.1. CUISINE - Vian style alternating grid */}
      <CuisineSection items={cuisineShowcase} />

      {/* 2.2. SPACE - Restaurant interior gallery */}
      <SpaceSection />

      {/* 2.3. MEDIA */}
      <MediaSection />

      {/* 3. FEATURED DISHES */}
      <section className="landing-section alt-bg" id="thuc-don" aria-labelledby="featured-title">
        <div className="landing-section-heading" data-reveal>
          <div>
            <p className="landing-eyebrow">Thực đơn hôm nay</p>
            <h2 id="featured-title">Món bán chạy</h2>
            <p>Những món ăn được yêu thích nhất tại nhà hàng, chế biến từ nguyên liệu tươi ngon mỗi ngày.</p>
          </div>
        </div>
        {featuredItems.length > 0 ? (
          <div className="signature-list">
            {featuredItems.map((item, idx) => (
              <article className="signature-dish" key={item.id} data-reveal style={{ "--reveal-index": idx } as React.CSSProperties}>
                <img alt={item.name} src={item.imageUrl ?? `https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&h=400&fit=crop`} loading="lazy" />
                <div className="signature-dish-info">
                  <p className="signature-dish-category">{item.categoryName}</p>
                  <h3 className="signature-dish-name">{item.name}</h3>
                  <span className="signature-dish-desc">{item.description}</span>
                  <strong className="signature-dish-price">{formatVnd(item.price)}</strong>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <p className="landing-empty-menu">Thực đơn đang được đồng bộ từ hệ thống. Vui lòng thử lại sau ít phút.</p>
        )}
      </section>

      {/* 4. PROMOTIONS - Vian ornate frame style */}
      <section className="landing-promo-vian-section" aria-labelledby="promo-title">
        <div className="landing-vian-section-title" data-reveal>
          <h2 id="promo-title">Khuyến mãi hôm nay</h2>
        </div>
        <div className="landing-promo-vian-grid" data-reveal>
          {[
            {
              img: promoItems.combo?.imageUrl ?? "/menu-images/33-lau-hai-san-chua-cay.png",
              title: "Combo gia đình",
              badge: "-20%",
              desc: "Tiết kiệm 20% khi gọi combo 4 món chính + 2 đồ uống + 1 tráng miệng.",
            },
            {
              img: promoItems.drink?.imageUrl ?? "/menu-images/57-ca-phe-sua-da.png",
              title: "Happy Hour 14h-17h",
              badge: "-15%",
              desc: "Giảm 15% tất cả đồ uống và tráng miệng vào khung giờ vàng mỗi ngày.",
            },
            {
              img: promoItems.seasonal?.imageUrl ?? "/menu-images/43-mi-quang-tom-thit.png",
              title: "Thực đơn mùa hè",
              badge: "MỚI",
              desc: "Ra mắt 10 món mới đặc biệt cho mùa hè với nguyên liệu theo mùa tươi ngon.",
            },
          ].map((item, i) => (
            <div className="landing-promo-vian-item" key={i}>
              <div className="landing-promo-vian-frame">
                <img src={item.img} alt={item.title} loading="lazy" />
                <div className="landing-promo-vian-badge">{item.badge}</div>
              </div>
              <h3>{item.title}</h3>
              <p>{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 5. HOW TO ORDER */}
      <section className="landing-section alt-bg" id="cach-dat-mon" aria-labelledby="steps-title">
        <div className="landing-section-heading" data-reveal>
          <div>
            <p className="landing-eyebrow">Đơn giản & Nhanh chóng</p>
            <h2 id="steps-title">Cách đặt món</h2>
            <p>Chỉ 3 bước đơn giản để thưởng thức bữa ăn tuyệt vời tại CMC Restaurant.</p>
          </div>
        </div>
        <div className="landing-steps" data-reveal>
          <div className="landing-step">
            <div className="landing-step-icon"><Smartphone size={28} /></div>
            <div className="landing-step-number" />
            <h3>Quét mã QR tại bàn</h3>
            <p>Mỗi bàn có mã QR riêng. Quét để mở phiên đặt món cho bàn của bạn.</p>
          </div>
          <div className="landing-step">
            <div className="landing-step-icon"><UtensilsCrossed size={28} /></div>
            <div className="landing-step-number" />
            <h3>Chọn món yêu thích</h3>
            <p>Duyệt thực đơn, nhờ AI gợi ý, thêm vào giỏ hàng và đặt món.</p>
          </div>
          <div className="landing-step">
            <div className="landing-step-icon"><Sparkles size={28} /></div>
            <div className="landing-step-number" />
            <h3>Nhận món tại bàn</h3>
            <p>Bếp nhận đơn ngay lập tức, nhân viên phục vụ mang món đến tận bàn.</p>
          </div>
        </div>
      </section>

      {/* 6. TESTIMONIALS */}
      <TestimonialsSection />

      {/* 7. CTA banner */}
      <section className="landing-section" style={{ background: "linear-gradient(135deg, #5a3a30 0%, #6e453b 60%, #8B6F5E 100%)", color: "#fff", textAlign: "center" }} data-reveal>
        <p className="landing-eyebrow" style={{ color: "rgba(221,197,165,0.8)" }}>Sẵn sàng thưởng thức?</p>
        <h2 style={{ fontSize: "clamp(28px, 3.5vw, 48px)", margin: "0 auto", maxWidth: 600, color: "#fff" }}>
          Đặt món ngay tại bàn của bạn
        </h2>
        <p style={{ maxWidth: 500, margin: "var(--space-4) auto 0", color: "rgba(237,228,213,0.85)", lineHeight: "var(--leading-relaxed)" }}>
          Quét mã QR trên bàn để bắt đầu phiên đặt món. Bếp nhận đơn ngay, phục vụ nhanh chóng.
        </p>
        <div style={{ marginTop: "var(--space-6)", display: "flex", justifyContent: "center", gap: "var(--space-4)", flexWrap: "wrap" }}>
          {storedTablePath ? (
            <a className="landing-button light" href={storedTablePath}>Tiếp tục đặt món</a>
          ) : (
            <button className="landing-button light" type="button" onClick={() => showQrNotice()}>
              Quét QR để đặt món
            </button>
          )}
        </div>
      </section>

      {/* AI CTA banner linking to the chat page. */}
      <section className="landing-ai-cta" id="ai-tu-van">
        <div className="landing-ai-cta-inner">
          <div className="landing-ai-cta-text">
            <Bot size={28} />
            <div>
              <h3>Trợ lý AI thông minh</h3>
              <p>Hỏi bất cứ điều gì về thực đơn: gợi ý món, combo hoặc đồ uống. AI tư vấn ngay!</p>
            </div>
          </div>
          <a className="landing-ai-cta-btn" href="/chat">
            <MessageCircle size={18} /> Chat với AI ngay
          </a>
        </div>
      </section>

      {/* 10. FOOTER */}
      <FooterSection />

      {/* Scan notice toast */}
      {scanNotice ? (
        <div className="landing-toast" role="status" style={{
          position: "fixed", bottom: 100, left: "50%", transform: "translateX(-50%)",
          zIndex: 80, padding: "var(--space-3) var(--space-5)",
          background: "var(--vian-brown-dark)", color: "#fff",
          borderRadius: "var(--radius-pill)", boxShadow: "var(--elevation-3)",
          fontSize: "var(--text-sm)", fontWeight: 600, whiteSpace: "nowrap",
          animation: "toast-in var(--duration-slow) var(--ease-emphasized) both",
        }}>
           <Smartphone size={16} style={{ display: "inline", verticalAlign: "-2px" }} /> {scanNotice}
        </div>
      ) : null}
    </div>
  );
}

/* ========================================================================
   Sub-components
   ======================================================================== */

const ROTATING_TEXTS = [
  "giảm đến 30%",
  "đậm đà vị Việt",
  "phục vụ tức thì",
  "đẳng cấp 5 sao",
  "gợi ý thông minh",
];

const PROMO_MESSAGES = [
  "Giảm ngay 10% cho đơn hàng đầu tiên qua AI",
  "Tặng Pepsi mát lạnh khi quét mã gọi món tại bàn",
  "Thưởng thức Phở Thìn nóng hổi chuẩn vị truyền thống",
  "100% nguyên liệu tươi sạch chuẩn VietGAP mỗi ngày",
];

function HeroSection({ storedTablePath, scanNotice, onQrNotice, slides }: {
  storedTablePath: string;
  scanNotice: string;
  onQrNotice: (msg?: string) => void;
  slides: { src: string; alt: string }[];
}) {
  const [activeSlide, setActiveSlide] = useHeroSlideshow(slides.length);

  const handlePrevSlide = () => {
    setActiveSlide((prev) => (prev - 1 + slides.length) % slides.length);
  };

  const handleNextSlide = () => {
    setActiveSlide((prev) => (prev + 1) % slides.length);
  };

  return (
    <section className="landing-hero" aria-labelledby="landing-title">
      <div className="landing-hero-slideshow" aria-hidden="true">
        {slides.map((slide, idx) => (
          <div className={`landing-hero-slide${idx === activeSlide ? " active" : ""}`} key={slide.src}>
            <img src={slide.src} alt={slide.alt} loading={idx === 0 ? "eager" : "lazy"} fetchPriority={idx === 0 ? "high" : undefined} />
          </div>
        ))}
      </div>
      <div className="landing-hero-overlay" aria-hidden="true" />
      
      <div className="landing-hero-copy">
        <h1 id="landing-title">
          <span className="hero-script-text">Đậm đà</span>
          <span className="hero-sub-heading">Hương vị cơm Việt</span>
        </h1>
      </div>

      {/* Left/Right Arrow Navigation Buttons */}
      <button className="landing-hero-nav-btn prev" type="button" onClick={handlePrevSlide} aria-label="Slide trước">
        <ChevronLeft size={24} />
      </button>
      <button className="landing-hero-nav-btn next" type="button" onClick={handleNextSlide} aria-label="Slide sau">
        <ChevronRight size={24} />
      </button>

      {/* Slide dots */}
      <div className="landing-hero-dots">
        {slides.map((_, idx) => (
          <button
            key={idx}
            className={`landing-hero-dot${idx === activeSlide ? " active" : ""}`}
            type="button"
            aria-label={`Slide ${idx + 1}`}
            onClick={() => setActiveSlide(idx)}
          />
        ))}
      </div>
    </section>
  );
}

function AboutSection() {
  return (
    <section className="landing-about" id="gioi-thieu" aria-labelledby="about-title">
      <div className="landing-about-image" data-reveal>
        <img
          src="/menu-images/03-banh-xeo-mien-tay.png"
          alt="Bánh xèo miền Tây tại CMC Restaurant"
          loading="lazy"
        />
      </div>
      <div className="landing-about-content" data-reveal style={{ "--reveal-index": 1 } as React.CSSProperties}>
        <p className="landing-eyebrow">Triết lý ẩm thực</p>
        <h2 id="about-title">CMC Restaurant - Hương vị Việt tròn vị</h2>
        <p>
          Tại CMC Restaurant, triết lý của chúng tôi rất đơn giản: chia sẻ hương vị ẩm thực Việt truyền thống và văn hóa thưởng thức cơm gia đình thơm ngon, tròn vị tới tất cả mọi người.
        </p>
        <p>
          Chúng tôi nâng niu từng bữa ăn bằng việc sử dụng nguồn nguyên liệu tươi sạch chuẩn VietGAP thu hoạch mỗi sớm mai, và chế biến tỉ mỉ dưới đôi bàn tay của những người đầu bếp tận tâm nhất.
        </p>
        <p>
          Không gian nhà hàng được thiết kế mở, tối giản và ngập tràn nắng gió tự nhiên. Đây là nơi phù hợp cho bữa cơm gia đình, buổi hẹn hò hoặc gặp gỡ đối tác.
        </p>
        <div className="landing-about-stats">
          <div className="landing-about-stat">
            <strong>91+</strong>
            <span>Món ngon Việt</span>
          </div>
          <div className="landing-about-stat">
            <strong>13</strong>
            <span>Danh mục</span>
          </div>
          <div className="landing-about-stat">
            <strong><Star aria-hidden="true" size={18} /> 5/5</strong>
            <span>Đánh giá khách</span>
          </div>
        </div>
      </div>
    </section>
  );
}

function SpaceSection() {
  const photos = [
    { src: "/album-images/02-khong-gian-tang-1.png", alt: "Không gian tầng 1 rộng rãi" },
    { src: "/album-images/05-san-vuon.png", alt: "Sân vườn xanh mát" },
    { src: "/album-images/06-phong-vip.png", alt: "Phòng VIP sang trọng" },
  ];

  return (
    <section className="landing-space-vian" id="khong-gian" aria-labelledby="space-title">
      <div className="landing-space-vian-bg" aria-hidden="true" />
      <div className="landing-vian-section-title" data-reveal style={{ border: "none", padding: "0 0 clamp(30px, 4vw, 50px)", background: "transparent" }}>
        <h2 id="space-title" style={{ color: "#fff" }}>Không gian nhà hàng</h2>
      </div>
      <div className="landing-space-gallery" data-reveal>
        {photos.map((p, idx) => (
          <div className={`landing-space-frame ${idx === 1 ? "featured" : ""}`} key={idx}>
            <img src={p.src} alt={p.alt} loading="lazy" />
          </div>
        ))}
      </div>
      <div style={{ position: "relative", display: "flex", justifyContent: "center", marginTop: "clamp(24px, 3vw, 40px)" }} data-reveal>
        <a className="landing-button" href="/album" style={{ background: "var(--vian-brown)", color: "#fff", letterSpacing: "1.2px" }}>
          Xem thêm
        </a>
      </div>
    </section>
  );
}

function CuisineSection({ items }: { items: CustomerMenuResponse["items"] }) {
  if (items.length === 0) return null;

  return (
    <section className="landing-cuisine-vian" id="am-thuc" aria-labelledby="cuisine-title">
      <div className="landing-vian-section-title" data-reveal style={{ border: "none", padding: "0 0 clamp(30px, 4vw, 50px)" }}>
        <h2 id="cuisine-title">Ẩm thực</h2>
      </div>
      <div className="landing-cuisine-grid" data-reveal>
        {items.map((item, idx) => (
          <div className={`landing-cuisine-item ${idx % 2 === 1 ? "reverse" : ""}`} key={item.id}>
            <div className="landing-cuisine-img-frame">
              <img src={item.imageUrl ?? "/menu-images/08-pho-bo-tai-nam.png"} alt={item.name} loading="lazy" />
            </div>
            <div className="landing-cuisine-text">
              <p className="landing-cuisine-category">{item.categoryName}</p>
              <h3>{item.name}</h3>
              <p>{item.description}</p>
              <strong className="landing-cuisine-price">{formatVnd(item.price)}</strong>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function MediaSection() {
  return (
    <section className="landing-section" aria-labelledby="media-title">
      <div className="landing-media-banner" data-reveal>
        <div className="landing-media-content">
          <p className="landing-eyebrow" style={{ color: "var(--color-warning)" }}>Truyền thông đánh giá</p>
          <h2 id="media-title">Hanoi Food Review & Báo chí nói về chúng tôi</h2>
          <p>
            "Một nơi để tìm về đúng nghĩa của mâm cơm Việt, những món ngon mộc mạc của bà của mẹ nhưng được bày biện tinh tế theo đẳng cấp 5 sao."
          </p>
          <a
            className="landing-button primary"
            href="https://www.youtube.com/watch?v=3zcLgiolz1E"
            target="_blank"
            rel="noopener noreferrer"
          >
            Xem Video Đánh Giá
          </a>
        </div>
        <div className="landing-media-video-placeholder">
          <img
            src="/menu-images/02-nem-ran-ha-noi.png"
            alt="Nem rán Hà Nội - Đặc sản CMC Restaurant"
            loading="lazy"
          />
          <div className="play-button-icon"><Play aria-hidden="true" fill="currentColor" /></div>
        </div>
      </div>
    </section>
  );
}

function TestimonialsSection() {
  const [activeDot, setActiveDot] = useState(0);

  // Auto-rotate testimonials
  useEffect(() => {
    const interval = setInterval(() => {
      setActiveDot((prev) => (prev + 1) % TESTIMONIALS.length);
    }, 6000);
    return () => clearInterval(interval);
  }, []);

  return (
    <section className="landing-testimonials-vian" id="danh-gia" aria-labelledby="testimonials-title">
      <div className="landing-testimonials-vian-bg" aria-hidden="true" />
      <h2 id="testimonials-title" className="landing-testimonials-vian-heading" data-reveal>Cảm nhận khách hàng</h2>
      <div className="landing-testimonials-vian-content" data-reveal>
        <img className="landing-testimonials-vian-avatar" src={TESTIMONIALS[activeDot].avatar} alt={TESTIMONIALS[activeDot].name} />
        <blockquote className="landing-testimonials-vian-quote">
          "{TESTIMONIALS[activeDot].text}"
        </blockquote>
        <cite className="landing-testimonials-vian-cite">{TESTIMONIALS[activeDot].name}</cite>
      </div>
      <div className="landing-testimonial-dots" data-reveal>
        {TESTIMONIALS.map((_, idx) => (
          <button key={idx} className={`landing-testimonial-dot${idx === activeDot ? " active" : ""}`} type="button" aria-label={`Review ${idx + 1}`} onClick={() => setActiveDot(idx)} />
        ))}
      </div>
    </section>
  );
}

function FooterSection() {
  return (
    <footer className="landing-footer">
      <div className="landing-footer-bg" aria-hidden="true" />
      <div className="landing-footer-content">
        <div>
          <h4>CMC Restaurant</h4>
          <p>Nhà hàng cơm Việt ngon tròn vị, kết hợp giữa ẩm thực gia đình mộc mạc và công nghệ đặt món QR AI tiện lợi.</p>
          <p style={{ fontSize: "var(--text-xs)", color: "var(--color-warning)", marginTop: "var(--space-2)" }}>
            * Nhà hàng có chỗ để xe ô tô miễn phí
          </p>
        </div>
        <div>
          <h4>Cơ sở nhà hàng</h4>
          <p style={{ marginBottom: "var(--space-2)", fontSize: "var(--text-sm)" }}>
            <strong>Cơ sở 1:</strong> 145 Hoàng Cầu, Q. Đống Đa, Hà Nội<br />
            Hotline: <a href="tel:0904816145" style={{ color: "inherit", textDecoration: "none" }}>0904 816 145</a>
          </p>
          <p style={{ fontSize: "var(--text-sm)" }}>
            <strong>Cơ sở 2:</strong> 37 Quang Trung, Q. Hoàn Kiếm, Hà Nội<br />
            Hotline: <a href="tel:0867100337" style={{ color: "inherit", textDecoration: "none" }}>0867 100 337</a>
          </p>
        </div>
        <div>
          <h4>Giờ mở cửa</h4>
          <p><strong>Sáng:</strong> 10:00 - 14:00</p>
          <p><strong>Chiều:</strong> 18:00 - 22:00</p>
          <p style={{ fontSize: "var(--text-xs)", opacity: 0.8 }}>Tất cả các ngày trong tuần</p>
        </div>
        <div>
          <h4>Liên hệ</h4>
          <p><Mail size={14} style={{ display: "inline", verticalAlign: "-2px" }} /> <a href="mailto:info@cmcrestaurant.vn" style={{ color: "inherit" }}>info@cmcrestaurant.vn</a></p>
          <p><Globe size={14} style={{ display: "inline", verticalAlign: "-2px" }} /> <a href="https://cmcrestaurant.vn" style={{ color: "inherit" }}>cmcrestaurant.vn</a></p>
        </div>
      </div>
      <div className="landing-footer-map">
        <iframe
          src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3724.364801124675!2d105.82390887610363!3d21.01808608814704!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3135ab78078dbb43%3A0xc3fa5c904fa9e2a8!2zMTQ1IEhvw6BuZyBD4bqndSwgQ2jhu6MgRDhuqthLCDEkOG7kW5nIMSQYSwgSMOgIE7hu5lpLCBWaeG7h3QgTmFt!5e0!3m2!1svi!2svn!4v1719888888888!5m2!1svi!2svn"
          title="Vị trí CMC Restaurant trên Google Maps"
          loading="lazy"
          referrerPolicy="no-referrer-when-downgrade"
        />
      </div>
      <div className="landing-footer-bottom">
        <span>Copyright 2024 CMC Restaurant. Thiết kế và phát triển bởi CMC Technology.</span>
        <div className="landing-footer-social">
          <a href="#" aria-label="Facebook" className="landing-social-icon">
            <FontAwesomeIcon icon={faFacebook} />
          </a>
          <a href="#" aria-label="YouTube" className="landing-social-icon">
            <FontAwesomeIcon icon={faYoutube} />
          </a>
          <a href="#" aria-label="Instagram" className="landing-social-icon">
            <FontAwesomeIcon icon={faInstagram} />
          </a>
          <a href="#" aria-label="TikTok" className="landing-social-icon">
            <FontAwesomeIcon icon={faTiktok} />
          </a>
        </div>
      </div>
    </footer>
  );
}
