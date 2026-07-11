import unittest
from pathlib import Path

from research.menu_seed import parse_restaurant_menu_seed


ROOT = Path(__file__).resolve().parents[2]


class MenuSeedTests(unittest.TestCase):
    def test_parser_reads_exactly_91_unique_items_and_13_categories(self):
        snapshot = parse_restaurant_menu_seed(
            ROOT / "backend" / "src" / "RestaurantQrAiOrdering.Api" / "Data" / "RestaurantMenuSeed.cs"
        )

        self.assertEqual(91, len(snapshot.items))
        self.assertEqual(91, len({item.id for item in snapshot.items}))
        self.assertEqual(13, len({item.category_id for item in snapshot.items}))
        self.assertEqual("Gỏi cuốn tôm thịt", snapshot.items[0].name)
        self.assertEqual("Cocktail chanh đào mật ong", snapshot.items[-1].name)


if __name__ == "__main__":
    unittest.main()
