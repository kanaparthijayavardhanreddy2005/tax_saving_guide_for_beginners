"""
TaxWise AI - Personalized Tax-Saving Recommendation Engine
Analyzes structured user financial profile against versioned Indian tax rules.
Classifies opportunities into:
- Eligible
- Potentially Eligible
- Requires Additional Information
- Not Applicable
Ranks recommendations by relevance, potential impact, and data completeness.
Never invents eligibility.
"""

from typing import Dict, List, Any, Optional

DEFAULT_SOURCE = "Income Tax Act, 1961 & CBDT Guidelines (Verified Tax Knowledge Base)"


def evaluate_recommendations(
    user_profile: Dict[str, Any],
    financial_year: str = "FY 2025-26"
) -> List[Dict[str, Any]]:
    """
    Evaluates personalized tax opportunities based on user inputs.
    Follows deterministic pseudo-algorithm from Specification Section 28.
    """
    gross_income = max(0.0, float(user_profile.get("gross_income", 0.0)))
    is_salaried = bool(user_profile.get("is_salaried", True))
    age = int(user_profile.get("age", 28))
    current_regime = str(user_profile.get("regime", "new")).lower()

    sec_80c = max(0.0, float(user_profile.get("sec_80c", 0.0)))
    sec_80d = max(0.0, float(user_profile.get("sec_80d", 0.0)))
    parents_senior = user_profile.get("parents_senior", None)  # None means unknown
    nps = max(0.0, float(user_profile.get("sec_80ccd_1b", 0.0)))
    rent_paid = max(0.0, float(user_profile.get("rent_paid", user_profile.get("hra_exemption", 0.0))))
    has_rent_receipts = user_profile.get("has_rent_receipts", None)
    home_loan = max(0.0, float(user_profile.get("home_loan_24b", 0.0)))
    edu_loan = max(0.0, float(user_profile.get("education_loan_80e", 0.0)))
    donations = max(0.0, float(user_profile.get("donations_80g", 0.0)))

    # Estimate marginal tax bracket
    if gross_income > 1500000:
        marginal_tax_rate = 0.30
    elif gross_income > 1000000:
        marginal_tax_rate = 0.20
    elif gross_income > 700000:
        marginal_tax_rate = 0.10
    elif gross_income > 500000:
        marginal_tax_rate = 0.05
    else:
        marginal_tax_rate = 0.0

    recommendations: List[Dict[str, Any]] = []

    # 1. Section 80C Opportunity
    remaining_80c = max(0.0, 150000.0 - sec_80c)
    if current_regime == "new" and gross_income > 1275000:
        status = "Potentially Eligible"
        why = "You are currently exploring the New Regime. If you utilize 80C deductions (PPF, ELSS, EPF), switching to the Old Regime could potentially lower your tax."
    elif remaining_80c > 0 and gross_income > 500000:
        status = "Eligible" if current_regime == "old" else "Potentially Eligible"
        why = f"You reported ₹{sec_80c:,.0f} under Section 80C. You still have ₹{remaining_80c:,.0f} unutilized limit out of the ₹1.5 Lakh ceiling."
    elif sec_80c >= 150000:
        status = "Eligible"
        why = "You have fully maximized the ₹1,50,000 threshold under Section 80C."
    else:
        status = "Not Applicable" if gross_income <= 400000 else "Potentially Eligible"
        why = "Section 80C offers up to ₹1,50,000 in deductions for eligible investments."

    pot_savings_80c = remaining_80c * (marginal_tax_rate * 1.04) if status in ("Eligible", "Potentially Eligible") else 0.0

    recommendations.append({
        "id": "rec_80c",
        "title": "Section 80C Tax-Saving Investments",
        "category": "Investments",
        "status": status,
        "potential_deduction": remaining_80c,
        "potential_savings": round(pot_savings_80c, 2),
        "why_suggested": why,
        "potential_relevance": "High" if remaining_80c > 50000 else "Medium",
        "eligibility_conditions": [
            "Applicable only under the Old Tax Regime",
            "Eligible options: PPF, ELSS, EPF, Term Insurance, 5-Yr FD, Children's Tuition",
            "Overall annual limit is capped at ₹1,50,000"
        ],
        "information_used": [
            f"Gross income: ₹{gross_income:,.0f}",
            f"Current 80C reported: ₹{sec_80c:,.0f}",
            f"Selected regime: {current_regime.upper()}"
        ],
        "applicable_rule": "Income Tax Act, 1961 - Section 80C",
        "source": DEFAULT_SOURCE,
        "caution": "Section 80C deductions are not available under the New Tax Regime (Section 115BAC).",
        "action_cta": "Review 80C Options (ELSS, PPF, EPF)"
    })

    # 2. Section 80D Health Insurance Opportunity
    remaining_80d = max(0.0, 25000.0 - sec_80d)
    if parents_senior is None:
        status_80d = "Requires Additional Information"
        why_80d = "You entered health insurance details, but whether your parents are senior citizens (age 60+) is not specified, which could unlock an extra ₹50,000 deduction."
    elif sec_80d < 25000:
        status_80d = "Potentially Eligible"
        why_80d = f"You reported ₹{sec_80d:,.0f} in health insurance. You can claim up to ₹25,000 for self/family and up to ₹50,000 for senior citizen parents."
    else:
        status_80d = "Eligible"
        why_80d = "You have active health insurance coverage qualifying under Section 80D."

    pot_savings_80d = remaining_80d * (marginal_tax_rate * 1.04)

    recommendations.append({
        "id": "rec_80d",
        "title": "Section 80D Health Insurance Premiums",
        "category": "Insurance",
        "status": status_80d,
        "potential_deduction": remaining_80d,
        "potential_savings": round(pot_savings_80d, 2),
        "why_suggested": why_80d,
        "potential_relevance": "High" if sec_80d == 0 else "Medium",
        "eligibility_conditions": [
            "Deduction up to ₹25,000 for self, spouse, and dependent children",
            "Additional deduction up to ₹25,000 (below 60) or ₹50,000 (senior citizens) for parents",
            "Premiums must be paid via non-cash banking channels"
        ],
        "information_used": [
            f"Reported 80D premium: ₹{sec_80d:,.0f}",
            f"Parents senior citizen status: {'Unspecified' if parents_senior is None else ('Yes' if parents_senior else 'No')}"
        ],
        "applicable_rule": "Income Tax Act, 1961 - Section 80D",
        "source": DEFAULT_SOURCE,
        "caution": "Only available under the Old Tax Regime. Cash payments for insurance premiums are not deductible.",
        "action_cta": "Review Health Insurance Deductions"
    })

    # 3. Section 80CCD(1B) NPS Extra ₹50,000 Opportunity
    remaining_nps = max(0.0, 50000.0 - nps)
    if nps == 0 and gross_income > 600000:
        status_nps = "Potentially Eligible"
        why_nps = "You haven't reported any voluntary NPS Tier-1 contribution. You can claim an exclusive deduction of up to ₹50,000 over and above the Section 80C limit."
    elif nps < 50000:
        status_nps = "Potentially Eligible"
        why_nps = f"You contributed ₹{nps:,.0f} to NPS. You still have ₹{remaining_nps:,.0f} headroom available under Section 80CCD(1B)."
    else:
        status_nps = "Eligible"
        why_nps = "You have maximized the full ₹50,000 exclusive NPS deduction under Section 80CCD(1B)."

    pot_savings_nps = remaining_nps * (marginal_tax_rate * 1.04)

    recommendations.append({
        "id": "rec_nps",
        "title": "Section 80CCD(1B) - National Pension System (NPS)",
        "category": "Retirement",
        "status": status_nps,
        "potential_deduction": remaining_nps,
        "potential_savings": round(pot_savings_nps, 2),
        "why_suggested": why_nps,
        "potential_relevance": "High" if remaining_nps > 20000 else "Medium",
        "eligibility_conditions": [
            "Must be an individual voluntary contribution to an NPS Tier-1 account",
            "Exclusive ₹50,000 limit over and above the ₹1,50,000 80C ceiling",
            "Applicable in the Old Tax Regime"
        ],
        "information_used": [
            f"NPS reported: ₹{nps:,.0f}",
            f"Gross income: ₹{gross_income:,.0f}"
        ],
        "applicable_rule": "Income Tax Act, 1961 - Section 80CCD(1B)",
        "source": DEFAULT_SOURCE,
        "caution": "NPS has a lock-in period until age 60, after which 60% can be withdrawn tax-free and 40% goes into an annuity pension.",
        "action_cta": "Explore NPS Tier-1 Benefits"
    })

    # 4. HRA Exemption (House Rent Allowance)
    if is_salaried and rent_paid > 0:
        if has_rent_receipts is None or has_rent_receipts is False:
            status_hra = "Requires Additional Information"
            why_hra = "You reported paying rent, but rent receipts / landlord PAN confirmation are needed to officially claim HRA exemption under Section 10(13A)."
        else:
            status_hra = "Eligible"
            why_hra = "You meet the conditions for HRA exemption under Section 10(13A) with verified rental expenditure."
    elif is_salaried and rent_paid == 0:
        status_hra = "Potentially Eligible"
        why_hra = "If you live in rented accommodation and your salary package includes HRA, you could claim Section 10(13A) exemption."
    else:
        status_hra = "Not Applicable"
        why_hra = "HRA exemption is only applicable to salaried employees who receive HRA component and pay rent."

    recommendations.append({
        "id": "rec_hra",
        "title": "Section 10(13A) House Rent Allowance (HRA)",
        "category": "Housing",
        "status": status_hra,
        "potential_deduction": rent_paid if status_hra == "Eligible" else 0.0,
        "potential_savings": round(rent_paid * marginal_tax_rate, 2) if status_hra == "Eligible" else 0.0,
        "why_suggested": why_hra,
        "potential_relevance": "High" if rent_paid > 0 else "Low",
        "eligibility_conditions": [
            "Must receive HRA as part of salary structure",
            "Must actually reside in a rented residential property and pay rent",
            "Cannot claim HRA for rent paid to oneself or for an owned property in the same city",
            "Landlord's PAN is mandatory if annual rent exceeds ₹1,00,000"
        ],
        "information_used": [
            f"Employment type: {'Salaried' if is_salaried else 'Non-Salaried'}",
            f"Rent reported: ₹{rent_paid:,.0f}"
        ],
        "applicable_rule": "Income Tax Act, 1961 - Section 10(13A) & Rule 2A",
        "source": DEFAULT_SOURCE,
        "caution": "HRA exemption is only claimable under the Old Tax Regime. Landlord PAN must be valid.",
        "action_cta": "Calculate Exact HRA Exemption"
    })

    # 5. Section 24(b) Home Loan Interest
    if home_loan > 0:
        status_hl = "Eligible"
        why_hl = f"You reported ₹{home_loan:,.0f} in home loan interest. Up to ₹2,00,000 is deductible for a self-occupied property under Section 24(b)."
    else:
        status_hl = "Potentially Eligible"
        why_hl = "If you are servicing a home loan, you can deduct up to ₹2 Lakhs interest under Section 24(b) and principal under Section 80C."

    recommendations.append({
        "id": "rec_home_loan",
        "title": "Section 24(b) Home Loan Interest Deduction",
        "category": "Housing",
        "status": status_hl,
        "potential_deduction": min(200000.0, home_loan),
        "potential_savings": round(min(200000.0, home_loan) * marginal_tax_rate, 2),
        "why_suggested": why_hl,
        "potential_relevance": "High" if home_loan > 0 else "Low",
        "eligibility_conditions": [
            "Loan must be for purchase or construction of residential property",
            "Deduction capped at ₹2,00,000 per financial year for self-occupied home",
            "Construction must be completed within 5 years from end of the financial year in which loan was taken"
        ],
        "information_used": [
            f"Home loan interest reported: ₹{home_loan:,.0f}"
        ],
        "applicable_rule": "Income Tax Act, 1961 - Section 24(b)",
        "source": DEFAULT_SOURCE,
        "caution": "Allowed under the Old Tax Regime. Home loan interest certificate from the lender is required.",
        "action_cta": "Review Home Loan Deduction Limits"
    })

    # 6. Section 80E Higher Education Loan Interest
    if edu_loan > 0:
        status_edu = "Eligible"
        why_edu = f"You reported ₹{edu_loan:,.0f} in education loan interest. Section 80E allows 100% deduction on interest with NO upper monetary ceiling!"
    else:
        status_edu = "Potentially Eligible"
        why_edu = "If you or your parents took a loan for higher education (graduation/post-graduation), the interest paid is 100% tax deductible for up to 8 consecutive years."

    recommendations.append({
        "id": "rec_80e",
        "title": "Section 80E Education Loan Interest",
        "category": "Education",
        "status": status_edu,
        "potential_deduction": edu_loan,
        "potential_savings": round(edu_loan * marginal_tax_rate, 2),
        "why_suggested": why_edu,
        "potential_relevance": "Medium" if edu_loan > 0 else "Low",
        "eligibility_conditions": [
            "Loan must be taken from a recognized financial institution or approved charitable institution",
            "Loan must be for higher education of self, spouse, children, or student for whom user is legal guardian",
            "Deduction is available for maximum 8 consecutive years starting from the year repayment begins",
            "No upper ceiling on the interest amount deductible"
        ],
        "information_used": [
            f"Education loan interest reported: ₹{edu_loan:,.0f}"
        ],
        "applicable_rule": "Income Tax Act, 1961 - Section 80E",
        "source": DEFAULT_SOURCE,
        "caution": "Only the interest component qualifies for deduction, not the principal repayment amount.",
        "action_cta": "Check Section 80E Guidelines"
    })

    # Ranking logic matching Specification Section 28:
    # 1. Relevance (status: Eligible / Potentially Eligible > Needs More Info > Not Applicable)
    # 2. Potential Impact (highest monetary savings / potential deduction)
    # 3. Completeness of information
    status_weights = {
        "Eligible": 4,
        "Potentially Eligible": 3,
        "Requires Additional Information": 2,
        "Not Applicable": 1
    }

    def ranking_key(item: Dict[str, Any]):
        return (
            status_weights.get(item["status"], 0),
            item["potential_savings"],
            item["potential_deduction"]
        )

    recommendations.sort(key=ranking_key, reverse=True)
    return recommendations
