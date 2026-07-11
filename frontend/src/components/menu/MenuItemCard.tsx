import type { MenuItem } from "../../types";

type MenuItemCardProps = {
  item: MenuItem;
  quantity: number;
  onAdd: (itemId: string) => void;
  onRemove: (itemId: string) => void;
};

const formatter = new Intl.NumberFormat("vi-VN");

export function formatVnd(price: number) {
  return `${formatter.format(price)}đ`;
}

/** Map ASCII tag keys to Vietnamese display labels with diacritics. */
const TAG_LABELS: Record<string, string> = {
  // Mức cay
  "khong cay": "Không cay", "cay nhe": "Cay nhẹ", "cay vua": "Cay vừa", "cay dam": "Cay đậm",
  // Nguyên liệu
  "bo": "Bò", "heo": "Heo", "ga": "Gà", "ca": "Cá", "tom": "Tôm", "muc": "Mực",
  "cua": "Cua", "dau hu": "Đậu hũ", "nam": "Nấm", "rau": "Rau",
  // Chế biến
  "nuong": "Nướng", "chien": "Chiên", "hap": "Hấp", "xao": "Xào", "kho": "Kho",
  "luoc": "Luộc", "rang": "Rang", "tiem": "Tiềm", "nau": "Nấu", "cuon": "Cuốn",
  // Vùng miền
  "mien Bac": "Miền Bắc", "mien Trung": "Miền Trung", "mien Nam": "Miền Nam",
  "Ha Noi": "Hà Nội", "Hue": "Huế", "Sai Gon": "Sài Gòn", "Da Nang": "Đà Nẵng",
  "mien Tay": "Miền Tây", "Tay Nguyen": "Tây Nguyên",
  // Dịp/Bữa
  "sang": "Sáng", "trua": "Trưa", "toi": "Tối", "an khuya": "Ăn khuya",
  "tiec": "Tiệc", "hen ho": "Hẹn hò", "sinh nhat": "Sinh nhật", "nhau": "Nhậu", "hang ngay": "Hàng ngày",
  // Đối tượng
  "tre em": "Trẻ em", "nguoi gia": "Người già", "gia dinh": "Gia đình",
  "nhom ban": "Nhóm bạn", "tiep khach": "Tiếp khách",
  // Chế độ ăn
  "chay": "Chay", "vegan": "Vegan", "healthy": "Healthy", "it calo": "Ít calo",
  "giau protein": "Giàu protein", "it dau mo": "Ít dầu mỡ", "khong MSG": "Không MSG",
  // Hương vị
  "dam da": "Đậm đà", "thanh nhe": "Thanh nhẹ", "beo": "Béo", "chua": "Chua",
  "ngot": "Ngọt", "man": "Mặn", "thom khoi": "Thơm khói",
  // Dị ứng
  "co hai san": "Có hải sản", "co dau phong": "Có đậu phộng", "co trung": "Có trứng",
  "co sua": "Có sữa", "co gluten": "Có gluten",
  // Giá
  "binh dan": "Bình dân", "tam trung": "Tầm trung", "cao cap": "Cao cấp", "premium": "Premium",
  // Phục vụ
  "ca nhan": "Cá nhân", "share": "Chia sẻ", "2-3 nguoi": "2-3 người", "3-5 nguoi": "3-5 người",
  "dat truoc": "Đặt trước", "mang di": "Mang đi",
  // Mùa
  "mua nong": "Mùa nóng", "mua lanh": "Mùa lạnh", "quanh nam": "Quanh năm", "giai nhiet": "Giải nhiệt",
};

export function tagLabel(tag: string): string {
  return TAG_LABELS[tag] || tag;
}

export function MenuItemCard({
  item,
  quantity,
  onAdd,
  onRemove,
}: MenuItemCardProps) {
  return (
    <article className={item.isAvailable ? "cmc-menu-card" : "cmc-menu-card disabled"}>
      <div className="cmc-card-image-wrap">
        <img alt={item.name} className="cmc-card-image" src={item.imageUrl} />
        <span className={item.isAvailable ? "cmc-availability ready" : "cmc-availability muted"}>
          {item.isAvailable ? "Còn món" : "Tạm hết"}
        </span>
      </div>
      <div className="cmc-card-content">
        <div>
          <p className="cmc-card-category">{item.categoryName}</p>
          <h3>{item.name}</h3>
          <p>{item.description}</p>
        </div>
        <div className="cmc-tag-row">
          {item.tags.slice(0, 3).map((tag) => (
            <span key={tag}>{tagLabel(tag)}</span>
          ))}
        </div>
        <div className="cmc-card-footer">
          <strong>{formatVnd(item.price)}</strong>
          {quantity > 0 ? (
            <div className="cmc-stepper anim-scale-in" aria-label={`${item.name} quantity`}>
              <button onClick={() => onRemove(item.id)} type="button">
                -
              </button>
              <span>{quantity}</span>
              <button disabled={!item.isAvailable} onClick={() => onAdd(item.id)} type="button">
                +
              </button>
            </div>
          ) : (
            <button
              className="cmc-add-button"
              disabled={!item.isAvailable}
              onClick={() => onAdd(item.id)}
              type="button"
            >
              + Thêm
            </button>
          )}
        </div>
      </div>
    </article>
  );
}
