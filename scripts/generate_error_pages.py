#!/usr/bin/env python3
"""
Generate the error reference of docs.tupana.ai from the error catalog.

The catalog (scripts/errors/error_catalog.json) is a copy of the backend's
single source of truth (pana-backend: packages/tupana-dte/src/tupana_dte/
errors/error_catalog.json). The API puts the same texts in its error
responses, so the pages can never say something the API does not.

It writes, for every code the API returns today (status "live"):

- api-reference/errors/<code>.mdx   one page per code
- api-reference/error-codes.mdx     the list of all codes, by section
- docs.json                         the pages, under the first "Errores" group

Usage:
    python3 scripts/generate_error_pages.py            # writes the files
    python3 scripts/generate_error_pages.py --check    # exits 1 if stale
    python3 scripts/generate_error_pages.py --catalog <path-to-backend-json>
                                                       # refreshes the copy first
"""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG_FILE = ROOT / "scripts" / "errors" / "error_catalog.json"
DOCS_JSON = ROOT / "docs.json"


class ErrorPages:
    BASE_URL = "https://docs.tupana.ai"
    FOLDER = "api-reference/errors"
    INDEX_PAGE = "api-reference/error-codes"
    FORMAT_PAGE = "api-reference/v2/errors"
    NAV_GROUP = "Códigos"
    GENERATED = (
        "{/* Generado por scripts/generate_error_pages.py desde el catálogo de "
        "errores. No editar a mano: se sobrescribe. */}"
    )

    def __init__(self, catalog):
        self.catalog = catalog
        self.live = {
            code: entry
            for code, entry in catalog["codes"].items()
            if entry["status"] == "live"
        }

    # -- files -----------------------------------------------------------------

    def files(self):
        """``{relative path: content}`` of every generated page."""
        pages = {
            f"{self.FOLDER}/{code}.mdx": self._code_page(code, entry)
            for code, entry in self.live.items()
        }
        pages[f"{self.INDEX_PAGE}.mdx"] = self._index_page()
        return pages

    def _statuses(self, entry):
        return ", ".join(str(status) for status in entry["http_status"])

    def _retry_line(self, entry):
        if not entry["retryable"]:
            return (
                "No. Repetir la misma solicitud va a fallar igual: primero hay "
                "que corregir la causa."
            )
        wait = entry.get("retry_after_seconds")
        if wait:
            return (
                f"Sí. Espera al menos {wait} segundos y reintenta; si el error "
                "sigue, aumenta la espera en cada intento."
            )
        return "Sí. Reintenta, aumentando la espera en cada intento."

    def _sample(self, code, entry):
        error = {
            "type": entry["type"],
            "code": code,
            "message": entry["description"],
            "suggested_action": entry["suggested_action"],
            "retryable": entry["retryable"],
        }
        if "retry_after_seconds" in entry:
            error["retry_after_seconds"] = entry["retry_after_seconds"]
        error["doc_url"] = f"{self.BASE_URL}/{self.FOLDER}/{code}"
        error["request_id"] = "req_8f3a9c2b1e7d4a60"
        return json.dumps({"error": error}, ensure_ascii=False, indent=2)

    @staticmethod
    def _prose(text):
        """Catalog text as MDX prose: ``<tu_api_key>`` or ``{id}`` would be
        read as a component or an expression and break the page."""
        for char, entity in (("<", "&lt;"), (">", "&gt;"), ("{", "&#123;"), ("}", "&#125;")):
            text = text.replace(char, entity)
        return text

    def _bullets(self, items):
        return "\n".join(f"- {self._prose(item)}" for item in items)

    def _code_page(self, code, entry):
        description = self._prose(entry["description"]).replace("'", "’")
        return "\n".join(
            [
                "---",
                f"title: '{code}'",
                f"sidebarTitle: '{code}'",
                f"description: '{entry['title']}. {description}'",
                "---",
                "",
                self.GENERATED,
                "",
                "| | |",
                "|---|---|",
                f"| **Código** | `{code}` |",
                f"| **Tipo** | `{entry['type']}` |",
                f"| **Estado HTTP** | {self._statuses(entry)} |",
                f"| **¿Reintentar?** | {'Sí' if entry['retryable'] else 'No'} |",
                "",
                "## Qué significa",
                "",
                f"**{entry['title']}.** {self._prose(entry['description'])}",
                "",
                "## Causas posibles",
                "",
                self._bullets(entry["causes"]),
                "",
                "## Cómo resolverlo",
                "",
                self._bullets(entry["solutions"]),
                "",
                "## ¿Conviene reintentar?",
                "",
                self._retry_line(entry),
                "",
                "## Respuesta de ejemplo",
                "",
                "El `message` puede variar según el caso; programa contra `code`.",
                "",
                "```json",
                self._sample(code, entry),
                "```",
                "",
                f"Ver [todos los códigos](/{self.INDEX_PAGE}) o el "
                f"[formato del error](/{self.FORMAT_PAGE}).",
                "",
            ]
        )

    def _index_page(self):
        lines = [
            "---",
            "title: 'Códigos de error'",
            "sidebarTitle: 'Todos los códigos'",
            "description: 'Lista de todos los códigos de error de la API de "
            "Tupana, con su causa, cómo resolverlo y si conviene reintentar.'",
            "---",
            "",
            self.GENERATED,
            "",
            "Cada error de la API trae un `code` estable y un `doc_url` que "
            "lleva a la página de ese código. Aquí están todos. El formato de "
            f"la respuesta está en [Errores](/{self.FORMAT_PAGE}).",
            "",
        ]
        for group, title in self.catalog["groups"].items():
            rows = [
                (code, entry)
                for code, entry in self.live.items()
                if entry["group"] == group
            ]
            if not rows:
                continue
            lines += [
                f"### {title}",
                "",
                "| Código | Qué significa | HTTP | ¿Reintentar? |",
                "|--------|---------------|:----:|:------------:|",
            ]
            for code, entry in rows:
                lines.append(
                    f"| [`{code}`](/{self.FOLDER}/{code}) | {entry['title']} | "
                    f"{self._statuses(entry)} | "
                    f"{'Sí' if entry['retryable'] else 'No'} |"
                )
            lines.append("")
        return "\n".join(lines)

    # -- navigation --------------------------------------------------------------

    def _nav_pages(self):
        return [
            self.INDEX_PAGE,
            {
                "group": self.NAV_GROUP,
                "pages": [f"{self.FOLDER}/{code}" for code in self.live],
            },
        ]

    def update_navigation(self, docs):
        """Lists the index and the code pages after the format page, in the
        first group of the navigation that holds it."""
        for version in docs["navigation"]["versions"]:
            for tab in version["tabs"]:
                for group in tab["groups"]:
                    pages = group.get("pages", [])
                    if self.FORMAT_PAGE in pages:
                        group["pages"] = [
                            self.FORMAT_PAGE,
                            *self._nav_pages(),
                            *self._other_pages(pages),
                        ]
                        return docs
        raise SystemExit(f"docs.json has no group with {self.FORMAT_PAGE}")

    def _other_pages(self, pages):
        """Pages of the group that this script does not own."""
        return [
            page
            for page in pages
            if page not in (self.FORMAT_PAGE, self.INDEX_PAGE)
            and not (isinstance(page, str) and page.startswith(self.FOLDER + "/"))
            and not (isinstance(page, dict) and page.get("group") == self.NAV_GROUP)
        ]


