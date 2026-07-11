import { Clock3, CreditCard, HeartHandshake, ShieldCheck } from "lucide-react";

export function CustomerWhyChooseUs() {
  const features = [
    {
      id: "1",
      icon: <ShieldCheck aria-hidden="true" size={28} />,
      title: "Nguyên liệu tươi sạch",
      description: "100% nguyên liệu được chọn lọc kỹ càng từ nguồn cung uy tín",
    },
    {
      id: "2",
      icon: <Clock3 aria-hidden="true" size={28} />,
      title: "Phục vụ nhanh chóng",
      description: "Đơn hàng được xử lý và chế biến trong thời gian ngắn nhất",
    },
    {
      id: "3",
      icon: <CreditCard aria-hidden="true" size={28} />,
      title: "Thanh toán tiện lợi",
      description: "Hỗ trợ nhiều hình thức thanh toán: tiền mặt, chuyển khoản, QR",
    },
    {
      id: "4",
      icon: <HeartHandshake aria-hidden="true" size={28} />,
      title: "Đội ngũ tận tâm",
      description: "Nhân viên luôn sẵn sàng hỗ trợ và lắng nghe ý kiến của bạn",
    },
  ];

  return (
    <section className="vian-why-section" aria-label="Tại sao chọn chúng tôi">
      <div className="vian-why-header">
        <p className="vian-script-label">Vì sao chọn chúng tôi</p>
        <h2>Trải nghiệm ẩm thực tuyệt vời</h2>
        <p>Cam kết mang đến cho bạn những bữa ăn ngon nhất</p>
      </div>

      <div className="vian-why-grid">
        {features.map((feature) => (
          <div className="vian-why-card" key={feature.id}>
            <div className="vian-why-icon">{feature.icon}</div>
            <h4>{feature.title}</h4>
            <p>{feature.description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
