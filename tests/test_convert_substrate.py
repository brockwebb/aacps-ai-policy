"""scripts/convert_substrate.py: eCFR XML keeps sections and definitions; struck Maryland chapter text never survives."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("convert_substrate", REPO / "scripts/convert_substrate.py")
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)

XML = b"""<?xml version="1.0"?>
<DIV5 N="312" TYPE="PART"><HEAD>PART 312&#x2014;COPPA RULE</HEAD>
<AUTH><HED>Authority:</HED><PSPACE>15 U.S.C. 6501.</PSPACE></AUTH>
<DIV8 N="312.2" TYPE="SECTION"><HEAD>&#xA7; 312.2 Definitions.</HEAD>
<P><I>Child</I> means an individual under the age of 13.</P>
<WRAP><P>Nested text is kept.</P></WRAP>
</DIV8></DIV5>"""


def test_ecfr_sections_are_headings_and_every_paragraph_survives():
    md = cs.ecfr_xml_to_markdown(XML)
    assert "# PART 312—COPPA RULE" in md
    assert "### § 312.2 Definitions." in md
    assert "Child means an individual under the age of 13." in md
    assert "Nested text is kept." in md, "an unregistered wrapper must be descended, not dropped"
    assert "**Authority:**" in md


CH634 = REPO / "corpus/inbox/md-ch634-2026-ai-ready-schools-act.pdf"


@pytest.mark.skipif(not CH634.is_file(), reason="the held chapter PDF is gitignored; present in the primary checkout")
def test_struck_text_of_chapter_634_is_dropped_and_enacted_text_kept():
    band = yaml.safe_load((REPO / "corpus/substrate.yaml").read_text())["strike"]
    md, dropped = cs.strike_pdf_to_markdown(CH634, band)
    flat = " ".join(md.split())
    assert dropped > 0
    # 7-2202(E) as introduced (struck in passage): Morgan State certifies tools each year
    assert "EACH YEAR, MORGAN STATE UNIVERSITY" not in flat
    assert "TO CERTIFY THAT ARTIFICIAL INTELLIGENCE TOOLS" not in flat
    # 7-2202(E) as enacted (underlined): the Department's rubric, which each local system shall use
    assert "THE DEPARTMENT SHALL DEVELOP AND PUBLISH A RUBRIC" in flat
    assert "SHALL USE THE RUBRIC AND OTHER EVALUATIVE TOOLS" in flat
    # 7-2202(D)(1): "COUNTY BOARD" struck, "LOCAL SCHOOL SYSTEM" inserted
    assert "EACH LOCAL SCHOOL SYSTEM SHALL DESIGNATE" in flat
    assert "EACH COUNTY BOARD" not in flat
    # 7-2202(C), unamended: the 120-day clock
    assert "ON OR BEFORE 120 DAYS FROM THE DATE THAT THE DEPARTMENT" in flat
