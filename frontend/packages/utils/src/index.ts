export const formatVnd = (value: number) => new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND", maximumFractionDigits: 0 }).format(value);
export const classNames = (...values: Array<string | false | null | undefined>) => values.filter(Boolean).join(" ");
