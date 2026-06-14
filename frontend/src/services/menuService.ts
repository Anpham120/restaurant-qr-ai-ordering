import { menuItems } from "../mocks/menuItems";
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

function getFallbackImage(index: number) {
  return menuItems[index % menuItems.length]?.imageUrl ?? menuItems[0]?.imageUrl ?? "";
}

function normalizeVN(text: string) {
  return text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/gi, "d")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function mapBackendMenu(menu: CustomerMenuResponse): CustomerMenuResponse {
  const imageByNormName = new Map(
    menuItems.map((item) => [normalizeVN(item.name), item.imageUrl]),
  );

  const keywordImages: Array<[string[], string]> = [
    [["com ga", "ga xoi"], menuItems.find((i) => normalizeVN(i.name).includes("bo luc lac"))?.imageUrl ?? ""],
    [["com suon", "suon nuong"], menuItems.find((i) => normalizeVN(i.name).includes("nem ran"))?.imageUrl ?? ""],
    [["cha gio"], menuItems.find((i) => normalizeVN(i.name).includes("nem ran"))?.imageUrl ?? ""],
    [["banh flan", "flan"], menuItems.find((i) => normalizeVN(i.name).includes("che khuc bach"))?.imageUrl ?? ""],
    [["bun bo"], menuItems.find((i) => normalizeVN(i.name).includes("pho bo"))?.imageUrl ?? ""],
  ];

  function findImage(normName: string, index: number): string {
    const exact = imageByNormName.get(normName);
    if (exact) return exact;
    for (const [key, url] of imageByNormName) {
      if (key.includes(normName) || normName.includes(key)) return url;
    }
    for (const [keywords, url] of keywordImages) {
      if (url && keywords.some((kw) => normName.includes(kw))) return url;
    }
    return getFallbackImage(index);
  }

  return {
    categories: menu.categories,
    items: menu.items.map((item, index) => ({
      ...item,
      imageUrl: findImage(normalizeVN(item.name), index),
      tags: item.tags ?? [],
    })),
  };
}

export async function fetchCustomerMenu(): Promise<CustomerMenuResponse> {
  return mapBackendMenu(await api.menu.get() as CustomerMenuResponse);
}
