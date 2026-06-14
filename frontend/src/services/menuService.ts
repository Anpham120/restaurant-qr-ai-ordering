import { menuCategories, menuItems } from "../mocks/menuItems";
import { createApiClient } from "@cmc/api-client";
import type { MenuItem } from "../types";

export type CustomerMenuCategory = {
  categoryId: string;
  name: string;
};

export type CustomerMenuResponse = {
  categories: CustomerMenuCategory[];
  items: MenuItem[];
};

const api = createApiClient();
const useMockMenu = import.meta.env.VITE_USE_MOCK_MENU === "true";

function toCategoryId(categoryName: string) {
  return `cat_${categoryName
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_|_$/g, "")}`;
}

function getFallbackImage(index: number) {
  return menuItems[index % menuItems.length]?.imageUrl ?? menuItems[0]?.imageUrl ?? "";
}

function mapBackendMenu(menu: CustomerMenuResponse): CustomerMenuResponse {
  const imageByName = new Map(menuItems.map((item) => [item.name.toLowerCase(), item.imageUrl]));

  return {
    categories: menu.categories,
    items: menu.items.map((item, index) => ({
      ...item,
      imageUrl: imageByName.get(item.name.toLowerCase()) ?? item.imageUrl ?? getFallbackImage(index),
      tags: item.tags ?? [],
    })),
  };
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

export async function fetchCustomerMenu(): Promise<CustomerMenuResponse> {
  if (useMockMenu) {
    return getCustomerMenu();
  }

  return mapBackendMenu(await api.menu.get() as CustomerMenuResponse);
}
