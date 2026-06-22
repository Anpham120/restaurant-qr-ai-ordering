type MenuCategoryTabsProps = {
  categories: string[];
  selectedCategory: string;
  onSelectCategory: (categoryName: string) => void;
};

export function MenuCategoryTabs({
  categories,
  selectedCategory,
  onSelectCategory,
}: MenuCategoryTabsProps) {
  return (
    <div className="cmc-category-tabs" aria-label="Danh mục thực đơn">
      {categories.map((category) => (
        <button
          className={category === selectedCategory ? "cmc-chip active" : "cmc-chip"}
          key={category}
          onClick={() => onSelectCategory(category)}
          type="button"
        >
          {category}
        </button>
      ))}
    </div>
  );
}

