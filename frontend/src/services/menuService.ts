import { menuCategories, menuItems } from "../mocks/menuItems";
import type { MenuItem } from "../types";

export type CustomerMenuCategory = {
  categoryId: string;
  name: string;
};

export type CustomerMenuResponse = {
  categories: CustomerMenuCategory[];
  items: MenuItem[];
};

function toCategoryId(categoryName: string) {
  return `cat_${categoryName
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_|_$/g, "")}`;
}

export function getCustomerMenu(): CustomerMenuResponse {
  return {
    categories: menuCategories
      .filter((categoryName) => categoryName !== "Tất cả")
      .map((categoryName) => ({
        categoryId: toCategoryId(categoryName),
        name: categoryName,
      })),
    items: menuItems,
  };
}
