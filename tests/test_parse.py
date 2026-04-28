import argparse

import pytest

from scripts.scrape import extract_transient_detail, month_slug_from_arg, parse_month_page, parse_thread_page


def test_parse_month_page_extracts_id_and_subject():
    html = '<html><body><a href="000123.html">Example Subject</a></body></html>'
    rows = parse_month_page(html, "http://listserv.aoir.org/pipermail/air-l-aoir.org/2026-April/date.html")
    assert rows[0]["id"] == "000123"
    assert rows[0]["subject"] == "Example Subject"


def test_extract_transient_detail_parses_pipermail_timezone():
    html = """
    <html><body>
      <i>Mon Apr 27 12:13:09 PDT 2026</i>
      <pre>Temporary body only.</pre>
    </body></html>
    """
    body, date = extract_transient_detail(html)
    assert body == "Temporary body only."
    assert date == "2026-04-27T19:13:09Z"


def test_parse_thread_page_extracts_pipermail_thread_path():
    html = """
    <!--0 01775884830.195834- -->
    <LI><A HREF="195834.html">Root</A><A NAME="195834">&nbsp;</A>
    <UL>
    <!--1 01775884830.195834-01775893989.195835- -->
    <LI><A HREF="195835.html">Reply</A><A NAME="195835">&nbsp;</A>
    </UL>
    """
    threads = parse_thread_page(html)
    assert threads["195834"]["thread_id"] == "195834"
    assert threads["195834"]["depth"] == 0
    assert threads["195834"]["parent_id"] is None
    assert threads["195835"]["thread_id"] == "195834"
    assert threads["195835"]["depth"] == 1
    assert threads["195835"]["parent_id"] == "195834"


def test_month_slug_from_arg_accepts_year_month():
    assert month_slug_from_arg("2026-01") == "2026-January"
    assert month_slug_from_arg("2026-03") == "2026-March"


def test_month_slug_from_arg_rejects_invalid_month():
    with pytest.raises(argparse.ArgumentTypeError):
        month_slug_from_arg("2026-13")
