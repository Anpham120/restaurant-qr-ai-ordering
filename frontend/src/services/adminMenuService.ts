import { menuItems } from "../mocks/menuItems";
import { createApiClient } from "@cmc/api-client";
import type { AdminMenuCategory, AdminMenuItem, AdminMenuOverview } from "../types";

const api = createApiClient({
  getAccessToken: () =>
    typeof window === "undefined" ? null : window.localStorage.getItem("cmc.accessToken"),
});
const useMockMenu = import.meta.env.VITE_USE_MOCK_MENU === "true";

export type AdminMenuItemPayload = {
  categoryId: string;
  name: string;
  description: string;
  price: number;
  imageUrl?: string | null;
  isAvailable: boolean;
  tags: string[];
};

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

function enrichMenuItem(item: AdminMenuItem, index: number): AdminMenuItem {
  return {
    ...item,
    imageUrl: item.imageUrl || menuItems[index % menuItems.length]?.imageUrl || "",
    tags: item.tags ?? [],
  };
}

export async function getAdminMenuOverview(): Promise<AdminMenuOverview> {
  if (!useMockMenu) {
    const backendItems = await api.request<AdminMenuItem[]>("/admin/menu-items?includeInactiveCategories=true");
    const categoriesById = new Map<string, AdminMenuCategory>();

    backendItems.forEach((item) => {
      const existing = categoriesById.get(item.categoryId);
      categoriesById.set(item.categoryId, {
        id: item.categoryId,
        name: item.categoryName,
        isActive: existing?.isActive ?? true,
        itemCount: (existing?.itemCount ?? 0) + 1,
      });
    });

    return {
      categories: Array.from(categoriesById.values()),
      items: backendItems.map(enrichMenuItem),
    };
  }

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

export async function setAdminMenuItemAvailability(
  itemId: string,
  isAvailable: boolean,
): Promise<AdminMenuItem> {
  return api.request<AdminMenuItem>(`/admin/menu-items/${encodeURIComponent(itemId)}/availability`, {
    method: "PATCH",
    body: JSON.stringify({ isAvailable }),
  });
}

export async function createAdminMenuItem(payload: AdminMenuItemPayload): Promise<AdminMenuItem> {
  return api.request<AdminMenuItem>("/admin/menu-items/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateAdminMenuItem(
  itemId: string,
  payload: AdminMenuItemPayload,
): Promise<AdminMenuItem> {
  return api.request<AdminMenuItem>(`/admin/menu-items/${encodeURIComponent(itemId)}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function deleteAdminMenuItem(itemId: string): Promise<void> {
  await api.request<void>(`/admin/menu-items/${encodeURIComponent(itemId)}`, {
    method: "DELETE",
  });
}
