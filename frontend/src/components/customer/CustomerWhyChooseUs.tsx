export function CustomerWhyChooseUs() {
  const features = [
    {
      id: "1",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="28" height="28">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          <path d="M9 12l2 2 4-4" />
        </svg>
      ),
      title: "Nguyên liệu tươi sạch",
      description: "100% nguyên liệu được chọn lọc kỹ càng từ nguồn cung uy tín",
    },
    {
      id: "2",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="28" height="28">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
      ),
      title: "Phục vụ nhanh chóng",
      description: "Đơn hàng được xử lý và chế biến trong thời gian ngắn nhất",
    },
    {
      id: "3",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="28" height="28">
          <rect x="1" y="4" width="22" height="16" rx="2" />
          <line x1="1" y1="10" x2="23" y2="10" />
        </svg>
      ),
      title: "Thanh toán tiện lợi",
      description: "Hỗ trợ nhiều hình thức thanh toán: tiền mặt, chuyển khoản, QR",
    },
    {
      id: "4",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="28" height="28">
          <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
        </svg>
      ),
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
