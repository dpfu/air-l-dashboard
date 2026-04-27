from scripts.classify import classify_post


def test_classify_cfp_with_deadline_tag():
    p = classify_post("CFP: Digital Culture Workshop", "Deadline: May 25, 2026")
    assert p.category == "call_for_papers"
    assert "cfp" in p.tags
    assert p.deadline is not None


def test_classify_job():
    p = classify_post("Postdoc Position in Internet Governance")
    assert p.category == "job"
    assert "postdoc" in p.tags
