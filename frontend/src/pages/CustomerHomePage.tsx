import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { loadOrderContext, saveMenuCart, loadMenuCart } from "../components/customer/customerMenuStorage";
import "../components/landing/customer-landing.css";
import { formatVnd } from "../components/menu/MenuItemCard";
import { fetchCustomerMenu, type CustomerMenuResponse } from "../services/menuService";
import { useRestaurantChat } from "../hooks/useRestaurantChat";
import type { SuggestedCartAction } from "../types";
import {
  Smartphone, UtensilsCrossed, Sparkles, MapPin, Phone, Mail, Globe,
  MessageCircle, Bot, Send, Star, CheckCircle, X,
  ExternalLink, Camera, QrCode, ChevronLeft, ChevronRight, Flame,
  ShoppingBag, BookOpen, Layers, Truck, Coffee,
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
  { id: "f1", name: "Phở bò tái nạm", description: "Nước dùng hầm xương 12 tiếng, thịt bò tái mềm, nạm giòn, hành lá tươi — tinh hoa ẩm thực Hà Nội.", categoryName: "Phở & Bún", price: 65000, imageUrl: "/menu-images/08-pho-bo-tai-nam.png", isAvailable: true },
  { id: "f2", name: "Bún chả Hà Nội", description: "Chả viên và chả miếng nướng than hoa thơm lừng, ăn kèm bún tươi, rau sống và nước mắm chua ngọt.", categoryName: "Phở & Bún", price: 60000, imageUrl: "/menu-images/11-bun-cha-ha-noi.png", isAvailable: true },
  { id: "f3", name: "Cơm tấm sườn bì chả", description: "Sườn nướng mật ong giòn ngọt, bì heo sợi giòn dai, chả trứng hấp mềm mịn — hương vị Sài Gòn chính gốc.", categoryName: "Cơm", price: 55000, imageUrl: "/menu-images/15-com-tam-suon-bi-cha.png", isAvailable: true },
  { id: "f4", name: "Lẩu hải sản chua cay", description: "Tôm, mực, nghêu tươi sống trong nước lẩu Tom Yum chua cay đậm đà, ăn kèm rau sống và bún tươi.", categoryName: "Lẩu", price: 280000, imageUrl: "/menu-images/33-lau-hai-san-chua-cay.png", isAvailable: true },
];

