import type { ChatMessage, SendChatMessageResponse } from "../types";

export function restoreCommittedHistory(
  serverMessages: ChatMessage[],
  welcomeMessage: ChatMessage,
): ChatMessage[] {
  return serverMessages.length > 0 ? serverMessages : [welcomeMessage];
}

export function appendCommittedExchange(
  current: ChatMessage[],
  response: Pick<SendChatMessageResponse, "userMessage" | "message">,
): ChatMessage[] {
  return [...current, response.userMessage, response.message];
}
