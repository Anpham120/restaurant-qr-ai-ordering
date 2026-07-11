import type { AdminCategory, AdminCategoryRequest } from "@cmc/shared-types";
import { api } from "./apiClient";

export async function getCategories(): Promise<AdminCategory[]> {
  return api.categories.list();
}

export async function getCategory(categoryId: string): Promise<AdminCategory> {
  return api.categories.get(categoryId);
}

export async function createCategory(payload: AdminCategoryRequest): Promise<AdminCategory> {
  return api.categories.create(payload);
}

export async function updateCategory(categoryId: string, payload: AdminCategoryRequest): Promise<AdminCategory> {
  return api.categories.update(categoryId, payload);
}

export async function deleteCategory(categoryId: string): Promise<void> {
  return api.categories.delete(categoryId);
}
