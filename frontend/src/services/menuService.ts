import type { MenuItem } from "../types";
import { resolveMenuImage, toPublicMenuImageUrl } from "../utils/menuImages";
import { api } from "./apiClient";

export type CustomerMenuCategory = {
  categoryId: string;
  name: string;
};

export type CustomerMenuResponse = {
  categories: CustomerMenuCategory[];
  items: MenuItem[];
};

function mapBackendMenu(menu: CustomerMenuResponse): CustomerMenuResponse {
  return {
    categories: menu.categories,
    items: menu.items.map((item, index) => {
      const resolved = resolveMenuImage(item.name, item.imageUrl, index);
      return {
      ...item,
      imageUrl: toPublicMenuImageUrl(resolved) ?? resolved,
      tags: item.tags ?? [],
    };
    }),
  };
}

export async function fetchCustomerMenu(): Promise<CustomerMenuResponse> {
  return mapBackendMenu((await api.menu.get()) as CustomerMenuResponse);
}
