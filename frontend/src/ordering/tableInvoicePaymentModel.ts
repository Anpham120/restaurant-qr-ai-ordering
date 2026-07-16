import type { TableInvoice } from "../types";

export type PromotionPreview = {
  code: string;
  discountAmount: number;
  totalAmount: number;
};

export function getInvoicePaymentTotal(
  invoice: TableInvoice,
  promotionPreview: PromotionPreview | null,
): number {
  return promotionPreview?.totalAmount ?? invoice.subtotalAmount;
}

export function validateAppliedPromotion(
  promotionCode: string,
  promotionPreview: PromotionPreview | null,
): string | null {
  const normalizedPromotionCode = promotionCode.trim().toUpperCase();
  if (normalizedPromotionCode && promotionPreview?.code !== normalizedPromotionCode) {
    return "Vui lòng bấm Áp dụng để kiểm tra mã ưu đãi và xem đúng số tiền cần thanh toán.";
  }
  return null;
}
