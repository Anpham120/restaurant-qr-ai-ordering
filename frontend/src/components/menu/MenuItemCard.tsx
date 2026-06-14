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
            <span key={tag}>{tag}</span>
          ))}
        </div>
        <div className="cmc-card-footer">
          <strong>{formatVnd(item.price)}</strong>
          {quantity > 0 ? (
            <div className="cmc-stepper" aria-label={`${item.name} quantity`}>
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
