import type { HTMLAttributes } from "react";

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
