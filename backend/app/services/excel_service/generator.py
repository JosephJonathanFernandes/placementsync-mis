"""Placement register Excel generation and synchronization.

Uses pandas + openpyxl. The register is append-only: approved records are
added without overwriting existing rows, and duplicates are avoided.
"""

from __future__ import annotations

import os
from typing import Any

import pandas as pd

COLUMNS = [
    "Sr. No.",
    "Student Name",
    "Registration No.",
    "Branch",
    "Company",
    "Role",
    "CTC",
    "Date",
    "Status",
]


class ExcelService:
    def __init__(self, file_path: str = "./exports/placement_register.xlsx"):
        self.file_path = file_path
        os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)

    def _empty_frame(self) -> pd.DataFrame:
        return pd.DataFrame(columns=COLUMNS)

    def _load_existing(self) -> pd.DataFrame:
        if os.path.exists(self.file_path):
            try:
                df = pd.read_excel(self.file_path)
                for col in COLUMNS:
                    if col not in df.columns:
                        df[col] = ""
                return df[COLUMNS]
            except Exception:
                return self._empty_frame()
        return self._empty_frame()

    def _save(self, df: pd.DataFrame) -> None:
        os.makedirs(os.path.dirname(self.file_path) or ".", exist_ok=True)
        with pd.ExcelWriter(self.file_path, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Placement Register")

    def _record_exists(self, df: pd.DataFrame, record: dict[str, Any]) -> bool:
        """A duplicate is same student + company + role.

        Records may use either display column keys ("Student Name") or
        snake_case keys ("student_name").
        """
        if df.empty:
            return False
        name = str(
            record.get("student_name", record.get("Student Name", ""))
        ).strip().lower()
        company = str(
            record.get("company_name", record.get("Company", ""))
        ).strip().lower()
        role = str(
            record.get("job_role", record.get("Role", ""))
        ).strip().lower()
        if not name or not company:
            return False
        mask = (
            df["Student Name"].astype(str).str.strip().str.lower() == name
        ) & (
            df["Company"].astype(str).str.strip().str.lower() == company
        ) & (
            df["Role"].fillna("").astype(str).str.strip().str.lower() == role
        )
        return bool(mask.any())

    def generate_from_records(
        self, records: list[dict[str, Any]], overwrite: bool = False
    ) -> dict[str, Any]:
        """Write records to the Excel register.

        If ``overwrite`` is False (default), existing rows are preserved and
        only new, non-duplicate records are appended.
        """
        existing = self._empty_frame() if overwrite else self._load_existing()

        new_rows: list[dict[str, Any]] = []
        start_sr = 1
        if not existing.empty:
            start_sr = int(pd.to_numeric(existing["Sr. No."], errors="coerce").max() or 0) + 1

        added = 0
        skipped = 0
        for idx, record in enumerate(records):
            if self._record_exists(existing, record):
                skipped += 1
                continue
            if self._record_exists(pd.DataFrame(new_rows), record):
                skipped += 1
                continue
            new_rows.append(
                {
                    "Sr. No.": start_sr + len(new_rows),
                    "Student Name": record.get("student_name", ""),
                    "Registration No.": record.get("registration_number", ""),
                    "Branch": record.get("branch", ""),
                    "Company": record.get("company_name", ""),
                    "Role": record.get("job_role", ""),
                    "CTC": record.get("package", ""),
                    "Date": record.get("selection_date", ""),
                    "Status": record.get("status", "Selected"),
                }
            )
            added += 1

        if new_rows:
            combined = pd.concat([existing, pd.DataFrame(new_rows)], ignore_index=True)
        else:
            combined = existing

        self._save(combined)

        return {
            "file_path": self.file_path,
            "added": added,
            "skipped_duplicates": skipped,
            "total_rows": len(combined),
        }

    def export_by_filter(
        self,
        records: list[dict[str, Any]],
        *,
        company: str | None = None,
        branch: str | None = None,
        status: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> pd.DataFrame:
        df = pd.DataFrame(records)
        if df.empty:
            return self._empty_frame()
        # Accept either display column keys or snake_case keys.
        KEY_ALIASES = {
            "student_name": "Student Name",
            "registration_number": "Registration No.",
            "branch": "Branch",
            "company_name": "Company",
            "job_role": "Role",
            "package": "CTC",
            "selection_date": "Date",
            "status": "Status",
        }
        rename: dict[str, str] = {}
        for col in df.columns:
            if col in COLUMNS:
                continue
            if col in KEY_ALIASES:
                rename[col] = KEY_ALIASES[col]
        if rename:
            df = df.rename(columns=rename)
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = ""
        mask = pd.Series(True, index=df.index)
        if company:
            mask &= df["Company"].astype(str).str.contains(company, case=False, na=False)
        if branch:
            mask &= df["Branch"].astype(str).str.contains(branch, case=False, na=False)
        if status:
            mask &= df["Status"].astype(str).str.contains(status, case=False, na=False)
        return df[mask][COLUMNS]
