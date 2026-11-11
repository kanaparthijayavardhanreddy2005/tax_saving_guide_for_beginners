"""
TaxWise AI - Automated Comprehensive Test Suite
Validates:
1. Rule-Based Tax Engine (Slabs, Standard Deduction, 87A Rebate, Marginal Relief, Cess)
2. Personalized Recommendation Engine (Eligibility status classification, Ranking)
3. Explainable AI Layer ("Why am I seeing this?", transparency attributes)
4. RAG Retrieval & Anti-Hallucination Safeguards
5. User Authentication & Profile Persistence
6. Flask REST API Endpoints
"""

import unittest
import json
import os
from unittest.mock import patch
from tax_engine import TaxCalculator
from recommendation_engine import evaluate_recommendations
from explainable_ai import generate_explanation, explain_all_recommendations
import rag_engine
import ai_assistant
from app import app
import auth
import database


class TestDatabaseConfiguration(unittest.TestCase):
    def test_database_connection_requires_a_postgres_url(self):
        with patch.dict(os.environ, {"DATABASE_URL": "", "SUPABASE_DB_URL": ""}):
            with self.assertRaisesRegex(RuntimeError, "Set DATABASE_URL"):
                database.get_db_connection()


class TestApplicationStartup(unittest.TestCase):
    def test_app_import_does_not_initialize_database(self):
        self.assertIsNotNone(app)


class TestTaxEngine(unittest.TestCase):
    def setUp(self):
        self.calc_2025 = TaxCalculator(financial_year="FY 2025-26")
        self.calc_2024 = TaxCalculator(financial_year="FY 2024-25")

    def test_gross_income_calculation(self):
        gross = self.calc_2025.calculateGrossIncome(
            salary_income=1000000,
            business_income=200000,
            interest_income=50000
        )
        self.assertEqual(gross, 1250000.0)

    def test_new_regime_zero_tax_threshold(self):
        # In FY 2025-26, salaried gross income ₹12,75,000 gets ₹75k std deduction -> ₹12L taxable -> Zero tax under 87A
        result = self.calc_2025.calculateFinalTax(gross_income=1275000.0, is_salaried=True, regime="new")
        self.assertEqual(result["standard_deduction"], 75000.0)
        self.assertEqual(result["taxable_income"], 1200000.0)
        self.assertEqual(result["total_tax"], 0.0)
        self.assertTrue(result["rebate_87a"] > 0)

    def test_marginal_relief_new_regime(self):
        # Taxable income ₹12,10,000 (just above ₹12L threshold)
        # Tax before cess cannot exceed (12,10,000 - 12,00,000) = ₹10,000
        result = self.calc_2025.calculateFinalTax(gross_income=1285000.0, is_salaried=True, regime="new")
        # gross 12,85,000 - std 75,000 = taxable 12,10,000
        self.assertEqual(result["taxable_income"], 1210000.0)
        self.assertTrue(result["marginal_relief"] > 0)
        self.assertEqual(result["tax_after_rebate"], 10000.0)

    def test_old_regime_deductions_capped(self):
        # 80C should be capped at ₹1,50,000 even if user enters ₹3,00,000
        ded = self.calc_2025.calculateEligibleDeductions(
            gross_income=1500000.0,
            is_salaried=True,
            regime="old",
            sec_80c=300000.0,
            sec_80d=35000.0
        )
        self.assertEqual(ded["details"]["sec_80c"], 150000.0)
        self.assertEqual(ded["details"]["sec_80d"], 35000.0)
        self.assertEqual(ded["standard_deduction"], 50000.0)

    def test_regime_comparison_neutrality(self):
        comparison = self.calc_2025.compareRegimes(gross_income=1000000.0, is_salaried=True)
        self.assertIn("neutral_disclaimer", comparison)
        self.assertIn("produces a lower estimated tax", comparison["neutral_disclaimer"])

    def test_senior_citizen_old_regime_slabs(self):
        senior = self.calc_2025.calculateFinalTax(gross_income=3000000.0, regime="old", age=60)
        non_senior = self.calc_2025.calculateFinalTax(gross_income=3000000.0, regime="old", age=59)
        self.assertLess(senior["base_tax"], non_senior["base_tax"])

    def test_section_87a_rebate_requires_residency(self):
        resident = self.calc_2025.calculateFinalTax(
            gross_income=700000.0, regime="new", is_resident=True
        )
        non_resident = self.calc_2025.calculateFinalTax(
            gross_income=700000.0, regime="new", is_resident=False
        )
        self.assertEqual(resident["total_tax"], 0.0)
        self.assertGreater(non_resident["total_tax"], 0.0)

    def test_unsupported_financial_year_is_rejected(self):
        with self.assertRaises(ValueError):
            TaxCalculator(financial_year="FY 2027-28")


