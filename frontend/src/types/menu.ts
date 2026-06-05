export type MenuItem = {
  id: string;
  name: string;
  description: string;
  price: number;
  categoryName: string;
  imageUrl: string;
  isAvailable: boolean;
  tags: string[];
};

export type MenuCart = Record<string, number>;

