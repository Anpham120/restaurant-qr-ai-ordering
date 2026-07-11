import type { CreateUserRequest, UserSummary } from "@cmc/shared-types";
import { api } from "./apiClient";

export async function createOperationalUser(payload: CreateUserRequest): Promise<UserSummary> {
  return api.users.create(payload);
}

export async function listUsers(): Promise<UserSummary[]> {
  const response = await api.users.list();
  return response.users;
}

export async function resetUserPassword(userId: string, newPassword: string): Promise<void> {
  await api.users.resetPassword(userId, { newPassword });
}
