"""Convert the held documents the kit's parser cannot read faithfully to the markdown substrate (AP-02 Part C).

The units, the output directory and the strike band are in corpus/substrate.yaml (why each converter exists is there).
Each output is `<out_dir>/<id>.md` with frontmatter carrying the source path and sha256, the converter and its
version, the conversion time and, for strike_pdf, the number of characters dropped as struck. Deterministic and
offline: no network, no model call, so constitution section 15 does not apply; re-running rewrites the same bytes
apart from `converted_at`.

    /Users/brock/GitHub/squiddy/.venv/bin/python scripts/convert_substrate.py [--config corpus/substrate.yaml]
"""

from __future__ import annotations

import argparse
import hashlib
import html as html_lib
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
CONVERTER_VERSION = "1"   # bump when either converter's output changes for the same input

#: eCFR element -> markdown heading depth (the part, the subpart, the section; DIV9 is an appendix)
ECFR_HEADINGS = {"DIV5": 1, "DIV6": 2, "DIV7": 3, "DIV8": 3, "DIV9": 3}
#: eCFR elements whose text is a paragraph of the document
ECFR_PARAS = {"P", "FP", "PSPACE", "CITA", "SECAUTH", "PARAUTH", "HD1", "HD2", "HD3", "NOTE"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def ecfr_xml_to_markdown(xml_bytes: bytes) -> str:
    """GPO/eCFR bulk XML -> markdown: a heading per DIV with a HEAD, a paragraph per P-like element, a table as rows."""
    root = ET.fromstring(xml_bytes)
    out: list[str] = []

    def walk(el: ET.Element) -> None:
        tag = el.tag
        if tag in ECFR_HEADINGS:
            head = el.find("HEAD")
            if head is not None:
                out.append("#" * ECFR_HEADINGS[tag] + " " + _norm("".join(head.itertext())))
            for child in el:
                if child is not head:
                    walk(child)
            return
        if tag in ("AUTH", "SOURCE", "EDNOTE", "EXTRACT", "APPRO", "DIV"):
            for child in el:
                walk(child)
            return
        if tag == "HED":
            out.append(f"**{_norm(''.join(el.itertext()))}**")
            return
        if tag == "TABLE":
            for tr in el.iter("TR"):
                cells = [_norm("".join(c.itertext())) for c in tr if c.tag in ("TD", "TH")]
                out.append("| " + " | ".join(cells) + " |")
            return
        if tag in ECFR_PARAS:
            text = _norm("".join(el.itertext()))
            if text:
                out.append(text)
            return
        for child in el:   # an unregistered wrapper: descend, never drop its text silently
            walk(child)

    walk(root)
    return "\n\n".join(out) + "\n"


def strike_pdf_to_markdown(path: Path, band: dict) -> tuple[str, int]:
    """A PDF's text with every struck character dropped: (markdown, characters dropped). One `## Page N` per page;
    lines kept as the text layer orders them, so a struck word leaves no gap words cannot be read across."""
    import pypdfium2 as pdfium
    import pypdfium2.raw as raw

    pdf = pdfium.PdfDocument(str(path))
    pages, dropped = [], 0
    for pno in range(len(pdf)):
        page = pdf[pno]
        rules = []
        for obj in page.get_objects():
            if obj.type != raw.FPDF_PAGEOBJ_PATH:
                continue
            left, bottom, right, top = obj.get_bounds()
            if top - bottom <= band["max_rule_height_pt"] and right - left >= band["min_rule_width_pt"]:
                rules.append((left, right, (bottom + top) / 2))
        tp = page.get_textpage()
        chars = []
        for i in range(tp.count_chars()):
            ch = tp.get_text_range(i, 1)
            if ch.strip() == "":
                chars.append(ch)
                continue
            left, bottom, right, top = tp.get_charbox(i)
            height = max(top - bottom, 0.1)
            mid_x = (left + right) / 2
            struck = any(rl <= mid_x <= rr and band["band_low"] <= (y - bottom) / height <= band["band_high"]
                         for rl, rr, y in rules)
            if struck:
                dropped += 1
                continue
            chars.append(ch)
        text = "".join(chars).replace("\r\n", "\n").replace("\r", "\n")
        lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")]
        pages.append(f"## Page {pno + 1}\n\n" + "\n".join(ln for ln in lines if ln))
    return "\n\n".join(pages) + "\n", dropped


def html_docling_to_markdown(path: Path) -> str:
    """HTML -> markdown through docling: the converter the document-ingest registry measured for HTML (headings and
    tables kept, no raw-HTML leaks); GovInfo's US Code pages keep every subsection heading under it."""
    from docling.document_converter import DocumentConverter
    return DocumentConverter().convert(str(path)).document.export_to_markdown() + "\n"


def html_extent(raw: bytes) -> dict:
    """The document-ingest extent gate's two shallow features (Kohlschuetter et al., WSDM 2010): visible characters
    after tag and script removal, and the share of them inside <a> elements. Flags, never drops."""
    text = raw.decode("utf-8", "replace")
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
    anchors = " ".join(re.findall(r"(?is)<a\b[^>]*>(.*?)</a>", text))
    def visible(s: str) -> str:
        return re.sub(r"\s+", " ", html_lib.unescape(re.sub(r"(?s)<[^>]+>", " ", s))).strip()
    v, a = visible(text), visible(anchors)
    return {"visible_chars": len(v), "link_density": round(len(a) / len(v), 3) if v else 1.0}


def frontmatter(meta: dict) -> str:
    return "---\n" + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True) + "---\n\n"


