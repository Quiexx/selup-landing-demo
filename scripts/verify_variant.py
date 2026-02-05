#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import re
import sys
from html.parser import HTMLParser
from pathlib import Path


EXCLUDED_TEXT_TAGS = {
    "script",
    "style",
    "svg",
    "defs",
}


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class VariantExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._stack: list[str] = []
        self.text_nodes: list[str] = []
        self.ids: set[str] = set()
        self.anchor_hrefs: set[str] = set()

    @property
    def _in_excluded_text_context(self) -> bool:
        return any(tag in EXCLUDED_TEXT_TAGS for tag in self._stack)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        self._stack.append(tag)
        in_svg_context = "svg" in self._stack

        for name, value in attrs:
            if not name:
                continue
            name_l = name.lower()
            if name_l == "id" and value and not in_svg_context:
                self.ids.add(value)
            if tag == "a" and name_l == "href" and value is not None:
                self.anchor_hrefs.add(value)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i] == tag:
                del self._stack[i:]
                return

    def handle_data(self, data: str) -> None:
        if self._in_excluded_text_context:
            return
        normalized = _normalize_text(data)
        if not normalized:
            return
        self.text_nodes.append(normalized)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract(path: Path) -> VariantExtractor:
    parser = VariantExtractor()
    parser.feed(_read_text(path))
    parser.close()
    return parser


def _diff_preview(a: list[str], b: list[str], limit: int = 10) -> str:
    out: list[str] = []
    max_len = max(len(a), len(b))
    shown = 0
    for i in range(max_len):
        av = a[i] if i < len(a) else "<missing>"
        bv = b[i] if i < len(b) else "<missing>"
        if av == bv:
            continue
        out.append(f"- idx {i}: base={av!r}")
        out.append(f"          var ={bv!r}")
        shown += 1
        if shown >= limit:
            break
    return "\n".join(out)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Verify that a landing variant keeps content identical to base.")
    ap.add_argument("base", type=Path, help="Base HTML file (e.g., index.html)")
    ap.add_argument("variant", type=Path, help="Variant HTML file to verify")
    ap.add_argument(
        "--unordered-text",
        action="store_true",
        help="Compare text nodes as a multiset (ignoring order). Useful when structure/layout changes.",
    )
    args = ap.parse_args(argv)

    base = args.base
    variant = args.variant
    if not base.exists():
        print(f"Base file not found: {base}", file=sys.stderr)
        return 2
    if not variant.exists():
        print(f"Variant file not found: {variant}", file=sys.stderr)
        return 2

    base_ex = extract(base)
    var_ex = extract(variant)

    ok = True

    if args.unordered_text:
        base_counter = Counter(base_ex.text_nodes)
        var_counter = Counter(var_ex.text_nodes)
        if base_counter != var_counter:
            ok = False
            missing = base_counter - var_counter
            extra = var_counter - base_counter
            print("Text nodes mismatch (unordered).", file=sys.stderr)
            print(f"Base text nodes: {len(base_ex.text_nodes)}", file=sys.stderr)
            print(f"Var  text nodes: {len(var_ex.text_nodes)}", file=sys.stderr)
            if missing:
                most_common_missing = missing.most_common(20)
                print("Missing text (top 20):", file=sys.stderr)
                for text, count in most_common_missing:
                    print(f"- {count}x {text!r}", file=sys.stderr)
            if extra:
                most_common_extra = extra.most_common(20)
                print("Extra text (top 20):", file=sys.stderr)
                for text, count in most_common_extra:
                    print(f"- {count}x {text!r}", file=sys.stderr)
    else:
        if base_ex.text_nodes != var_ex.text_nodes:
            ok = False
            print("Text nodes mismatch.", file=sys.stderr)
            print(f"Base text nodes: {len(base_ex.text_nodes)}", file=sys.stderr)
            print(f"Var  text nodes: {len(var_ex.text_nodes)}", file=sys.stderr)
            print(_diff_preview(base_ex.text_nodes, var_ex.text_nodes), file=sys.stderr)

    if base_ex.ids != var_ex.ids:
        ok = False
        missing = sorted(base_ex.ids - var_ex.ids)
        extra = sorted(var_ex.ids - base_ex.ids)
        print("ID set mismatch.", file=sys.stderr)
        if missing:
            print(f"Missing IDs ({len(missing)}): {missing[:30]}", file=sys.stderr)
        if extra:
            print(f"Extra IDs ({len(extra)}): {extra[:30]}", file=sys.stderr)

    if base_ex.anchor_hrefs != var_ex.anchor_hrefs:
        ok = False
        missing = sorted(base_ex.anchor_hrefs - var_ex.anchor_hrefs)
        extra = sorted(var_ex.anchor_hrefs - base_ex.anchor_hrefs)
        print("Anchor href set mismatch.", file=sys.stderr)
        if missing:
            print(f"Missing hrefs ({len(missing)}): {missing[:30]}", file=sys.stderr)
        if extra:
            print(f"Extra hrefs ({len(extra)}): {extra[:30]}", file=sys.stderr)

    if ok:
        print("OK")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
