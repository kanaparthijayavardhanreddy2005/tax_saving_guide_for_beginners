"""PostgreSQL database access and explicit schema/rule initialization."""

import json
import os
from pathlib import Path
import psycopg
from psycopg.rows import dict_row

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def get_db_connection() -> psycopg.Connection:
    """Open a PostgreSQL connection using the configured Supabase connection URL."""
    database_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not database_url:
        raise RuntimeError(
            "Database is not configured. Set DATABASE_URL to your Supabase PostgreSQL connection string."
        )

    return psycopg.connect(
        database_url,
        row_factory=dict_row,
        connect_timeout=10,
        prepare_threshold=None,
    )


def init_db() -> None:
    """Create missing tables from schema.sql when explicitly invoked."""
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_db_connection() as conn:
        for statement in schema.split(";"):
            if statement.strip():
                conn.execute(statement)


def seed_default_tax_rules() -> None:
    """Seed the built-in rules only when the tax_rules table is empty."""
    rules = [
        (
            "FY 2025-26", "Section 80C Deduction", "deduction",
            {"regime": "old", "eligible_instruments": ["EPF", "PPF", "ELSS", "Life Insurance", "Tuition Fee", "Home Loan Principal"]},
            150000.0, "Income Tax Act, 1961 - Section 80C", "2025-04-01",
        ),
        (
            "FY 2025-26", "Section 80D Health Insurance", "deduction",
            {"regime": "old", "self_limit": 25000, "senior_parent_limit": 50000, "max_total": 100000},
            100000.0, "Income Tax Act, 1961 - Section 80D", "2025-04-01",
        ),
        (
            "FY 2025-26", "Section 80CCD(1B) NPS Additional Deduction", "deduction",
            {"regime": "old", "tier": "Tier-1", "additional_over_80c": True},
            50000.0, "Income Tax Act, 1961 - Section 80CCD(1B)", "2025-04-01",
        ),
        (
            "FY 2025-26", "Section 24(b) Home Loan Interest", "deduction",
            {"regime": "old", "property_type": "self-occupied"},
            200000.0, "Income Tax Act, 1961 - Section 24(b)", "2025-04-01",
        ),
        (
            "FY 2025-26", "Section 80E Education Loan Interest", "deduction",
            {"regime": "old", "limit_type": "no_upper_cap", "duration_years": 8},
            None, "Income Tax Act, 1961 - Section 80E", "2025-04-01",
        ),
        (
            "FY 2025-26", "Section 80G Charitable Donations", "deduction",
            {"regime": "old", "modes": ["cheque", "digital", "demand_draft"]},
            None, "Income Tax Act, 1961 - Section 80G", "2025-04-01",
        ),
        (
            "FY 2025-26", "Standard Deduction (New Regime)", "standard_deduction",
            {"regime": "new", "employment_type": "salaried"},
            75000.0, "Finance Act 2024 / 2025 - Section 16(ia)", "2025-04-01",
        ),
        (
            "FY 2025-26", "Standard Deduction (Old Regime)", "standard_deduction",
            {"regime": "old", "employment_type": "salaried"},
            50000.0, "Finance Act 2019 / 2024 - Section 16(ia)", "2025-04-01",
        ),
        (
            "FY 2025-26", "Section 87A Rebate (New Regime)", "rebate",
            {"regime": "new", "max_taxable_income": 1200000.0, "marginal_relief": True},
            60000.0, "Income Tax Act, 1961 - Section 87A / Budget 2025", "2025-04-01",
        ),
        (
            "FY 2025-26", "Section 87A Rebate (Old Regime)", "rebate",
            {"regime": "old", "max_taxable_income": 500000.0},
            12500.0, "Income Tax Act, 1961 - Section 87A", "2025-04-01",
        ),
        (
            "FY 2024-25", "Section 87A Rebate (New Regime)", "rebate",
            {"regime": "new", "max_taxable_income": 700000.0, "marginal_relief": True},
            25000.0, "Finance Act 2023 / 2024 - Section 87A", "2024-04-01",
        ),
        (
            "FY 2024-25", "Standard Deduction (New Regime)", "standard_deduction",
            {"regime": "new", "employment_type": "salaried"},
            75000.0, "Budget 2024 - Section 16(ia)", "2024-07-23",
        ),
    ]

    with get_db_connection() as conn:
        count = conn.execute("SELECT COUNT(*) AS count FROM tax_rules").fetchone()["count"]
        if count == 0:
            conn.executemany(
                """
                INSERT INTO tax_rules
                    (financial_year, rule_name, rule_type, conditions, limits, source, effective_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    (fy, name, rule_type, json.dumps(conditions), limits, source, effective_date)
                    for fy, name, rule_type, conditions, limits, source, effective_date in rules
                ],
            )


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    init_db()
    seed_default_tax_rules()
    print("PostgreSQL schema is ready and default tax rules are seeded if needed.")