def convert(config_path: Path, repo: Path = REPO) -> list[Path]:
    cfg = yaml.safe_load(config_path.read_text())
    out_dir = repo / cfg["out_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for unit in cfg["units"]:
        src = repo / unit["source"]
        if not src.is_file():
            raise SystemExit(f"FATAL: {unit['id']}: source {src} is not on disk (acquire it first)")
        meta = {"doc_id": unit["id"], "source_path": unit["source"], "source_sha256": sha256_file(src),
                "source_format": src.suffix.lstrip("."), "converter": f"aacps-ai-policy/{unit['converter']}",
                "converter_version": CONVERTER_VERSION,
                "converted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "evidence_class": "structural"}
        if unit["converter"] == "ecfr_xml":
            body = ecfr_xml_to_markdown(src.read_bytes())
        elif unit["converter"] == "strike_pdf":
            body, dropped = strike_pdf_to_markdown(src, cfg["strike"])
            meta["struck_chars_dropped"] = dropped
        elif unit["converter"] == "html_docling":
            body = html_docling_to_markdown(src)
            ext = html_extent(src.read_bytes())
            gate = cfg["extent_gate"]
            meta["extent"] = ext
            if ext["visible_chars"] < gate["min_visible_chars"] or ext["link_density"] > gate["max_link_density"]:
                meta["extent_flag"] = "thin_extent_suspected"
        elif unit["converter"] == "md_passthrough":
            text = src.read_text(encoding="utf-8")
            if text.startswith("---\n"):          # the acquisition's own frontmatter is kept, nested, as provenance
                end = text.index("\n---", 4)
                meta["acquisition_frontmatter"] = yaml.safe_load(text[4:end])
                text = text[end + 4:].lstrip("\n")
            body = text
        else:
            raise SystemExit(f"FATAL: {unit['id']}: unknown converter {unit['converter']!r} (conversion_gap: "
                             f"unknown_format)")
        out = out_dir / f"{unit['id']}{cfg['out_suffix']}"
        out.write_text(frontmatter(meta) + body, encoding="utf-8")
        visible = len(body)
        print(f"{unit['id']}: {visible} chars{', struck dropped ' + str(meta['struck_chars_dropped']) if 'struck_chars_dropped' in meta else ''} -> {out.relative_to(repo)}")
        written.append(out)
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", default=str(REPO / "corpus/substrate.yaml"))
    args = ap.parse_args(argv)
    convert(Path(args.config))
    return 0


if __name__ == "__main__":
    sys.exit(main())