const TESTIMONIALS = [
  { name: "Anh Công Vũ", role: "Food Blogger", avatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop", stars: 5, text: "Một nơi để tìm về đúng nghĩa với mâm cơm Việt, những món ngon mộc mạc của bà của mẹ. Mình gọi đĩa thịt rang cháy cạnh và bát canh cua mồng tơi nhiều gạch kèm cà pháo muối giòn mà ưng ý vô cùng!" },
  { name: "Chị Phương Anh", role: "Nhà báo", avatar: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop", stars: 5, text: "Đồ ăn đúng vị gia đình nhưng lại được bày biện bắt mắt như nhà hàng 5 sao. Không gian quán đẹp, thoáng đãng ngập ánh nắng tự nhiên, phục vụ rất dễ thương và lên món nhanh." },
  { name: "Anh Quyết", role: "Doanh nhân", avatar: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&h=100&fit=crop", stars: 5, text: "Nhà hàng cơm Việt CMC là nơi tôi tự tin rủ bạn bè, đối tác đi ăn những bữa cơm thân mật như tại nhà. Đặc biệt hệ thống quét QR đặt món tại bàn rất tiện lợi, thông minh." },
];

const CHAT_QUICK_PROMPTS = [
  "Gợi ý món cho 2 người",
  "Giá của Phở bò tái nạm bao nhiêu?",
  "Tôi muốn đồ uống thanh mát",
  "Nhà hàng thanh toán bằng cách nào?",
];

/* ========================================================================
   Helpers
   ======================================================================== */
function getStoredTablePath() {
  if (typeof window === "undefined") return "";
  const ctx = loadOrderContext();
  if (!ctx.tableCode || !ctx.qrToken || !ctx.sessionId) return "";
  return `/table/${encodeURIComponent(ctx.tableCode)}?qr=${encodeURIComponent(ctx.qrToken)}`;
}

function hasActiveSession(): boolean {
  if (typeof window === "undefined") return false;
  const ctx = loadOrderContext();
  return Boolean(ctx.sessionId && ctx.tableCode);
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

function useHeaderScroll() {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 60);
    window.addEventListener("scroll", handler, { passive: true });
    handler();
    return () => window.removeEventListener("scroll", handler);
  }, []);
  return scrolled;
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
              title: "Happy Hour 14h–17h",
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

      {/* 9. AI CTA BANNER — links to /chat page */}
      <section className="landing-ai-cta" id="ai-tu-van">
        <div className="landing-ai-cta-inner">
          <div className="landing-ai-cta-text">
            <Bot size={28} />
            <div>
              <h3>Trợ lý AI thông minh</h3>
              <p>Hỏi bất cứ điều gì về thực đơn — gợi ý món, combo, đồ uống. AI tư vấn ngay!</p>
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
  "🔥 Giảm ngay 10% cho đơn hàng đầu tiên qua AI",
  "✨ Tặng Pepsi mát lạnh khi quét mã gọi món tại bàn",
  "🍲 Thưởng thức Phở Thìn nóng hổi chuẩn vị truyền thống",
  "🌿 100% nguyên liệu tươi sạch chuẩn VietGAP mỗi ngày",
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
        <h2 id="about-title">CMC Restaurant – Hương vị Việt tròn vị</h2>
        <p>
          Tại CMC Restaurant, triết lý của chúng tôi rất đơn giản: chia sẻ hương vị ẩm thực Việt truyền thống và văn hóa thưởng thức cơm gia đình thơm ngon, tròn vị tới tất cả mọi người.
        </p>
        <p>
          Chúng tôi nâng niu từng bữa ăn bằng việc sử dụng nguồn nguyên liệu tươi sạch chuẩn VietGAP thu hoạch mỗi sớm mai, và chế biến tỉ mỉ dưới đôi bàn tay của những người đầu bếp tận tâm nhất.
        </p>
        <p>
          Không gian nhà hàng được thiết kế mở, tối giản và ngập tràn nắng gió tự nhiên – là chốn tìm về lý tưởng cho những bữa cơm gia đình đầm ấm, buổi hẹn hò hay gặp gỡ đối tác trang trọng.
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
            <strong>5★</strong>
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
          <div className="play-button-icon">▶</div>
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
        <span>© 2024 CMC Restaurant. Thiết kế & phát triển bởi CMC Technology.</span>
        <div className="landing-footer-social">
          <a href="#" aria-label="Facebook" className="landing-social-icon">
            <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20"><path d="M22 12c0-5.523-4.477-10-10-10S2 6.477 2 12c0 4.991 3.657 9.128 8.438 9.878v-6.987h-2.54V12h2.54V9.797c0-2.506 1.492-3.89 3.777-3.89 1.094 0 2.238.195 2.238.195v2.46h-1.26c-1.243 0-1.63.771-1.63 1.562V12h2.773l-.443 2.89h-2.33v6.988C18.343 21.128 22 16.991 22 12z"/></svg>
          </a>
          <a href="#" aria-label="YouTube" className="landing-social-icon">
            <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>
          </a>
          <a href="#" aria-label="Instagram" className="landing-social-icon">
            <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 1 0 0 12.324 6.162 6.162 0 0 0 0-12.324zM12 16a4 4 0 1 1 0-8 4 4 0 0 1 0 8zm6.406-11.845a1.44 1.44 0 1 0 0 2.881 1.44 1.44 0 0 0 0-2.881z"/></svg>
          </a>
          <a href="#" aria-label="TikTok" className="landing-social-icon">
            <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20"><path d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z"/></svg>
          </a>
        </div>
      </div>
    </footer>
  );
}

/* ========================================================================
   AI Chat Section (Inline on landing page)
   ======================================================================== */
type ChatSectionProps = {
  menuItems: CustomerMenuResponse["items"];
  onQrNotice: (msg?: string) => void;
};

