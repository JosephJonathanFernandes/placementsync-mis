"""Tests for the information extraction engine (Module C)."""

from app.services.email_service.parser import parse_eml_bytes
from app.services.extraction_service.engine import ExtractionEngine


ENGINE = ExtractionEngine()


def _parse(eml_bytes: bytes):
    return parse_eml_bytes(eml_bytes)


def test_simple_paragraph_extraction():
    eml = b"""From: placement.coordinator@college.edu
To: ps@college.edu
Date: Mon, 02 Sep 2026 10:15:00 +0530
Subject: Placement Selections - TechNova Solutions

Name: Arjun Mehta
Registration Number: 22CS014
Branch: CSE
Job Role: Software Engineer
CTC: 12 LPA

Congratulations!
"""
    parsed = _parse(eml)
    data = ENGINE.extract_from_parsed_email(
        parsed_email=parsed, email_date=parsed.date
    )
    assert data.company_name == "TechNova Solutions"
    names = [s.name for s in data.students]
    assert "Arjun Mehta" in names
    arjun = next(s for s in data.students if s.name == "Arjun Mehta")
    assert arjun.registration_number == "22CS014"
    assert arjun.branch == "CSE"
    assert arjun.job_role == "Software Engineer"
    assert arjun.package == "12 LPA"


def test_bullet_list_multiple_students():
    eml = (
        """From: placement.coordinator@college.edu
Subject: Campus Placement Results - GlobalSoft Technologies

Selected candidates:
\u2022 Rajesh Kumar (Reg No: 22ECE027, ECE) - Role: Embedded Engineer - Package: 8 LPA
\u2022 Pooja Singh (Reg No: 22CSE056, CSE) - Role: DevOps Engineer - Package: 15 LPA
"""
    ).encode("utf-8")
    parsed = _parse(eml)
    data = ENGINE.extract_from_parsed_email(
        parsed_email=parsed, email_date=parsed.date
    )
    assert data.company_name == "GlobalSoft Technologies"
    names = [s.name for s in data.students]
    assert names == ["Rajesh Kumar", "Pooja Singh"]
    rajesh = next(s for s in data.students if s.name == "Rajesh Kumar")
    assert rajesh.registration_number == "22ECE027"
    assert rajesh.branch == "ECE"


def test_html_table_extraction():
    eml = b"""From: placements@university.edu
Subject: Selections - WebSpire Pvt Ltd
Content-Type: text/html; charset="utf-8"

<table>
<tr><th>Student Name</th><th>Reg No</th><th>Branch</th><th>Role</th><th>CTC</th></tr>
<tr><td>Kavita Nair</td><td>22IT088</td><td>IT</td><td>Full Stack Developer</td><td>14 LPA</td></tr>
<tr><td>Divya Joshi</td><td>22CSE099</td><td>CSE</td><td>Frontend Developer</td><td>13 LPA</td></tr>
</table>
"""
    parsed = _parse(eml)
    data = ENGINE.extract_from_parsed_email(
        parsed_email=parsed, email_date=parsed.date
    )
    assert data.company_name == "WebSpire Pvt Ltd"
    names = [s.name for s in data.students]
    assert "Kavita Nair" in names
    assert "Divya Joshi" in names
    kavita = next(s for s in data.students if s.name == "Kavita Nair")
    assert kavita.registration_number == "22IT088"
    assert kavita.branch == "IT"
    assert kavita.job_role == "Full Stack Developer"
    assert kavita.package == "14 LPA"


def test_forwarded_email():
    eml = b"""From: staff@college.edu
Subject: Fwd: Placement Selections - CloudEdge Inc

---------- Forwarded Message ----------
From: hr@cloudedge.com
Subject: Placement Selections - CloudEdge Inc

Name: Rahul Verma
Reg No: 22CSE045
Branch: CSE
Role: Cloud Engineer
Package: 20 LPA
"""
    parsed = _parse(eml)
    data = ENGINE.extract_from_parsed_email(
        parsed_email=parsed, email_date=parsed.date
    )
    assert data.company_name == "CloudEdge Inc"
    names = [s.name for s in data.students]
    assert "Rahul Verma" in names
    assert "Forwarded Message" not in names


def test_missing_fields_handled_gracefully():
    eml = b"""From: hr@company.edu
Subject: Placement News

We have completed the hiring process.
"""
    parsed = _parse(eml)
    data = ENGINE.extract_from_parsed_email(
        parsed_email=parsed, email_date=parsed.date
    )
    assert data.students == []
    assert "students" in data.missing_fields
    # No student names should be invented
    assert data.company_name is None


def test_no_invention_of_names_from_congratulations():
    eml = b"""From: coordinator@college.edu
Subject: Placement update

Dear Sir, congratulations on the event. Please contact John Smith for details.
"""
    parsed = _parse(eml)
    data = ENGINE.extract_from_parsed_email(
        parsed_email=parsed, email_date=parsed.date
    )
    # "John Smith" appears only in a congratulations/context line with no
    # selection structure; it must not be treated as a selected student.
    assert data.students == []


def test_multiple_companies_in_subject_picks_most_specific():
    eml = b"""From: hr@company.edu
Subject: Campus Placement - WebSpire Pvt Ltd

Selected candidate:
Name: Aria Khan
"""
    parsed = _parse(eml)
    data = ENGINE.extract_from_parsed_email(
        parsed_email=parsed, email_date=parsed.date
    )
    assert data.company_name == "WebSpire Pvt Ltd"


def test_confidence_is_between_zero_and_one():
    eml = b"""Subject: Selections - Acme Corp

Name: Aryan Das
Reg No: 22CS001
Branch: CSE
Role: Engineer
Package: 10 LPA
"""
    parsed = _parse(eml)
    data = ENGINE.extract_from_parsed_email(
        parsed_email=parsed, email_date=parsed.date
    )
    assert 0.0 <= data.confidence <= 1.0
    for s in data.students:
        assert 0.0 <= s.confidence <= 1.0


def test_empty_malformed_email_safe():
    data = ENGINE.extract(
        subject=None, body_text=None, body_html=None, email_date=None
    )
    assert data.students == []
    assert data.company_name is None
    assert data.confidence >= 0.0
