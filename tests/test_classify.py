from scripts.classify import classify_post, detect_deadline


def test_classify_cfp_with_deadline_tag():
    p = classify_post("CFP: Digital Culture Workshop", "Deadline: May 25, 2026")
    assert p.category == "call_for_papers"
    assert "cfp" in p.tags
    assert p.deadline is not None


def test_classify_job():
    p = classify_post("Postdoc Position in Internet Governance")
    assert p.category == "job"
    assert "postdoc" in p.tags
    assert classify_post("PhD in Feminist Software Design: Fully Funded, Uni of Amsterdam").category == "job"
    assert classify_post("Call for Digital Sovereignty Visiting Fellow at United Nations University").category == "job"
    assert classify_post("Call for Applications: Assistant Managing Editor (JCEA, 2026-2028)").category == "job"


def test_classify_publication_for_book_and_published_special_issue():
    assert classify_post("New Book Announcement: Platform Studies").category == "publication"
    assert classify_post("Special Issue Published - Digital Resilience").category == "publication"


def test_classify_cfp_special_issue_when_submission_signal_present():
    p = classify_post("CfP special issue on mobile disconnection and online events")
    assert p.category == "call_for_papers"
    assert "cfp" in p.tags
    assert classify_post("Final Call for Posters, Demos, and Work-in-Progress Contributions").category == "call_for_papers"
    assert classify_post("Call-for Papers for an Online Conference and Publication").category == "call_for_papers"
    assert classify_post("International Conference: Last Call for Research Papers").category == "call_for_papers"
    assert classify_post("37th IEEE Symposium: Second Call for Workshop Proposals").category == "call_for_papers"
    assert classify_post("Submissions Now Open for AoIR2026").category == "call_for_papers"
    assert classify_post("Submit your abstracts by April 30").category == "call_for_papers"
    assert classify_post("Call for Chapter Proposals - Handbook Gray Zones").category == "call_for_papers"
    assert classify_post("Last Call for ICA Mobile Comm Preconference Submissions").category == "call_for_papers"


def test_classify_events_without_treating_all_calls_as_events():
    assert classify_post("Webinar on AI Influencers").category == "event"
    assert classify_post("Book launch: The Many Faces of Data Access").category == "event"
    assert classify_post("Event Invitation | How to Demystify AI | 17 March 2026").category == "event"
    assert classify_post("invite: Governance by Data Infrastructure at the University of Amsterdam (27 March)").category == "event"
    assert classify_post("Building a Feminist Research Career in Anti-Feminist Times - 10 June at King's College London").category == "event"
    assert classify_post("AI Justice Public Lecture - Professor Sanjay Sharma on Inclusive AI").category == "event"
    assert classify_post("ISOC LIVE - What’s On & What’s New - Apr 21 2026").category == "event"
    assert classify_post("Panel on Censorship and Freedom of Expression at the Cambridge Disinformation Summit").category == "event"
    assert classify_post("Last call for registration to The Digital Conference for paper presenters").category == "event"


def test_classify_publication_for_reports():
    assert classify_post("Governing AI Search: New AI Forensics Policy Report").category == "publication"
    assert classify_post("New Reports on Extended Reality Research").category == "publication"


def test_classify_rest_as_other():
    assert classify_post("ARPANET resurrection update and possible significances?").category == "other"
    assert classify_post("Hype Literacy Toolkit").category == "other"
    assert classify_post("Multi-author-position paper").category == "other"
    assert classify_post("Call for Participants: AI and News in UK").category == "other"
    assert classify_post("RECORDING - State of the Internet 2026").category == "other"
    assert classify_post("RECORDING - ICANN85 Community Forum").category == "other"
    assert classify_post("Inquiry: PhD Opportunities Starting in the Next Year").category == "other"
    assert classify_post("LaborTech Call for Award Nominations--Book, Grad Student Paper, Social Justice").category == "other"
    assert classify_post("2 year appt. in AI and Information Literacies").category == "other"


def test_body_does_not_override_specific_subject_category():
    body = "Quoted footer mentions jobs, professor positions, and conference deadlines."
    assert classify_post("ARPANET resurrection update and possible significances?", body).category == "other"


def test_detect_dates_uses_reference_year_and_filters_implausible_dates():
    p = classify_post(
        "Hybrid book launch on April 8",
        "Deadline: April 8. Historic network demo on October 29, 1969. Due April 24, 2126.",
        reference_date="2026-04-04T01:56:11Z",
    )
    assert p.deadline == "2026-04-08"
    assert p.event_date is None


def test_cfp_deadline_prefers_submission_context_over_event_dates():
    p = classify_post(
        "CFP: Foo conference January 2027",
        "Submission deadline: June 15, 2026\nConference dates: January 4-8, 2027",
        reference_date="2026-04-01T00:00:00Z",
    )
    assert p.deadline == "2026-06-15"


def test_deadline_detector_handles_day_month_and_ordinal_dates():
    assert detect_deadline("Deadline 17th April 2026 is approaching!", "2026-04-10T00:00:00Z") == "2026-04-17"
    assert detect_deadline("Submission Deadline: 22nd March 2026", "2026-03-01T00:00:00Z") == "2026-03-22"
    assert detect_deadline("15 MAR Deadline", "2026-03-01T00:00:00Z") == "2026-03-15"


def test_deadline_detector_chooses_earliest_action_deadline():
    body = "Important dates\nDeadline for abstracts: 15 March 2026\nFull papers due: 15 May 2026\nConference: July 7, 2026"
    assert classify_post("Call for papers", body, reference_date="2026-02-01T00:00:00Z").deadline == "2026-03-15"


def test_cfp_without_deadline_context_does_not_use_event_date_as_deadline():
    p = classify_post(
        "CfP Synthetic Social Media: Studying Platform-Embedded AI 22-25 September 2026",
        "Workshop dates: 22-25 September 2026",
        reference_date="2026-03-20T00:00:00Z",
    )
    assert p.deadline is None