function AiChatSection({ menuItems, onQrNotice }: ChatSectionProps) {
  const chat = useRestaurantChat();
  const bodyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [chat.messages, chat.suggestions, chat.thinking]);

  function handleAddToCart(action: SuggestedCartAction) {
    if (!hasActiveSession()) {
      onQrNotice("Vui lòng quét mã QR tại bàn để đặt món vào giỏ hàng.");
      return;
    }
    const item = menuItems.find((value) => value.id === action.menuItemId && value.isAvailable);
    if (!item) {
      onQrNotice("Món này không còn khả dụng trong menu hiện tại.");
      chat.setSuggestions((current) => current.filter((value) => value.menuItemId !== action.menuItemId));
      return;
    }
    const currentCart = loadMenuCart();
    const next = { ...currentCart, [item.id]: (currentCart[item.id] ?? 0) + action.quantity };
    saveMenuCart(next);
    chat.setSuggestions((current) => current.filter((value) => value.menuItemId !== action.menuItemId));
    onQrNotice(`Đã thêm ${item.name} (×${action.quantity}) vào giỏ sau khi bạn xác nhận.`);
  }

  return (
    <section className="landing-ai-section" id="ai-tu-van" aria-labelledby="ai-title">
      <div className="landing-ai-container">
        {/* Left: Branding + Quick prompts */}
        <div className="landing-ai-intro">
          <div className="landing-ai-badge">
            <Bot size={18} /> AI Tư vấn
          </div>
          <h2 id="ai-title">Trợ lý AI<br/>thông minh</h2>
          <p>Hỏi bất cứ điều gì về thực đơn — gợi ý món, combo, đồ uống hay thông tin dinh dưỡng. AI sẽ tư vấn ngay cho bạn!</p>
          <div className="landing-ai-prompts">
            {CHAT_QUICK_PROMPTS.map((p) => (
              <button key={p} className="landing-ai-prompt-btn" type="button" disabled={!chat.chatSessionId || chat.thinking} onClick={() => chat.send(undefined, p)}>
                {p}
              </button>
            ))}
          </div>
        </div>

        {/* Right: Chat window */}
        <div className="landing-ai-chat-window">
          <div className="landing-ai-chat-header">
            <Bot size={18} />
            <span>CMC AI Assistant</span>
          </div>
          <div className="landing-ai-chat-body" ref={bodyRef}>
            {chat.messages.map((m) => (
              <div key={m.id} className={`landing-ai-msg ${m.role}`}>
                {m.role === "assistant" && (
                  <div className="landing-ai-msg-avatar"><Bot size={14} /></div>
                )}
                <div className="landing-ai-msg-bubble">{m.content}</div>
              </div>
            ))}

            {chat.suggestions.length > 0 && (
              <div className="landing-ai-suggestions">
                {chat.suggestions.map((s) => {
                  const item = menuItems.find((i) => i.id === s.menuItemId);
                  return (
                    <div className="landing-ai-suggestion-card" key={s.menuItemId}>
                      {item?.imageUrl && <img src={item.imageUrl} alt={s.name} />}
                      <div className="landing-ai-suggestion-info">
                        <strong>{item?.name ?? s.name}</strong>
                        <span>{formatVnd(item?.price ?? s.price)} × {s.quantity}</span>
                      </div>
                      <button className="landing-ai-suggestion-btn" type="button" onClick={() => handleAddToCart(s)}>
                        Thêm vào giỏ
                      </button>
                    </div>
                  );
                })}
              </div>
            )}

            {chat.thinking && (
              <div className="landing-chat-typing">
                <span /><span /><span />
              </div>
            )}
          </div>

          {chat.error && <p role="alert" className="landing-ai-error">{chat.error}</p>}

          <form className="landing-ai-composer" onSubmit={(e) => chat.send(e)}>
            <input
              className="landing-ai-input"
              placeholder="Hỏi về thực đơn..."
              value={chat.input}
              maxLength={1000}
              onChange={(e) => chat.setInput(e.target.value)}
              aria-label="Nhập tin nhắn"
            />
            <button className="landing-ai-send" type="submit" disabled={!chat.ready || !chat.chatSessionId || chat.thinking || !chat.input.trim()} aria-label="Gửi">
              <Send size={16} />
            </button>
          </form>
        </div>
      </div>
    </section>
  );
}
