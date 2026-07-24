import { describe, expect, it } from "vitest";
import {
  labelGuestItemStatus,
  labelOrderStatus,
  labelPaymentChip,
} from "./opsStatusLabels";

describe("opsStatusLabels", () => {
  it("localizes order and payment chips", () => {
    expect(labelOrderStatus("Placed")).toBe("Đã gửi");
    expect(labelPaymentChip("Unselected", "NotRequested")).toBe("Chưa chọn · Chưa yêu cầu thu");
  });

  it("maps pending items to chờ chế biến after order confirm", () => {
    expect(labelGuestItemStatus("Pending", "Placed")).toBe("Chờ xác nhận");
    expect(labelGuestItemStatus("Pending", "Confirmed")).toBe("Chờ chế biến");
    expect(labelGuestItemStatus("Pending", "Preparing")).toBe("Chờ chế biến");
    expect(labelGuestItemStatus("Preparing", "Confirmed")).toBe("Đang chuẩn bị");
  });
});