class ErrorPagesCommand:
    @classmethod
    def run(cls, argv):
        if "--catalog" in argv:
            shutil.copyfile(argv[argv.index("--catalog") + 1], CATALOG_FILE)
        pages = ErrorPages(json.loads(CATALOG_FILE.read_text(encoding="utf-8")))
        wanted = pages.files()
        docs = pages.update_navigation(
            json.loads(DOCS_JSON.read_text(encoding="utf-8"))
        )
        wanted["docs.json"] = json.dumps(docs, ensure_ascii=False, indent=2) + "\n"
        folder = ROOT / ErrorPages.FOLDER
        extra = (
            [p for p in folder.glob("*.mdx") if f"{ErrorPages.FOLDER}/{p.name}" not in wanted]
            if folder.exists()
            else []
        )
        stale = [
            path
            for path, content in wanted.items()
            if not (ROOT / path).exists()
            or (ROOT / path).read_text(encoding="utf-8") != content
        ]
        if "--check" in argv:
            if stale or extra:
                print("Stale error pages:", stale + [str(p.name) for p in extra])
                print("Run: python3 scripts/generate_error_pages.py")
                return 1
            print(f"Error pages are up to date ({len(pages.live)} codes).")
            return 0
        folder.mkdir(parents=True, exist_ok=True)
        for path in stale:
            (ROOT / path).write_text(wanted[path], encoding="utf-8")
        for path in extra:
            path.unlink()
        print(f"{len(pages.live)} codes: {len(stale)} files written, {len(extra)} removed.")
        return 0


if __name__ == "__main__":
    sys.exit(ErrorPagesCommand.run(sys.argv[1:]))
