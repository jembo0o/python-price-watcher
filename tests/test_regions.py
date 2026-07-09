import unittest

from price_watcher.regions import get_steam_country_code, normalize_region


class RegionTests(unittest.TestCase):
    def test_normalize_region_supports_ukraine_aliases(self) -> None:
        self.assertEqual(normalize_region("ua"), "ua")
        self.assertEqual(normalize_region("Ukraine"), "ua")
        self.assertEqual(normalize_region("UKR"), "ua")

    def test_normalize_region_supports_eu_aliases(self) -> None:
        self.assertEqual(normalize_region("eu"), "eu")
        self.assertEqual(normalize_region("Europe"), "eu")
        self.assertEqual(normalize_region("eurozone"), "eu")

    def test_get_steam_country_code_maps_eu_to_germany_storefront(self) -> None:
        self.assertEqual(get_steam_country_code("eu"), "de")
        self.assertEqual(get_steam_country_code("europe"), "de")

    def test_get_steam_country_code_maps_ukraine_to_ua(self) -> None:
        self.assertEqual(get_steam_country_code("ukraine"), "ua")

    def test_normalize_region_rejects_blank_region(self) -> None:
        with self.assertRaises(ValueError):
            normalize_region(" ")


if __name__ == "__main__":
    unittest.main()
