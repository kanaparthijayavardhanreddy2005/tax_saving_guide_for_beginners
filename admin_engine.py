"""
TaxWise AI - Admin Dashboard & Rule Management Engine
Allows authorized administrators to:
- View and manage versioned tax rules (FY 2024-25, FY 2025-26)
- Ingest and review knowledge-base documents
- Monitor system statistics, queries, and failed retrievals
- Ensure data integrity and rule currency
"""

import json
from typing import Dict, List, Any, Optional
from database import get_db_connection
from rag_engine import KNOWLEDGE_DOCUMENTS, VectorKnowledgeBase


def get_system_statistics() -> Dict[str, Any]:
    """Retrieves operational telemetry and knowledge metrics."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) AS count FROM users")
        user_count = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) AS count FROM tax_profiles")
        profile_count = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) AS count FROM tax_rules")
        rules_count = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) AS count FROM chat_history")
        chat_count = cursor.fetchone()["count"]

        cursor.execute("SELECT DISTINCT financial_year FROM tax_rules")
        active_fys = [r["financial_year"] for r in cursor.fetchall()]

        return {
            "total_users": user_count,
            "profiles_created": profile_count,
            "tax_rules_configured": rules_count,
            "chat_queries_handled": chat_count,
            "knowledge_base_documents": len(KNOWLEDGE_DOCUMENTS),
            "supported_financial_years": active_fys if active_fys else ["FY 2024-25", "FY 2025-26"],
            "system_health": "Optimal",
            "retrieval_status": "Active (Hybrid Vector Space TF-IDF)"
        }
    finally:
        conn.close()


def get_all_tax_rules(financial_year: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves versioned tax rules from database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if financial_year:
            cursor.execute("SELECT * FROM tax_rules WHERE financial_year = %s ORDER BY id ASC", (financial_year,))
        else:
            cursor.execute("SELECT * FROM tax_rules ORDER BY financial_year DESC, id ASC")

        rows = cursor.fetchall()
        rules = []
        for r in rows:
            rules.append({
                "id": r["id"],
                "financial_year": r["financial_year"],
                "rule_name": r["rule_name"],
                "rule_type": r["rule_type"],
                "conditions": json.loads(r["conditions"]) if r["conditions"] else {},
                "limits": r["limits"],
                "source": r["source"],
                "effective_date": r["effective_date"],
                "last_updated": r["last_updated"].isoformat() if r["last_updated"] else None
            })
        return rules
    finally:
        conn.close()


def add_or_update_tax_rule(rule_data: Dict[str, Any]) -> Dict[str, Any]:
    """Adds a new tax rule or updates an existing one."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        fy = rule_data.get("financial_year", "FY 2025-26")
        name = rule_data.get("rule_name", "").strip()
        rtype = rule_data.get("rule_type", "deduction")
        conditions = json.dumps(rule_data.get("conditions", {}))
        limits = rule_data.get("limits")
        source = rule_data.get("source", "Official IT Notification")
        effective_date = rule_data.get("effective_date", "2025-04-01")

        if not name:
            return {"success": False, "error": "Rule name is required."}

        rule_id = rule_data.get("id")
        if rule_id:
            cursor.execute("""
            UPDATE tax_rules
            SET financial_year = %s, rule_name = %s, rule_type = %s, conditions = %s, limits = %s, source = %s, effective_date = %s, last_updated = CURRENT_TIMESTAMP
            WHERE id = %s
            """, (fy, name, rtype, conditions, limits, source, effective_date, rule_id))
        else:
            cursor.execute("""
            INSERT INTO tax_rules (financial_year, rule_name, rule_type, conditions, limits, source, effective_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (fy, name, rtype, conditions, limits, source, effective_date))

        conn.commit()
        return {"success": True, "message": "Tax rule saved successfully."}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def get_admin_documents() -> List[Dict[str, Any]]:
    """Returns all knowledge-base documents for admin inspection."""
    return KNOWLEDGE_DOCUMENTS
