#!/usr/bin/env python3
"""
Generate llms.txt and llms-full.txt for docs.tupana.ai.

- llms.txt      = scripts/llms/header.md + an index of every v2 page (title,
                  URL and description), read from docs.json.
- llms-full.txt = scripts/llms/header.md + every v2 page converted from MDX
                  to plain Markdown (snippets inlined) + the complete v2 API
                  reference rendered from the OpenAPI specs (operations,
                  parameters, request/response schemas and examples).

Usage:
    python3 scripts/generate_llms.py           # writes llms.txt and llms-full.txt
    python3 scripts/generate_llms.py --check   # exits 1 if the files are stale
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE_URL = "https://docs.tupana.ai"
HEADER_FILE = ROOT / "scripts" / "llms" / "header.md"
NAV_VERSION = "v2"
SPECS = [
    ("api-reference/openapi-v2.json", "https://api.tupana.ai/v2"),
    ("api-reference/openapi-payment-requests.json", "https://api.tupana.ai/v1"),
]
HTTP_METHODS = ("get", "post", "put", "patch", "delete")
CALLOUTS = {
    "Note": "Nota",
    "Warning": "Importante",
    "Tip": "Consejo",
    "Info": "Info",
    "Check": "Listo",
}


# --------------------------------------------------------------------------
# Navigation
# --------------------------------------------------------------------------


def load_nav_pages():
    """Return [(tab, group, page_path)] for the v2 navigation, deduplicated."""
    docs = json.loads((ROOT / "docs.json").read_text(encoding="utf-8"))
    version = next(
        v for v in docs["navigation"]["versions"] if v["version"] == NAV_VERSION
    )
    pages, seen = [], set()

    def walk_group(tab, group):
        for page in group.get("pages", []):
            if isinstance(page, str):
                if page not in seen:
                    seen.add(page)
                    pages.append((tab, group["group"], page))
            else:
                walk_group(tab, page)

    for tab in version["tabs"]:
        for group in tab.get("groups", []):
            walk_group(tab["tab"], group)
    return pages


def parse_frontmatter(text):
    match = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
    if not match:
        return {}, text
    meta = {}
    for line in match.group(1).splitlines():
        kv = re.match(r"^([A-Za-z_:\-]+):\s*(.*)$", line)
        if kv:
            meta[kv.group(1)] = kv.group(2).strip().strip("'\"")
    return meta, text[match.end():]


# --------------------------------------------------------------------------
# MDX -> Markdown
# --------------------------------------------------------------------------


def split_code_blocks(text):
    """Yield (is_code, chunk) so code fences are never transformed."""
    parts = re.split(r"(^```.*?^```[ \t]*$)", text, flags=re.S | re.M)
    for i, part in enumerate(parts):
        yield (i % 2 == 1), part


def inline_snippets(body, page_file):
    imports = {}
    for match in re.finditer(
        r"^import\s+(\w+)\s+from\s+['\"](/snippets/[^'\"]+)['\"];?\s*$", body, re.M
    ):
        imports[match.group(1)] = match.group(2)
    body = re.sub(r"^import\s+\w+\s+from\s+['\"][^'\"]+['\"];?[ \t]*$", "", body, flags=re.M)

    def replace(match):
        name, attrs = match.group(1), match.group(2) or ""
        if name not in imports:
            return match.group(0)
        snippet_path = ROOT / imports[name].lstrip("/")
        if not snippet_path.exists():
            return ""
        snippet = snippet_path.read_text(encoding="utf-8")
        props = dict(re.findall(r'(\w+)="([^"]*)"', attrs))
        for key, value in props.items():
            snippet = snippet.replace("{props.%s}" % key, value)
        return "\n" + snippet + "\n"

    return re.sub(r"<(\w+)((?:\s+\w+=\"[^\"]*\")*)\s*/>", replace, body, flags=re.S)


def mdx_to_markdown(body):
    out = []
    for is_code, chunk in split_code_blocks(body):
        if is_code:
            out.append(dedent_fence(chunk))
            continue
        text = chunk
        text = re.sub(r"\{/\*.*?\*/\}", "", text, flags=re.S)
        text = re.sub(r"<div style=\{\{.*?\}\}>", "", text, flags=re.S)
        text = re.sub(r"<iframe.*?/>", "", text, flags=re.S)
        text = re.sub(r"<img[^>]*alt=\"([^\"]*)\"[^>]*/?>", r"[Imagen: \1]", text)
        text = re.sub(r"<img[^>]*/?>", "", text)
        text = re.sub(
            r"<pre><code[^>]*>(.*?)</code></pre>", r"\n```\n\1\n```\n", text, flags=re.S
        )
        for tag, label in CALLOUTS.items():
            text = re.sub(r"<%s[^>]*>\s*" % tag, "\n> **%s:** " % label, text)
            text = text.replace("</%s>" % tag, "\n")
        text = re.sub(r"<Card[^>]*title=\"([^\"]*)\"[^>]*href=\"([^\"]*)\"[^>]*>",
                      r"\n**[\1](\2)**: ", text)
        text = re.sub(r"<Card[^>]*title=\"([^\"]*)\"[^>]*>", r"\n**\1**: ", text)
        text = re.sub(r"<(Step|Tab|Accordion)[^>]*title=\"([^\"]*)\"[^>]*>",
                      r"\n**\2**\n", text)
        text = re.sub(r"<Frame[^>]*caption=\"([^\"]*)\"[^>]*>", r"\n_\1_\n", text)
        text = re.sub(
            r"<ParamField\s+(\w+)=\"([^\"]*)\"([^>]*)>",
            lambda m: "\n- `%s` (%s%s): " % (
                m.group(2), m.group(1),
                ", " + re.search(r'type="([^"]*)"', m.group(3)).group(1)
                if re.search(r'type="([^"]*)"', m.group(3)) else ""),
            text,
        )
        text = re.sub(r"</?[A-Z][A-Za-z]*[^>]*>", "", text)
        text = re.sub(r"</?div[^>]*>", "", text)
        text = re.sub(r"<code>(.*?)</code>", r"`\1`", text)
        text = re.sub(r"\]\((/[^)\s]*)\)", lambda m: "](%s%s)" % (BASE_URL, m.group(1)), text)
        out.append(text)
    result = "".join(out)
    result = "\n".join(line.rstrip() for line in result.splitlines())
    return re.sub(r"\n{3,}", "\n\n", result).strip()


def dedent_fence(chunk):
    lines = chunk.splitlines()
    indent = min(
        (len(l) - len(l.lstrip()) for l in lines if l.strip()), default=0
    )
    return "\n".join(l[indent:] for l in lines)


def demote_headings(markdown):
    """Push page headings one level down (the page title is ##), outside code."""
    out = []
    for is_code, chunk in split_code_blocks(markdown):
        if not is_code:
            chunk = re.sub(r"^(#{1,5}) ", lambda m: "#" * (len(m.group(1)) + 1) + " ",
                           chunk, flags=re.M)
        out.append(chunk)
    return "".join(out)


def page_markdown(page):
    path = ROOT / (page + ".mdx")
    if not path.exists():
        return None, {}
    meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    body = inline_snippets(body, path)
    return mdx_to_markdown(body), meta


# --------------------------------------------------------------------------
# OpenAPI -> Markdown
# --------------------------------------------------------------------------


class SpecRenderer:
    def __init__(self, spec):
        self.spec = spec

    def resolve(self, node):
        seen = set()
        while isinstance(node, dict) and "$ref" in node:
            ref = node["$ref"]
            if ref in seen:
                break
            seen.add(ref)
            target = self.spec
            for part in ref.lstrip("#/").split("/"):
                target = target.get(part, {})
            node = target
        return node

    @staticmethod
    def ref_name(node):
        if isinstance(node, dict) and "$ref" in node:
            return node["$ref"].rsplit("/", 1)[-1]
        return None

    def type_label(self, schema):
        name = self.ref_name(schema)
        if name:
            return "`%s`" % name
        schema = schema or {}
        for combo in ("oneOf", "anyOf", "allOf"):
            if combo in schema:
                joiner = " + " if combo == "allOf" else " | "
                return joiner.join(self.type_label(s) for s in schema[combo])
        kind = schema.get("type", "object" if "properties" in schema else "any")
        if kind == "array":
            return "array de %s" % self.type_label(schema.get("items", {}))
        if schema.get("format"):
            kind = "%s (%s)" % (kind, schema["format"])
        if schema.get("nullable"):
            kind += ", nullable"
        return kind

    def schema_lines(self, schema, depth=0, max_depth=6):
        """Render nested properties as an indented list. $ref stops expansion."""
        lines = []
        if depth > max_depth or self.ref_name(schema):
            return lines
        schema = schema or {}
        if schema.get("type") == "array" and not self.ref_name(schema.get("items")):
            return self.schema_lines(schema.get("items", {}), depth, max_depth)
        for combo in ("allOf", "oneOf", "anyOf"):
            for i, sub in enumerate(schema.get(combo, [])):
                if combo != "allOf":
                    lines.append("%s- Opción %d: %s" % ("  " * depth, i + 1, self.type_label(sub)))
                    lines.extend(self.schema_lines(sub, depth + 1, max_depth))
                else:
                    lines.extend(self.schema_lines(sub, depth, max_depth))
        required = set(schema.get("required", []))
        for name, prop in (schema.get("properties") or {}).items():
            resolved = prop if self.ref_name(prop) else (prop or {})
            desc = (resolved.get("description") or "").strip().replace("\n", " ")
            extras = []
            if name in required:
                extras.append("requerido")
            enum = resolved.get("enum")
            if enum:
                extras.append("valores: " + ", ".join("`%s`" % e for e in enum))
            if "default" in resolved:
                extras.append("default: `%s`" % json.dumps(resolved["default"], ensure_ascii=False))
            if "example" in resolved and not isinstance(resolved["example"], (dict, list)):
                extras.append("ej: `%s`" % resolved["example"])
            for key, label in (("maxLength", "máx. largo"), ("minimum", "mín."),
                               ("maximum", "máx."), ("maxItems", "máx. ítems")):
                if key in resolved:
                    extras.append("%s %s" % (label, resolved[key]))
            line = "%s- `%s` (%s%s)" % (
                "  " * depth, name, self.type_label(prop),
                "; " + "; ".join(extras) if extras else "")
            if desc:
                line += ": " + desc
            lines.append(line)
            lines.extend(self.schema_lines(prop, depth + 1, max_depth))
        return lines

    def example_block(self, content):
        example = content.get("example")
        if example is None and content.get("examples"):
            first = next(iter(content["examples"].values()))
            example = self.resolve(first).get("value")
        if example is None:
            return []
        return ["```json", json.dumps(example, ensure_ascii=False, indent=2), "```"]

    def operation(self, method, path, op, server):
        title = op.get("summary") or op.get("operationId") or path
        prefix = "/" + server.rstrip("/").rsplit("/", 1)[-1]
        lines = ["### %s %s%s" % (method.upper(), prefix, path),
                 "", "**%s**" % title, ""]
        if op.get("description"):
            lines += [op["description"].strip(), ""]
        lines += ["URL completa: `%s %s%s`" % (method.upper(), server, path), ""]
        params = [self.resolve(p) for p in op.get("parameters", [])]
        if params:
            lines += ["Parámetros:", ""]
            for p in params:
                schema = p.get("schema", {})
                desc = (p.get("description") or "").strip().replace("\n", " ")
                extra = []
                if p.get("required"):
                    extra.append("requerido")
                if schema.get("enum"):
                    extra.append("valores: " + ", ".join("`%s`" % e for e in schema["enum"]))
                if "default" in schema:
                    extra.append("default: `%s`" % json.dumps(schema["default"], ensure_ascii=False))
                lines.append("- `%s` (%s, %s%s)%s" % (
                    p.get("name"), p.get("in"), self.type_label(schema),
                    "; " + "; ".join(extra) if extra else "",
                    ": " + desc if desc else ""))
            lines.append("")
        body = self.resolve(op.get("requestBody")) if op.get("requestBody") else None
        if body:
            for mime, content in body.get("content", {}).items():
                schema = content.get("schema", {})
                lines += ["Cuerpo (`%s`): %s" % (mime, self.type_label(schema)), ""]
                lines += self.schema_lines(self.resolve(schema)) + [""]
                example = self.example_block(content)
                if example:
                    lines += ["Ejemplo de cuerpo:", ""] + example + [""]
        for status, resp in (op.get("responses") or {}).items():
            resp = self.resolve(resp)
            lines.append("Respuesta `%s`: %s" % (status, (resp.get("description") or "").strip()))
            for mime, content in (resp.get("content") or {}).items():
                schema = content.get("schema")
                if schema:
                    lines.append("")
                    lines.append("Esquema: %s" % self.type_label(schema))
                example = self.example_block(content)
                if example:
                    lines += [""] + example
            lines.append("")
        return lines

    def render(self, server):
        info = self.spec.get("info", {})
        lines = ["## %s (OpenAPI %s)" % (info.get("title", "API"), info.get("version", "")), ""]
        if info.get("description"):
            lines += [info["description"].strip(), ""]
        lines += ["Servidor base: `%s`" % server, ""]
        for scheme in (self.spec.get("components", {}).get("securitySchemes") or {}).values():
            lines += ["Autenticación: header `%s`. %s" % (
                scheme.get("name", "Authorization"), scheme.get("description", "")), ""]
        for path, item in self.spec.get("paths", {}).items():
            for method in HTTP_METHODS:
                if method in item:
                    lines += self.operation(method, path, item[method], server)
        schemas = self.spec.get("components", {}).get("schemas", {})
        if schemas:
            lines += ["### Esquemas de %s" % info.get("title", "la API"), ""]
            for name, schema in schemas.items():
                lines += ["#### `%s`" % name, ""]
                if schema.get("description"):
                    lines += [schema["description"].strip(), ""]
                lines.append("Tipo: %s" % self.type_label(schema))
                lines += [""] + self.schema_lines(schema) + [""]
                if "example" in schema:
                    lines += ["```json", json.dumps(schema["example"], ensure_ascii=False, indent=2), "```", ""]
        return lines


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


def build():
    header = HEADER_FILE.read_text(encoding="utf-8").strip()
    pages = load_nav_pages()

    index = ["", "## Índice de páginas (API v2)", ""]
    current_tab = None
    for tab, group, page in pages:
        if tab != current_tab:
            index += ["", "### %s" % tab, ""]
            current_tab = tab
        path = ROOT / (page + ".mdx")
        meta = parse_frontmatter(path.read_text(encoding="utf-8"))[0] if path.exists() else {}
        title = meta.get("title", page)
        url = BASE_URL + ("/" if page == "index" else "/" + page)
        desc = meta.get("description", "")
        index.append("- [%s](%s)%s" % (title, url, ": " + desc if desc else ""))
    llms = header + "\n" + "\n".join(index).rstrip() + "\n"

    full = [header, "", "---", "",
            "# Parte 1: guías y páginas de la documentación (v2)", ""]
    for tab, group, page in pages:
        markdown, meta = page_markdown(page)
        if markdown is None:
            continue
        url = BASE_URL + ("/" if page == "index" else "/" + page)
        full += ["", "---", "",
                 "## %s" % meta.get("title", page), "",
                 "Fuente: %s · Sección: %s / %s" % (url, tab, group), ""]
        if meta.get("description"):
            full += ["> %s" % meta["description"], ""]
        if meta.get("openapi"):
            full += ["Endpoint: `%s` (detalle completo en la Parte 2)." % meta["openapi"].split(" ", 1)[-1], ""]
        full.append(demote_headings(markdown))
    full += ["", "---", "", "# Parte 2: referencia completa de la API (generada desde OpenAPI)", ""]
    for spec_path, server in SPECS:
        spec = json.loads((ROOT / spec_path).read_text(encoding="utf-8"))
        full += SpecRenderer(spec).render(server)
    full_text = re.sub(r"\n{3,}", "\n\n", "\n".join(full)).strip() + "\n"
    return llms, full_text


def main():
    llms, full = build()
    targets = {ROOT / "llms.txt": llms, ROOT / "llms-full.txt": full}
    if "--check" in sys.argv:
        stale = [p.name for p, c in targets.items()
                 if not p.exists() or p.read_text(encoding="utf-8") != c]
        if stale:
            print("Desactualizados: %s. Corre python3 scripts/generate_llms.py" % ", ".join(stale))
            sys.exit(1)
        print("llms.txt y llms-full.txt al día.")
        return
    for path, content in targets.items():
        path.write_text(content, encoding="utf-8")
        print("%s: %d bytes" % (path.name, len(content.encode("utf-8"))))


if __name__ == "__main__":
    main()