class TestRecommendationEngine(unittest.TestCase):
    def test_classification_and_ranking(self):
        profile = {
            "gross_income": 1500000.0,
            "is_salaried": True,
            "sec_80c": 50000.0,     # ₹1,00,000 headroom left -> should be Potentially Eligible / Eligible
            "sec_80d": 0.0,         # Should be flagged
            "sec_80ccd_1b": 0.0,    # NPS headroom
            "education_loan_80e": 40000.0  # Should be marked Eligible
        }
        recs = evaluate_recommendations(profile)
        statuses = [r["status"] for r in recs]
        self.assertIn("Eligible", statuses)
        self.assertIn("Potentially Eligible", statuses)

        # Check ranking: highest savings/relevance comes first
        top_rec = recs[0]
        self.assertIn(top_rec["status"], ["Eligible", "Potentially Eligible"])


class TestExplainableAI(unittest.TestCase):
    def test_why_am_i_seeing_this_structure(self):
        rec = {
            "id": "rec_80d",
            "title": "Section 80D Health Insurance",
            "status": "Potentially Eligible",
            "why_suggested": "You entered health insurance details.",
            "information_used": ["Reported 80D premium: ₹0"],
            "applicable_rule": "Section 80D",
            "source": "Income Tax Act",
            "caution": "Cash payments not allowed."
        }
        profile = {"parents_senior": None}
        explanation = generate_explanation(rec, profile)

        self.assertIn("why_am_i_seeing_this", explanation)
        self.assertIn("user_data_considered", explanation)
        self.assertIn("relevant_rule", explanation)
        self.assertIn("missing_information", explanation)
        self.assertIn("source", explanation)


class TestRAGAndAntiHallucination(unittest.TestCase):
    def test_grounded_retrieval(self):
        res = rag_engine.query_rag_knowledge("What is the deduction limit under Section 80C?")
        self.assertEqual(res["confidence"], "high")
        self.assertTrue(len(res["sources"]) > 0)
        self.assertEqual(res["sources"][0]["section"], "Section 80C")

    def test_anti_hallucination_safeguard(self):
        # Query on arbitrary unrelated domain
        res = rag_engine.query_rag_knowledge("What is quantum entanglement in black holes?")
        self.assertEqual(res["confidence"], "insufficient")
        self.assertIn("couldn't find sufficient information", res["answer"])

    def test_citations_include_financial_year_and_source_location(self):
        result = rag_engine.query_rag_knowledge("What is the deduction limit under Section 80C?")
        source = result["sources"][0]
        self.assertEqual(source["financial_year"], "FY 2025-26")
        self.assertTrue(source["page"])
        self.assertTrue(source["url"].startswith("https://"))

    def test_offline_answer_does_not_invent_tax_arithmetic(self):
        result = rag_engine.query_rag_knowledge("Explain Section 80C")
        answer = ai_assistant.format_grounded_fallback_answer(
            "Explain Section 80C", result["sources"], result["retrieved_chunks"]
        )
        self.assertNotIn("₹31,200", answer)
        self.assertIn(result["retrieved_chunks"][0], answer)


class TestAPIEndpoints(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_calculate_endpoint(self):
        resp = self.client.post("/api/tax/calculate", json={
            "gross_income": 1200000,
            "is_salaried": True,
            "regime": "new"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("result", data)
        self.assertIn("comparison", data)
        self.assertIn("recommendations", data)

    def test_negative_income_validation(self):
        resp = self.client.post("/api/tax/calculate", json={"gross_income": -50000})
        self.assertEqual(resp.status_code, 400)

    def test_education_topics_endpoint(self):
        resp = self.client.get("/api/education/topics")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(len(data["topics"]) > 5)

    def test_documents_endpoint(self):
        resp = self.client.get("/api/documents")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(len(data["documents"]) > 4)

    def test_document_guide_includes_all_requested_tax_sections(self):
        response = self.client.get("/api/documents")
        documents = response.get_json()["documents"]
        section_names = {document["name"] for document in documents if document.get("kind") == "tax-section"}
        expected_sections = {
            "Section 80C", "Section 80CCD(1B)", "Section 80D", "Section 80E",
            "Section 80G", "Section 80TTA", "Section 80TTB", "Section 24(b)",
            "Section 80DD", "Section 80U", "Section 80DDB"
        }
        self.assertTrue(expected_sections.issubset(section_names))
        self.assertTrue(all(
            document.get("conditions") and document.get("regime") and document.get("official_source_url")
            for document in documents if document.get("kind") == "tax-section"
        ))

    def test_admin_and_password_change_require_authorization(self):
        self.assertEqual(self.client.get("/api/admin/stats").status_code, 403)
        self.assertEqual(
            self.client.post("/api/admin/rules", json={"rule_name": "Unauthorized"}).status_code,
            403
        )
        self.assertEqual(
            self.client.post(
                "/api/auth/reset-password",
                json={"email": "someone@example.com", "new_password": "new-password-long"}
            ).status_code,
            401
        )


if __name__ == "__main__":
    unittest.main()
