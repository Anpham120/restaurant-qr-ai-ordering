import { getApiBaseUrl } from "./apiClient";
import type { MenuItem } from "../types";

export type CustomerMenuCategory = {
  categoryId: string;
  name: string;
};

export type CustomerMenuResponse = {
  categories: CustomerMenuCategory[];
  items: MenuItem[];
};

type ApiMenuItem = Omit<MenuItem, "price" | "imageUrl" | "tags"> & {
  price: number | string;
  imageUrl?: string | null;
  tags?: string[] | null;
};

type ApiMenuResponse = {
  categories?: CustomerMenuCategory[];
  items?: ApiMenuItem[];
};

const fallbackImage =
  "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=900&q=80";

function mapMenuItem(item: ApiMenuItem): MenuItem {
  return {
    id: item.id,
    name: item.name,
    description: item.description,
    price: Number(item.price),
    categoryName: item.categoryName,
    imageUrl: item.imageUrl?.trim() || fallbackImage,
    isAvailable: item.isAvailable,
    tags: item.tags ?? [],
  };
}

export async function getCustomerMenu(): Promise<CustomerMenuResponse> {
  const response = await fetch(`${getApiBaseUrl()}/menu`);

  if (!response.ok) {
    throw new Error("Không tải được thực đơn. Vui lòng thử lại sau.");
  }

  const payload = (await response.json()) as ApiMenuResponse;

  return {
    categories: payload.categories ?? [],
    items: (payload.items ?? []).map(mapMenuItem),
  };
}
