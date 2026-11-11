"""
TaxWise AI - Explainable AI Layer
Generates structured explanations for every recommendation:
- "Why am I seeing this?"
- User data considered
- Relevant rule
- Eligibility logic
- Reason for recommendation
- Missing information
- Source & important caution
Uses deterministic rule matching and verified knowledge sources.
"""

from typing import Dict, List, Any


def generate_explanation(recommendation: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates a structured, transparent explanation for a specific tax-saving recommendation.
    Complies with Explainability Algorithm in Specification Section 29.
    """
    rec_id = recommendation.get("id", "")
    title = recommendation.get("title", "")
    status = recommendation.get("status", "Potentially Eligible")
    rule = recommendation.get("applicable_rule", "Income Tax Act, 1961")
    source = recommendation.get("source", "Official Income Tax Knowledge Base")

    user_data = recommendation.get("information_used", [])
    eligibility_conditions = recommendation.get("eligibility_conditions", [])
    caution = recommendation.get("caution", "")

    # Specific missing information prompts based on recommendation type
    missing_info = []
    if rec_id == "rec_80d":
        if user_profile.get("parents_senior") is None:
            missing_info.append("Parents' age (whether 60 or above) to determine if ₹50,000 limit applies.")
        if not user_profile.get("preventive_checkup_claimed"):
            missing_info.append("Any preventive health check-up expenses (up to ₹5,000 deductible).")
    elif rec_id == "rec_hra":
        if not user_profile.get("has_rent_receipts"):
            missing_info.append("Valid rent receipts and rental agreement with landlord PAN.")
        if not user_profile.get("metro_city"):
            missing_info.append("City of residence (Metro 50% vs Non-Metro 40% basic salary cap).")
    elif rec_id == "rec_80c":
        if user_profile.get("sec_80c", 0) < 150000:
            missing_info.append("EPF/PF deducted by employer, life insurance premiums, or children's school tuition fees.")
    elif rec_id == "rec_home_loan":
        missing_info.append("Annual interest and principal repayment certificate issued by lending bank.")

    explanation = {
        "title": title,
        "status": status,
        "why_am_i_seeing_this": [
            f"You reported financial profile attributes matching this tax rule ({', '.join(user_data)}).",
            f"The recommendation is evaluated against {rule}.",
            f"Current status determined by the engine: {status}."
        ],
        "user_data_considered": user_data,
        "relevant_rule": rule,
        "eligibility_logic": eligibility_conditions,
        "reason_for_recommendation": recommendation.get("why_suggested", ""),
        "missing_information": missing_info if missing_info else ["No critical information missing for preliminary evaluation."],
        "source": source,
        "caution": caution,
        "financial_year": user_profile.get("financial_year", "FY 2025-26")
    }

    return explanation


def explain_all_recommendations(
    recommendations: List[Dict[str, Any]],
    user_profile: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Enriches each recommendation with its Explainable AI explanation object."""
    enriched = []
    for rec in recommendations:
        rec_copy = dict(rec)
        rec_copy["explanation"] = generate_explanation(rec, user_profile)
        enriched.append(rec_copy)
    return enriched
