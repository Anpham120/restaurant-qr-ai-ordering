import { menuItems } from "../mocks/menuItems";
import { createApiClient } from "@cmc/api-client";
import type { AdminMenuCategory, AdminMenuItem, AdminMenuOverview } from "../types";

const api = createApiClient({
  getAccessToken: () =>
    typeof window === "undefined" ? null : window.localStorage.getItem("cmc.accessToken"),
});

export type AdminMenuItemPayload = {
  categoryId: string;
  name: string;
  description: string;
  price: number;
  imageUrl?: string | null;
  isAvailable: boolean;
  tags: string[];
};

function enrichMenuItem(item: AdminMenuItem, index: number): AdminMenuItem {
  return {
    ...item,
    imageUrl: item.imageUrl || menuItems[index % menuItems.length]?.imageUrl || "",
    tags: item.tags ?? [],
  };
}

export async function getAdminMenuOverview(): Promise<AdminMenuOverview> {
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
