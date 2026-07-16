import type { MenuItem } from "../../types";
import { Quote, Star } from "lucide-react";

type CustomerTestimonialsProps = {
  menuItems: MenuItem[];
};

const testimonials = [
  {
    id: "1",
    name: "Chị Phương Anh",
    role: "Khách hàng thân thiết",
    avatar: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop&crop=face",
    rating: 5,
    text: "Đồ ăn ngon, lên món nhanh, phục vụ tận tình. Nhất định sẽ quay lại!",
  },
  {
    id: "2",
    name: "Anh Minh Đức",
    role: "Doanh nhân",
    avatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop&crop=face",
    rating: 5,
    text: "Không gian đẹp, ấm cúng. Món ăn vừa miệng, rất phù hợp để tiếp khách.",
  },
  {
    id: "3",
    name: "Chị Thu Hà",
    role: "Food Blogger",
    avatar: "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=100&h=100&fit=crop&crop=face",
    rating: 5,
    text: "Menu QR tiện lợi, order nhanh chóng. Trải nghiệm ăn uống tuyệt vời!",
  },
];

function StarRating({ rating }: { rating: number }) {
  return (
    <div className="vian-stars" aria-label={`${rating} sao`}>
      {Array.from({ length: 5 }).map((_, i) => (
        <Star
          key={i}
          className={i < rating ? "star filled" : "star"}
          fill="currentColor"
          size={16}
        />
      ))}
    </div>
  );
}

export function CustomerTestimonials({ menuItems }: CustomerTestimonialsProps) {
  const featuredTestimonials = testimonials.slice(0, 3);

  return (
    <section className="vian-testimonials" aria-label="Cảm nhận khách hàng">
      <div className="vian-testimonials-header">
        <p className="vian-script-label">Đánh giá</p>
        <h2 className="vian-testimonials-title">Khách hàng nói gì về chúng tôi</h2>
        <p className="vian-testimonials-subtitle">
          Hơn 1000+ khách hàng đã tin tưởng và đồng hành cùng chúng tôi
        </p>
      </div>

      <div className="vian-testimonials-grid">
        {featuredTestimonials.map((testimonial) => (
          <article className="vian-testimonial-card" key={testimonial.id}>
            <div className="vian-testimonial-header">
              <img
                alt={testimonial.name}
                className="vian-testimonial-avatar"
                src={testimonial.avatar}
              />
              <div className="vian-testimonial-info">
                <h4 className="vian-testimonial-name">{testimonial.name}</h4>
                <p className="vian-testimonial-role">{testimonial.role}</p>
              </div>
            </div>
            <StarRating rating={testimonial.rating} />
            <blockquote className="vian-testimonial-text">
              "{testimonial.text}"
            </blockquote>
            <div className="vian-testimonial-decor">
              <Quote aria-hidden="true" fill="currentColor" size={32} />
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
