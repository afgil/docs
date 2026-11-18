#!/usr/bin/env python3
"""Tests for generate_error_pages.py: one page per live error code, an index
that links every one of them, and a navigation that lists them."""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from generate_error_pages import ErrorPages  # noqa: E402

CATALOG = {
    "types": {"rate_limit_error": "Demasiadas solicitudes.", "sii_error": "SII."},
    "groups": {"limits": "Límites", "sii": "SII"},
    "codes": {
        "rate_limited": {
            "type": "rate_limit_error",
            "http_status": [429],
            "group": "limits",
            "status": "live",
            "title": "Demasiadas solicitudes",
            "description": "Superaste el límite.",
            "causes": ["Un ciclo sin pausas."],
            "solutions": ["Espera y reintenta."],
            "suggested_action": "Espera los segundos de Retry-After.",
            "retryable": True,
            "retry_after_seconds": 5,
            "responsibility": "client",
        },
        "folios_exhausted": {
            "type": "sii_error",
            "http_status": [400],
            "group": "sii",
            "status": "planned",
            "title": "Sin folios",
            "description": "No quedan folios.",
            "causes": ["Se usaron todos."],
            "solutions": ["Pide más."],
            "suggested_action": "Pide más folios.",
            "retryable": False,
            "responsibility": "client",
        },
    },
}
NAVIGATION = {
    "navigation": {
        "versions": [
            {
                "version": "v2",
                "tabs": [
                    {
                        "tab": "API",
                        "groups": [
                            {"group": "Errores", "pages": ["api-reference/v2/errors"]}
                        ],
                    },
                    {
                        "tab": "Otra",
                        "groups": [
                            {"group": "Errores", "pages": ["api-reference/v2/errors"]}
                        ],
                    },
                ],
            }
        ]
    }
}


class TestErrorPages(unittest.TestCase):
    def setUp(self):
        self.pages = ErrorPages(CATALOG)

    def test_only_live_codes_get_a_page(self):
        files = self.pages.files()
        self.assertIn("api-reference/errors/rate_limited.mdx", files)
        self.assertNotIn("api-reference/errors/folios_exhausted.mdx", files)

    def test_code_page_has_every_section_and_the_sample_response(self):
        page = self.pages.files()["api-reference/errors/rate_limited.mdx"]
        for heading in (
            "## Qué significa",
            "## Causas posibles",
            "## Cómo resolverlo",
            "## ¿Conviene reintentar?",
            "## Respuesta de ejemplo",
        ):
            self.assertIn(heading, page)
        self.assertIn("Un ciclo sin pausas.", page)
        self.assertIn('"code": "rate_limited"', page)
        self.assertIn('"retry_after_seconds": 5', page)
        self.assertIn(
            '"doc_url": "https://docs.tupana.ai/api-reference/errors/rate_limited"',
            page,
        )
        self.assertNotIn("responsibility", page)
        self.assertNotIn("client", page)

    def test_angle_brackets_in_the_catalog_do_not_break_the_page(self):
        catalog = json.loads(json.dumps(CATALOG))
        catalog["codes"]["rate_limited"]["solutions"] = ["Envía Api-Key <tu_api_key>."]
        page = ErrorPages(catalog).files()["api-reference/errors/rate_limited.mdx"]
        self.assertIn("Api-Key &lt;tu_api_key&gt;.", page)

    def test_index_links_every_live_code_and_no_planned_one(self):
        index = self.pages.files()["api-reference/error-codes.mdx"]
        self.assertIn("[`rate_limited`](/api-reference/errors/rate_limited)", index)
        self.assertIn("### Límites", index)
        self.assertNotIn("folios_exhausted", index)
        self.assertNotIn("### SII", index)

    def test_navigation_lists_index_and_codes_once_in_the_first_errors_group(self):
        docs = json.loads(json.dumps(NAVIGATION))
        self.pages.update_navigation(docs)
        tabs = docs["navigation"]["versions"][0]["tabs"]
        first = tabs[0]["groups"][0]["pages"]
        self.assertEqual(first[0], "api-reference/v2/errors")
        self.assertEqual(first[1], "api-reference/error-codes")
        self.assertEqual(
            first[2],
            {"group": "Códigos", "pages": ["api-reference/errors/rate_limited"]},
        )
        self.assertEqual(tabs[1]["groups"][0]["pages"], ["api-reference/v2/errors"])

    def test_updating_the_navigation_twice_changes_nothing(self):
        docs = json.loads(json.dumps(NAVIGATION))
        self.pages.update_navigation(docs)
        once = json.dumps(docs)
        self.pages.update_navigation(docs)
        self.assertEqual(json.dumps(docs), once)


if __name__ == "__main__":
    unittest.main()
