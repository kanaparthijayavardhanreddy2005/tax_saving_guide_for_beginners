"""
TaxWise AI - Rule-Based Tax Calculation Engine
Deterministic, versioned Indian Income Tax computation engine.
Mandatory Architecture:
- Class TaxCalculator
- calculateGrossIncome()
- calculateEligibleDeductions()
- calculateTaxableIncome()
- calculateTaxBeforeRebate()
- calculateRebate()
- calculateCess()
- calculateFinalTax()
- compareRegimes()
Versioned by Financial Year (FY 2024-25 and FY 2025-26 / FY 2026-27).
Never relies on LLMs for mathematical calculations.
"""

from typing import Dict, List, Any, Optional

DEFAULT_FINANCIAL_YEAR = "FY 2025-26"
SUPPORTED_FINANCIAL_YEARS = {"FY 2024-25", "FY 2025-26"}
OFFICIAL_SOURCE = "Income Tax Department of India (e-Filing Portal)"


class TaxCalculator:
    """
    Dedicated deterministic Indian Income Tax calculation engine.
    Supports versioned financial years, itemized deductions, Section 87A rebate,
    marginal relief, surcharge, and 4% Health & Education Cess.
    """

    def __init__(self, financial_year: str = DEFAULT_FINANCIAL_YEAR):
        if financial_year not in SUPPORTED_FINANCIAL_YEARS:
            raise ValueError(f"Unsupported financial year: {financial_year}")
        self.financial_year = financial_year

    def calculateGrossIncome(
        self,
        salary_income: float = 0.0,
        business_income: float = 0.0,
        interest_income: float = 0.0,
        rental_income: float = 0.0,
        other_income: float = 0.0
    ) -> float:
        """Computes aggregate gross income across all reported heads."""
        total = (
            max(0.0, float(salary_income)) +
            max(0.0, float(business_income)) +
            max(0.0, float(interest_income)) +
            max(0.0, float(rental_income)) +
            max(0.0, float(other_income))
        )
        return round(total, 2)

    def calculateEligibleDeductions(
        self,
        gross_income: float,
        is_salaried: bool = True,
        regime: str = "new",
        sec_80c: float = 0.0,
        sec_80d: float = 0.0,
        hra_exemption: float = 0.0,
        sec_80ccd_1b: float = 0.0,
        home_loan_interest_24b: float = 0.0,
        education_loan_interest_80e: float = 0.0,
        donations_80g: float = 0.0,
        savings_interest_80tta: float = 0.0,
        nps_employer_80ccd2: float = 0.0,
        other_deductions: float = 0.0
    ) -> Dict[str, Any]:
        """
        Determines applicable deductions based on tax regime and statutory limits.
        New Regime:
          - Standard Deduction: ₹75,000 for salaried (FY 2024-25 & 2025-26)
          - Employer NPS (Sec 80CCD(2)): Allowed in both regimes
        Old Regime:
          - Standard Deduction: ₹50,000 for salaried
          - Section 80C: Capped at ₹1,50,000
          - Section 80D: Capped at ₹1,00,000 (Self ₹25k/50k + Parents ₹25k/50k)
          - Section 80CCD(1B): Capped at ₹50,000
          - Section 24(b): Capped at ₹2,00,000 (Self-occupied home loan interest)
          - Section 80E: Uncapped interest on higher education loans
          - Section 80G: Eligible charitable donations
          - Section 80TTA: Capped at ₹10,000 for savings account interest
        """
        regime = regime.lower()

        if regime == "new":
            std_deduction = 75000.0 if is_salaried else 0.0
            allowed_employer_nps = max(0.0, float(nps_employer_80ccd2))
            total = min(gross_income, std_deduction + allowed_employer_nps)

            return {
                "regime": "new",
                "standard_deduction": round(std_deduction, 2),
                "employer_nps_80ccd2": round(allowed_employer_nps, 2),
                "itemized_deductions": 0.0,
                "total_deductions": round(total, 2),
                "details": {
                    "standard_deduction": round(std_deduction, 2),
                    "employer_nps_80ccd2": round(allowed_employer_nps, 2)
                }
            }
        else:
            # Old Regime
            std_deduction = 50000.0 if is_salaried else 0.0
            c_ded = min(150000.0, max(0.0, float(sec_80c)))
            d_ded = min(100000.0, max(0.0, float(sec_80d)))
            hra_ded = max(0.0, float(hra_exemption))
            nps_ded = min(50000.0, max(0.0, float(sec_80ccd_1b)))
            home_loan = min(200000.0, max(0.0, float(home_loan_interest_24b)))
            edu_loan = max(0.0, float(education_loan_interest_80e))
            donations = max(0.0, float(donations_80g))
            tta = min(10000.0, max(0.0, float(savings_interest_80tta)))
            other = max(0.0, float(other_deductions))

            itemized_sum = (
                c_ded + d_ded + hra_ded + nps_ded +
                home_loan + edu_loan + donations + tta + other
            )
            total = min(gross_income, std_deduction + itemized_sum)

            return {
                "regime": "old",
                "standard_deduction": round(std_deduction, 2),
                "itemized_deductions": round(itemized_sum, 2),
                "total_deductions": round(total, 2),
                "details": {
                    "sec_80c": round(c_ded, 2),
                    "sec_80d": round(d_ded, 2),
                    "hra_exemption": round(hra_ded, 2),
                    "sec_80ccd_1b": round(nps_ded, 2),
                    "home_loan_24b": round(home_loan, 2),
                    "education_loan_80e": round(edu_loan, 2),
                    "donations_80g": round(donations, 2),
                    "savings_interest_80tta": round(tta, 2),
                    "other_deductions": round(other, 2)
                }
            }

    def calculateTaxableIncome(self, gross_income: float, total_deductions: float) -> float:
        """Computes net taxable income after deducting allowable deductions."""
        return max(0.0, round(gross_income - total_deductions, 2))

    def calculateTaxBeforeRebate(
        self,
        taxable_income: float,
        regime: str = "new",
        age: int = 28
    ) -> Dict[str, Any]:
        """
        Calculates base slab tax before Section 87A rebate and cess.
        Versioned for FY 2025-26 and FY 2024-25.
        """
        regime = regime.lower()
        income = max(0.0, float(taxable_income))
        breakdown: List[Dict[str, Any]] = []
        base_tax = 0.0

        if regime == "new":
            if self.financial_year == "FY 2024-25":
                # FY 2024-25 New Regime Slabs
                slabs = [
                    (0, 300000, 0.00, "Up to ₹3,00,000"),
                    (300000, 700000, 0.05, "₹3,00,001 to ₹7,00,000"),
                    (700000, 1000000, 0.10, "₹7,00,001 to ₹10,00,000"),
                    (1000000, 1200000, 0.15, "₹10,00,001 to ₹12,00,000"),
                    (1200000, 1500000, 0.20, "₹12,00,001 to ₹15,00,000"),
                    (1500000, float("inf"), 0.30, "Above ₹15,00,000")
                ]
            else:
                # Default FY 2025-26 New Regime Slabs (Budget 2025 revised brackets)
                slabs = [
                    (0, 400000, 0.00, "Up to ₹4,00,000"),
                    (400000, 800000, 0.05, "₹4,00,001 to ₹8,00,000"),
                    (800000, 1200000, 0.10, "₹8,00,001 to ₹12,00,000"),
                    (1200000, 1600000, 0.15, "₹12,00,001 to ₹16,00,000"),
                    (1600000, 2000000, 0.20, "₹16,00,001 to ₹20,00,000"),
                    (2000000, 2400000, 0.25, "₹20,00,001 to ₹24,00,000"),
                    (2400000, float("inf"), 0.30, "Above ₹24,00,000")
                ]
        else:
            if age >= 80:
                slabs = [
                    (0, 500000, 0.00, "Up to ₹5,00,000"),
                    (500000, 1000000, 0.20, "₹5,00,001 to ₹10,00,000"),
                    (1000000, float("inf"), 0.30, "Above ₹10,00,000")
                ]
            elif age >= 60:
                slabs = [
                    (0, 300000, 0.00, "Up to ₹3,00,000"),
                    (300000, 500000, 0.05, "₹3,00,001 to ₹5,00,000"),
                    (500000, 1000000, 0.20, "₹5,00,001 to ₹10,00,000"),
                    (1000000, float("inf"), 0.30, "Above ₹10,00,000")
                ]
            else:
                slabs = [
                    (0, 250000, 0.00, "Up to ₹2,50,000"),
                    (250000, 500000, 0.05, "₹2,50,001 to ₹5,00,000"),
                    (500000, 1000000, 0.20, "₹5,00,001 to ₹10,00,000"),
                    (1000000, float("inf"), 0.30, "Above ₹10,00,000")
                ]

        for lower, upper, rate, label in slabs:
            if income > lower:
                taxable_in_slab = min(income, upper) - lower
                slab_tax = taxable_in_slab * rate
                base_tax += slab_tax
                breakdown.append({
                    "slab": label,
                    "rate": f"{int(rate * 100)}%",
                    "taxable_amount": round(taxable_in_slab, 2),
                    "tax": round(slab_tax, 2)
                })
            else:
                breakdown.append({
                    "slab": label,
                    "rate": f"{int(rate * 100)}%",
                    "taxable_amount": 0.0,
                    "tax": 0.0
                })

        return {
            "base_tax": round(base_tax, 2),
            "slab_breakdown": breakdown
        }

    def calculateRebate(
        self,
        taxable_income: float,
        base_tax: float,
        regime: str = "new",
        is_resident: bool = True
    ) -> Dict[str, float]:
        """
        Computes Section 87A rebate and marginal relief.
        FY 2025-26 New Regime:
          - Full rebate if taxable income <= ₹12,00,000.
          - Marginal relief: If taxable income > ₹12L, tax cannot exceed income over ₹12L.
        FY 2024-25 New Regime:
          - Full rebate if taxable income <= ₹7,00,000 (rebate ₹25,000).
        Old Regime:
          - Full rebate if taxable income <= ₹5,00,000 (max ₹12,500).
        """
        regime = regime.lower()
        rebate_87a = 0.0
        marginal_relief = 0.0
        tax_after_rebate = base_tax

        if not is_resident:
            pass
        elif regime == "new":
            threshold = 700000.0 if self.financial_year == "FY 2024-25" else 1200000.0

            if taxable_income <= threshold:
                rebate_87a = base_tax
                tax_after_rebate = 0.0
            else:
                excess_income = taxable_income - threshold
                if base_tax > excess_income:
                    marginal_relief = base_tax - excess_income
                    tax_after_rebate = excess_income
        else:
            # Old Regime: Threshold ₹5,00,000
            if taxable_income <= 500000.0:
                rebate_87a = min(12500.0, base_tax)
                tax_after_rebate = max(0.0, base_tax - rebate_87a)

        return {
            "rebate_87a": round(rebate_87a, 2),
            "marginal_relief": round(marginal_relief, 2),
            "tax_after_rebate": round(tax_after_rebate, 2)
        }

    def calculateSurcharge(self, tax: float, taxable_income: float, regime: str = "new") -> float:
        """Calculates surcharge for high-income brackets."""
        is_new = (regime.lower() == "new")
        if taxable_income <= 5000000:
            return 0.0
        elif taxable_income <= 10000000:
            return round(tax * 0.10, 2)
        elif taxable_income <= 20000000:
            return round(tax * 0.15, 2)
        elif taxable_income <= 50000000:
            return round(tax * 0.25, 2)
        else:
            # > ₹5 Crore: capped at 25% under New Regime, 37% under Old Regime
            return round(tax * (0.25 if is_new else 0.37), 2)

    def calculateCess(self, tax_plus_surcharge: float) -> float:
        """Computes 4% Health and Education Cess."""
        return round(tax_plus_surcharge * 0.04, 2)

    def calculateFinalTax(
        self,
        gross_income: float,
        is_salaried: bool = True,
        regime: str = "new",
        age: int = 28,
        is_resident: bool = True,
        **deduction_kwargs
    ) -> Dict[str, Any]:
        """
        Executes complete end-to-end deterministic tax calculation following
        the mandatory architecture pipeline:
        Gross Income -> Eligible Deductions -> Taxable Income ->
        Base Tax -> Rebate/Relief -> Surcharge -> Cess -> Final Tax.
        """
        gross = max(0.0, float(gross_income))
        deductions_res = self.calculateEligibleDeductions(
            gross_income=gross,
            is_salaried=is_salaried,
            regime=regime,
            **deduction_kwargs
        )
        total_deductions = deductions_res["total_deductions"]
        taxable_income = self.calculateTaxableIncome(gross, total_deductions)

        slab_res = self.calculateTaxBeforeRebate(taxable_income, regime=regime, age=age)
        base_tax = slab_res["base_tax"]

        rebate_res = self.calculateRebate(
            taxable_income, base_tax, regime=regime, is_resident=is_resident
        )
        tax_after_rebate = rebate_res["tax_after_rebate"]

        surcharge = self.calculateSurcharge(tax_after_rebate, taxable_income, regime=regime)
        cess = self.calculateCess(tax_after_rebate + surcharge)
        total_tax = round(tax_after_rebate + surcharge + cess, 2)
        take_home = round(max(0.0, gross - total_tax), 2)
        effective_rate = round((total_tax / gross * 100.0), 2) if gross > 0 else 0.0

        return {
            "financial_year": self.financial_year,
            "regime": regime,
            "regime_name": "New Tax Regime (Section 115BAC)" if regime == "new" else "Old Tax Regime",
            "gross_income": gross,
            "is_salaried": is_salaried,
            "standard_deduction": deductions_res["standard_deduction"],
            "total_deductions": total_deductions,
            "deductions_breakdown": deductions_res.get("details", {}),
            "taxable_income": taxable_income,
            "base_tax": base_tax,
            "rebate_87a": rebate_res["rebate_87a"],
            "marginal_relief": rebate_res["marginal_relief"],
            "tax_after_rebate": tax_after_rebate,
            "surcharge": surcharge,
            "cess": cess,
            "total_tax": total_tax,
            "take_home": take_home,
            "effective_rate": effective_rate,
            "slab_breakdown": slab_res["slab_breakdown"],
            "source": OFFICIAL_SOURCE
        }

    def compareRegimes(
        self,
        gross_income: float,
        is_salaried: bool = True,
        **deduction_kwargs
    ) -> Dict[str, Any]:
        """
        Evaluates user profile under both Old and New Tax Regimes.
        Provides scenario differences and neutral beginner explanation:
        'Based on the information provided, this scenario currently produces a
        lower estimated tax. Verify your eligibility and current rules before making a final decision.'
        """
        new_res = self.calculateFinalTax(gross_income, is_salaried=is_salaried, regime="new", **deduction_kwargs)
        old_res = self.calculateFinalTax(gross_income, is_salaried=is_salaried, regime="old", **deduction_kwargs)

        tax_diff = abs(old_res["total_tax"] - new_res["total_tax"])
        lower_regime = "new" if new_res["total_tax"] <= old_res["total_tax"] else "old"
        higher_regime = "old" if lower_regime == "new" else "new"

        if new_res["total_tax"] == old_res["total_tax"]:
            neutral_summary = "Both regimes yield an identical estimated tax liability for your current inputs."
            recommendation_text = "Based on the information provided, either regime produces the same estimated tax. Verify your eligibility and current rules before making a final decision."
        elif lower_regime == "new":
            neutral_summary = f"The New Tax Regime produces a lower estimated tax by ₹{tax_diff:,.2f}."
            recommendation_text = "Based on the information provided, this scenario currently produces a lower estimated tax. Verify your eligibility and current rules before making a final decision."
        else:
            neutral_summary = f"The Old Tax Regime produces a lower estimated tax by ₹{tax_diff:,.2f} due to your declared deductions."
            recommendation_text = "Based on the information provided, this scenario currently produces a lower estimated tax. Verify your eligibility and current rules before making a final decision."

        return {
            "financial_year": self.financial_year,
            "new_regime": new_res,
            "old_regime": old_res,
            "lower_tax_regime": lower_regime,
            "tax_difference": round(tax_diff, 2),
            "summary": neutral_summary,
            "neutral_disclaimer": recommendation_text,
            "source": OFFICIAL_SOURCE
        }


# Convenience factory & global instance
default_calculator = TaxCalculator(DEFAULT_FINANCIAL_YEAR)


def calculate_tax(gross_income: float, is_salaried: bool = True, regime: str = "new", **kwargs) -> Dict[str, Any]:
    return default_calculator.calculateFinalTax(gross_income, is_salaried, regime, **kwargs)


def compare_regimes(gross_income: float, is_salaried: bool = True, **kwargs) -> Dict[str, Any]:
    return default_calculator.compareRegimes(gross_income, is_salaried, **kwargs)
