import type { HTMLAttributes } from "react";

export type BrandLocale = "vi" | "en";

export function formatVnd(amount: number, locale: BrandLocale = "vi") {
  return new Intl.NumberFormat(locale === "vi" ? "vi-VN" : "en-US", {
    style: "currency",
    currency: "VND",
    currencyDisplay: "symbol",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function BrandWordmark({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`brand-wordmark ${className}`.trim()} {...props}>
      <span className="brand-wordmark-monogram" aria-hidden="true">CMC</span>
      <span className="brand-wordmark-copy">
        <strong>CMC Restaurant</strong>
        <small>Gọi món tại bàn</small>
      </span>
    </div>
  );
}
