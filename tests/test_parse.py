from scripts.scrape import parse_month_page


def test_parse_month_page_extracts_id_and_subject():
    html = '<html><body><a href="000123.html">Example Subject</a></body></html>'
    rows = parse_month_page(html, "http://listserv.aoir.org/pipermail/air-l-aoir.org/2026-April/date.html")
    assert rows[0]["id"] == "000123"
    assert rows[0]["subject"] == "Example Subject"
