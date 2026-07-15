import { useI18n } from "@cmc/i18n";

export type MenuCategoryOption = { id: string; label: string };

type MenuCategoryTabsProps = {
  categories: MenuCategoryOption[];
  selectedCategory: string;
  onSelectCategory: (categoryId: string) => void;
};

export function MenuCategoryTabs({
  categories,
  selectedCategory,
  onSelectCategory,
}: MenuCategoryTabsProps) {
  const { t } = useI18n();
  return (
    <div className="cmc-category-tabs" aria-label={t("Danh mục thực đơn")}>
      {categories.map((category) => (
        <button
          className={category.id === selectedCategory ? "cmc-chip active" : "cmc-chip"}
          key={category.id}
          onClick={() => onSelectCategory(category.id)}
          type="button"
        >
          {category.label}
        </button>
      ))}
    </div>
  );
}
