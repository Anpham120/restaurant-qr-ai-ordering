import { menuItems } from "../mocks/menuItems";
import type { AdminMenuCategory, AdminMenuItem, AdminMenuOverview } from "../types";

const categoryIdsByName = new Map<string, string>([
  ["Khai vị", "cat_appetizer"],
  ["Phở & Bún", "cat_noodle"],
  ["Món chính", "cat_main"],
  ["Hải sản", "cat_seafood"],
  ["Lẩu", "cat_hotpot"],
  ["Tráng miệng", "cat_dessert"],
  ["Đồ uống", "cat_drink"],
]);

const toCategoryId = (categoryName: string) =>
  categoryIdsByName.get(categoryName) ?? `cat_${categoryName.toLowerCase().replace(/\s+/g, "_")}`;

export async function getAdminMenuOverview(): Promise<AdminMenuOverview> {
  const items: AdminMenuItem[] = menuItems.map((item) => ({
    ...item,
    categoryId: toCategoryId(item.categoryName),
  }));

  const categories: AdminMenuCategory[] = Array.from(categoryIdsByName.entries()).map(
    ([name, id]) => ({
      id,
      name,
      isActive: true,
      itemCount: items.filter((item) => item.categoryName === name).length,
    }),
  );

  return { categories, items };
}
