from __future__ import annotations

import unittest

from app.rag.response_cache import ResponseCache


class ResponseCacheVersioningTests(unittest.TestCase):
    def test_cache_key_includes_catalog_index_prompt_and_model_versions(self) -> None:
        cache = ResponseCache()
        response = {"content": "cached"}
        versions = {
            "catalog_version": "catalog-v1",
            "index_version": "index-v1",
            "prompt_version": "prompt-v1",
            "model_version": "model-a",
        }
        cache.put(
            "Gio mo cua?",
            ["chunk-hours"],
            response,
            session_id="s1",
            **versions,
        )

        self.assertEqual(
            response,
            cache.get(
                "Gio mo cua?",
                ["chunk-hours"],
                session_id="s1",
                **versions,
            ),
        )

        for version_name, changed_value in (
            ("catalog_version", "catalog-v2"),
            ("index_version", "index-v2"),
            ("prompt_version", "prompt-v2"),
            ("model_version", "model-b"),
        ):
            changed_versions = {**versions, version_name: changed_value}
            with self.subTest(version_name=version_name):
                self.assertIsNone(
                    cache.get(
                        "Gio mo cua?",
                        ["chunk-hours"],
                        session_id="s1",
                        **changed_versions,
                    )
                )

    def test_menu_version_remains_a_compatible_catalog_version_alias(self) -> None:
        cache = ResponseCache()
        response = {"content": "legacy"}
        cache.put("hours", ["chunk-hours"], response, menu_version="menu-v1")

        self.assertEqual(
            response,
            cache.get("hours", ["chunk-hours"], catalog_version="menu-v1"),
        )


if __name__ == "__main__":
    unittest.main()
