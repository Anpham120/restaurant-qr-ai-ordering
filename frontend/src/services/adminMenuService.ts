import { getApiBaseUrl } from "./apiClient";
import { getAuthHeaders } from "./authService";
import type { AdminMenuCategory, AdminMenuItem, AdminMenuOverview } from "../types";

export type AdminMenuItemInput = {
  categoryId: string;
  name: string;
  description: string;
  price: number;
  imageUrl: string;
  isAvailable: boolean;
  tags: string[];
};

type ApiAdminCategory = {
  categoryId: string;
  name: string;
  displayOrder: number;
  isActive: boolean;
};

type ApiAdminMenuItem = AdminMenuItem & {
  imageUrl?: string | null;
};

type ApiErrorPayload = {
  error?: {
    code?: string;
    message?: string;
  };
};

const fallbackImage =
  "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=900&q=80";

function apiUrl(path: string) {
  return `${getApiBaseUrl()}${path}`;
}

async function parseJson<T>(response: Response): Promise<T> {
  const payload = (await response.json().catch(() => ({}))) as T & ApiErrorPayload;
  if (!response.ok) {
    throw new Error(payload.error?.message ?? "Không thể xử lý yêu cầu thực đơn.");
  }

  return payload;
}

function mapMenuItem(item: ApiAdminMenuItem): AdminMenuItem {
  return {
    ...item,
    imageUrl: item.imageUrl?.trim() || fallbackImage,
    tags: item.tags ?? [],
  };
}

function buildPayload(input: AdminMenuItemInput) {
  return {
    categoryId: input.categoryId,
    name: input.name.trim(),
    description: input.description.trim(),
    price: input.price,
    imageUrl: input.imageUrl.trim() || null,
    isAvailable: input.isAvailable,
    tags: input.tags,
  };
}

export async function getAdminMenuOverview(): Promise<AdminMenuOverview> {
  const [categoriesResponse, itemsResponse] = await Promise.all([
    fetch(apiUrl("/admin/categories"), {
      headers: getAuthHeaders(),
    }),
    fetch(apiUrl("/admin/menu-items?includeInactiveCategories=true"), {
      headers: getAuthHeaders(),
    }),
  ]);

  const [categoriesPayload, itemsPayload] = await Promise.all([
    parseJson<ApiAdminCategory[]>(categoriesResponse),
    parseJson<ApiAdminMenuItem[]>(itemsResponse),
  ]);

  const items = itemsPayload.map(mapMenuItem);
  const categories = categoriesPayload.map<AdminMenuCategory>((category) => ({
    id: category.categoryId,
    name: category.name,
    displayOrder: category.displayOrder,
    isActive: category.isActive,
    itemCount: items.filter((item) => item.categoryId === category.categoryId).length,
  }));

  return { categories, items };
}

export async function createAdminMenuItem(input: AdminMenuItemInput): Promise<AdminMenuItem> {
  const response = await fetch(apiUrl("/admin/menu-items"), {
    method: "POST",
    headers: {
      ...getAuthHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify(buildPayload(input)),
  });

  return mapMenuItem(await parseJson<ApiAdminMenuItem>(response));
}

export async function updateAdminMenuItem(
  menuItemId: string,
  input: AdminMenuItemInput,
): Promise<AdminMenuItem> {
  const response = await fetch(apiUrl(`/admin/menu-items/${encodeURIComponent(menuItemId)}`), {
    method: "PUT",
    headers: {
      ...getAuthHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify(buildPayload(input)),
  });

  return mapMenuItem(await parseJson<ApiAdminMenuItem>(response));
}

export async function updateAdminMenuItemAvailability(
  menuItemId: string,
  isAvailable: boolean,
): Promise<AdminMenuItem> {
  const response = await fetch(
    apiUrl(`/admin/menu-items/${encodeURIComponent(menuItemId)}/availability`),
    {
      method: "PATCH",
      headers: {
        ...getAuthHeaders(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ isAvailable }),
    },
  );

  return mapMenuItem(await parseJson<ApiAdminMenuItem>(response));
}
