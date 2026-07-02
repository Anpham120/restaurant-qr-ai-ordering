import { menuItems } from "../mocks/menuItems";

function normalizeVN(text: string) {
  return text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/gi, "d")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function getFallbackImage(index: number) {
  return menuItems[index % menuItems.length]?.imageUrl ?? menuItems[0]?.imageUrl ?? "";
}

function isUsableImageUrl(imageUrl?: string | null) {
  if (!imageUrl) {
    return false;
  }
  return !/example\.com/i.test(imageUrl);
}

const imageByNormName = new Map(menuItems.map((item) => [normalizeVN(item.name), item.imageUrl]));

const keywordImages: Array<[string[], string]> = [
  [["com ga", "ga xoi"], menuItems.find((item) => normalizeVN(item.name).includes("bo luc lac"))?.imageUrl ?? ""],
  [["com suon", "suon nuong"], menuItems.find((item) => normalizeVN(item.name).includes("nem ran"))?.imageUrl ?? ""],
  [["cha gio"], menuItems.find((item) => normalizeVN(item.name).includes("nem ran"))?.imageUrl ?? ""],
  [["banh flan", "flan"], menuItems.find((item) => normalizeVN(item.name).includes("che khuc bach"))?.imageUrl ?? ""],
  [["bun bo"], menuItems.find((item) => normalizeVN(item.name).includes("pho bo"))?.imageUrl ?? ""],
  [["ca phe"], menuItems.find((item) => normalizeVN(item.name).includes("ca phe"))?.imageUrl ?? ""],
  [["tra dao"], menuItems.find((item) => normalizeVN(item.name).includes("tra dao"))?.imageUrl ?? ""],
];

export function resolveMenuImage(name: string, imageUrl?: string | null, index = 0) {
  if (isUsableImageUrl(imageUrl)) {
    return imageUrl!;
  }

  const normName = normalizeVN(name);
  const exact = imageByNormName.get(normName);
  if (exact) {
    return exact;
  }

  for (const [key, url] of imageByNormName) {
    if (key.includes(normName) || normName.includes(key)) {
      return url;
    }
  }

  for (const [keywords, url] of keywordImages) {
    if (url && keywords.some((keyword) => normName.includes(keyword))) {
      return url;
    }
  }

  return getFallbackImage(index);
}
