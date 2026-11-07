"""Tests for the Excel placement register service (Module F)."""

import os

import pandas as pd

from app.services.excel_service.generator import ExcelService, COLUMNS

RECORDS = [
    {
        "student_name": "Arjun Mehta",
        "registration_number": "22CS014",
        "branch": "CSE",
        "company_name": "TechNova Solutions",
        "job_role": "Software Engineer",
        "package": "12 LPA",
        "selection_date": "2026-09-02",
        "status": "Selected",
    },
    {
        "student_name": "Sneha Reddy",
        "registration_number": "22IT033",
        "branch": "IT",
        "company_name": "TechNova Solutions",
        "job_role": "Frontend Developer",
        "package": "10 LPA",
        "selection_date": "2026-09-02",
        "status": "Selected",
    },
]


def _remove(path: str) -> None:
    if os.path.exists(path):
        os.remove(path)


def test_create_and_append_records():
    path = "./.test_excel_register.xlsx"
    _remove(path)
    try:
        service = ExcelService(file_path=path)
        result = service.generate_from_records(RECORDS, overwrite=False)
        assert result["added"] == 2
        assert result["skipped_duplicates"] == 0
        assert result["total_rows"] == 2

        df = pd.read_excel(path)
        assert list(df.columns) == COLUMNS
        assert len(df) == 2
        assert df.iloc[0]["Student Name"] == "Arjun Mehta"
        assert df.iloc[0]["CTC"] == "12 LPA"
    finally:
        _remove(path)


def test_duplicates_are_skipped():
    path = "./.test_excel_register_dup.xlsx"
    _remove(path)
    try:
        service = ExcelService(file_path=path)
        first = service.generate_from_records(RECORDS, overwrite=False)
        second = service.generate_from_records(RECORDS, overwrite=False)
        assert first["added"] == 2
        assert second["added"] == 0
        assert second["skipped_duplicates"] == 2
        df = pd.read_excel(path)
        assert len(df) == 2
    finally:
        _remove(path)


def test_overwrite_mode_replaces_file():
    path = "./.test_excel_register_ovw.xlsx"
    _remove(path)
    try:
        service = ExcelService(file_path=path)
        service.generate_from_records(RECORDS[:1], overwrite=False)
        result = service.generate_from_records(RECORDS[1:], overwrite=True)
        assert result["added"] == 1
        df = pd.read_excel(path)
        assert len(df) == 1
        assert df.iloc[0]["Student Name"] == "Sneha Reddy"
    finally:
        _remove(path)


def test_export_by_filter():
    path = "./.test_excel_register_filter.xlsx"
    _remove(path)
    try:
        service = ExcelService(file_path=path)
        service.generate_from_records(RECORDS, overwrite=False)
        filtered = service.export_by_filter(
            RECORDS, company="TechNova", branch="CSE"
        )
        assert len(filtered) == 1
        assert filtered.iloc[0]["Student Name"] == "Arjun Mehta"
    finally:
        _remove(path)
