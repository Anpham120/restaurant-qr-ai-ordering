import { PageShell } from "./PageShell";

export function AdminMenuPage() {
  return (
    <PageShell
      eyebrow="Admin"
      title="Quản lý thực đơn"
      description="Điều chỉnh món ăn, danh mục, giá bán và trạng thái còn món theo nhận diện CMC."
      variant="admin"
      stats={[
        { label: "Món đang bán", value: "18", detail: "Dữ liệu mẫu thực đơn" },
        { label: "Tạm hết", value: "2", detail: "Cần ẩn trên menu khách" },
      ]}
    >
      <div className="panel-grid">
        {[
          ["Danh mục", "Sắp xếp món theo nhóm để khách dễ tìm trên menu."],
          ["Trạng thái món", "Bật/tắt còn món và nổi bật món nên gợi ý."],
          ["Giá bán", "Kiểm tra giá hiển thị trước khi đồng bộ API."],
        ].map(([item, detail]) => (
          <article className="feature-panel" key={item}>
            <span className="panel-kicker">CMC Menu</span>
            <h3>{item}</h3>
            <p>{detail}</p>
          </article>
        ))}
      </div>
    </PageShell>
  );
}
