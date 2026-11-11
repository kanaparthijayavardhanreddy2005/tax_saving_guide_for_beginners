# TaxWise AI: Intelligent Tax Saving Guide for Beginners
## Comprehensive Project Documentation & Technical Specification

> **Prototype status:** This document describes the intended architecture and current local prototype. The current RAG corpus is maintained in Python and searched with in-memory TF-IDF; PDF ingestion, embeddings, an external vector database, email-based password recovery, and a production admin identity system are not implemented. Citation metadata and tax content require review against current official publications.

---

### 1. Abstract
TaxWise AI is a responsive Indian income-tax education prototype for beginners, students, young professionals, and first-time taxpayers. It separates deterministic tax computation from generative AI and combines (1) retrieval over a code-maintained tax knowledge base, (2) a beginner-friendly conversational layer, (3) a financial-year-aware tax engine, (4) a personalized recommendation engine, and (5) explainable recommendation details. The current knowledge passages and citation metadata have not been independently certified as a complete or current legal corpus.

---

### 2. Introduction
Income tax planning in India is notoriously complicated for novices. With the co-existence of two distinct regimes (the legacy Old Tax Regime and the revised concessional New Tax Regime under Section 115BAC), individuals struggle to determine whether itemized deductions (Sections 80C, 80D, 80CCD, 24b, and 10(13A) HRA) outweigh the lower slab rates and enhanced standard deduction of the default regime. Generic large language models frequently hallucinate tax brackets, invent arbitrary deductions, and execute faulty arithmetic. TaxWise AI eliminates these risks through an isolated multi-tier architecture where tax calculations are purely deterministic, and AI is employed solely for natural language parsing, educational retrieval, and explainability.

---

### 3. Problem Statement
1. **Mathematical Hallucinations in LLMs**: General-purpose LLMs struggle with multi-tier progressive tax brackets, Section 87A rebate marginal relief caps, and statutory surcharge boundaries.
2. **Jargon Overload for Beginners**: Statutory terms like Chapter VI-A deductions, TRACES certificates, and Form 26AS overwhelm early-career earners.
3. **Lack of Transparency (Black-Box AI)**: Conventional financial apps recommend products without explaining *why* the user qualifies, *which* rules apply, or *what* evidence is required.
4. **Frequent Regulatory Changes**: Annual union budgets alter slabs and limits, making hardcoded tools obsolete.

---

### 4. Existing System
- **Traditional Tax Calculators**: Static forms that provide raw numbers without contextual guidance, education, or personalized tax-saving strategies.
- **Generic AI Chatbots**: Prone to fabricating outdated slab rates, assuming deductions that no longer exist under the New Regime, and providing ungrounded advice.

---

### 5. Proposed System
TaxWise AI introduces a hybrid architecture uniting:
- **Rule-Based Engine**: Python class `TaxCalculator` executing deterministic calculations versioned by Financial Year (`FY 2024-25` and `FY 2025-26`).
- **Local RAG prototype**: In-memory TF-IDF retrieval with financial-year filtering and source metadata; it does not yet include embeddings, persistent vector storage, or document ingestion.
- **Personalized Recommendations**: Classifies opportunities into `Eligible`, `Potentially Eligible`, `Requires Additional Information`, and `Not Applicable`.
- **Explainable AI (XAI)**: Generates transparent answers to "Why am I seeing this?".
- **Tax Education Center & Document Explainer**: Guides for Form 16, Form 26AS, AIS, and ITR forms.

---

### 6. Objectives
- Enable users to ask tax queries in colloquial natural language.
- Compute accurate income tax under both Old and New Regimes with Section 87A rebate and marginal relief.
- Compare scenarios side-by-side with objective, neutral conclusions.
- Surface personalized tax headroom and rank suggestions by potential savings.
- Deliver transparent explainability for every automated suggestion.
- Prevent financial misinformation through strict anti-hallucination barriers.

---

### 7. Scope
- **Geographic Scope**: Republic of India.
- **Regulatory Framework**: Income Tax Act, 1961, Finance Act 2024, and Union Budget 2025.
- **User Demographics**: Salaried individuals, freelancers, professionals (Section 44ADA), and beginners.
- **Supported Tax Years**: FY 2024-25 (AY 2025-26) and FY 2025-26 (AY 2026-27).

---

### 8. Literature Survey
1. **Retrieval-Augmented Generation (Lewis et al., 2020)**: Demonstrated that grounding parametric models in non-parametric indexes drastically reduces factual hallucinations.
2. **Explainable AI in FinTech (Arrieta et al., 2020)**: Established that user trust in automated financial recommendations requires post-hoc explanation of feature importance and decision rules.
3. **Indian Income Tax Reform Studies (CBDT Technical Bulletins 2023-2025)**: Documented the rationale for Section 115BAC concessional slabs and the necessity of automated tools to help citizens evaluate regime choices.

---

### 9. System Architecture
```
                                USER
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │    Web Application    │
                     │  Dashboard & Chat UI  │
                     └───────────┬───────────┘
                                 │
          ┌──────────────────────┴──────────────────────┐
          ▼                                             ▼
Natural Language Question                     Financial Profile & Inputs
          │                                             │
          ▼                                             ▼
      NLP + LLM                                 Rule-Based Engine
          │                                             │
          ▼                                             ▼
     RAG Pipeline                                Tax Calculation
          │                                             │
          ▼                                             ▼
  Tax Knowledge Base                          Recommendation Engine
          │                                             │
          └──────────────────────┬──────────────────────┘
                                 │
                                 ▼
                        Explainable AI Layer
                                 │
                                 ▼
                        Final User Response
```

---

### 10. Methodology
- **Separation of Concerns**: Generative AI generates natural language explanations; Python code performs arithmetic.
- **Data Model**: Relational storage in SQLite for users, tax profiles, versioned tax rules, and chat histories.
- **Anti-Hallucination Pipeline**: If cosine similarity over verified documents falls below minimum threshold, the assistant states: *"I couldn't find sufficient information in my verified tax knowledge base to answer this confidently."*

---

### 11. Functional Requirements
- **FR1**: 8-stage step-by-step wizard collecting personal, income, investment, loan, and deduction data.
- **FR2**: Deterministic tax calculation applying FY-versioned slabs, 87A rebate, and marginal relief.
- **FR3**: Side-by-side scenario comparison table with neutral verdict.
- **FR4**: RAG-based AI chat assistant supporting multi-turn conversation and "Beginner Mode".
- **FR5**: Personalized recommendations classified by eligibility and ranked by monetary savings.
- **FR6**: Explainable AI view showing user data considered, rule, logic, and missing information.
- **FR7**: Tax Education Center and Document Explainer with search and category filtering.
- **FR8**: User authentication and profile persistence.
- **FR9**: Admin telemetry dashboard.

---

### 12. Non-Functional Requirements
- **Accuracy**: Deterministic calculations are covered by unit tests; tax results and source content are not independently certified for filing.
- **Performance**: Measure calculation and retrieval latency in the target deployment; no benchmark is currently recorded.
- **Security**: Passwords use Werkzeug's password hashing; session cookies use HttpOnly and SameSite=Lax. Configure a private session secret, HTTPS secure cookies, and an admin token before deployment.
- **Usability**: WCAG-accessible light FinTech color scheme, responsive layout, and zero unexplained jargon.

---

### 13. Technology Stack
- **Backend**: Python 3.10+ / 3.14, Flask 3.1, Werkzeug
- **Database**: SQLite3 (Embedded Relational Database)
- **AI / NLP**: Google GenAI SDK (`google-genai`), Gemini 2.5 Flash, Hybrid Vector Space Model
- **Frontend**: HTML5, Vanilla CSS3 (Custom FinTech Design System), Vanilla JavaScript (ES6+), Chart.js
- **Testing**: Python `unittest` framework

---

### 14. Database Design
- **Users**: `id`, `name`, `email`, `password_hash`, `created_at`
- **TaxProfiles**: `id`, `user_id`, `financial_year`, `income`, `employment_type`, `age`, `other_income`, `regime`, `created_at`, `updated_at`
- **FinancialInputs**: `id`, `user_id`, `category`, `amount`, `description`, `financial_year`, `created_at`
- **TaxRules**: `id`, `financial_year`, `rule_name`, `rule_type`, `conditions`, `limits`, `source`, `effective_date`, `last_updated`
- **Recommendations**: `id`, `user_id`, `recommendation_type`, `reason`, `status`, `rule_reference`, `created_at`
- **Documents**: `id`, `title`, `source`, `financial_year`, `category`, `content`, `metadata`, `created_at`
- **ChatHistory**: `id`, `user_id`, `question`, `answer`, `sources`, `timestamp`

---

### 15. RAG Architecture
- **Current corpus**: Tax passages and metadata are declared in `rag_engine.py`; there is no automated PDF or web ingestion pipeline.
- **Retrieval**: Pure-Python TF-IDF vectors with inverse document frequency weighting, cosine similarity, and financial-year filtering.
- **Grounding**: Top-$k$ retrieved passages are passed to the assistant with citation metadata. Links currently target the official portal landing page, not necessarily the exact cited publication.
- **Future work**: Add source-document ingestion, chunk provenance, embeddings, persistent vector storage, and retrieval-quality evaluation before treating this as a verified production RAG service.

---

### 16. NLP / LLM Architecture
- **Query Processing**: Normalization, stop-word removal, and keyword bonus matching for Indian tax sections (e.g. 80C, 80D, 87A, HRA).
- **Output Structuring**:
  - `### 📌 Simple Explanation`
  - `### 📜 Relevant Rule`
  - `### 💡 Example`
  - `### 🎯 What It Means For You`
  - `### ⚠️ Important Conditions`
  - `### 🏛️ Source`

---

### 17. Tax Calculation Algorithm
```python
gross_income = sum(salary, business, interest, rental, other)
total_deductions = calculate_eligible_deductions(gross_income, regime, is_salaried, deductions)
taxable_income = max(0, gross_income - total_deductions)
base_tax = apply_slabs(taxable_income, regime, financial_year)
rebate_87a, marginal_relief, tax_after_rebate = apply_rebate_and_relief(taxable_income, base_tax, regime, financial_year)
surcharge = calculate_surcharge(tax_after_rebate, taxable_income, regime)
cess = (tax_after_rebate + surcharge) * 0.04
final_tax = round(tax_after_rebate + surcharge + cess, 2)
```

---

### 18. Recommendation Algorithm
For each versioned rule in the database:
1. Verify financial year applicability.
2. Check user inputs against conditions.
3. If critical inputs are omitted, classify as `Requires Additional Information`.
4. If conditions are met and unused headroom exists, classify as `Eligible` or `Potentially Eligible`.
5. Otherwise, classify as `Not Applicable`.
6. Rank recommendations by `(status_weight, potential_savings, potential_deduction)`.

---

### 19. Explainable AI Methodology
Every recommendation is paired with an explanation object providing:
- **User Data Considered**: Specific numeric inputs that triggered the rule.
- **Relevant Rule**: Statutory section and financial year version.
- **Eligibility Logic**: Detailed criteria tested.
- **Reason for Recommendation**: Plain-English rationale.
- **Missing Information**: Clarifications that would make the evaluation definitive.
- **Source & Caution**: Official government reference and caveats.

---

### 20. Implementation
- `app.py`: Clean REST endpoints for auth, calculations, comparisons, RAG chat, education, and admin.
- `tax_engine.py`: Versioned `TaxCalculator` class with zero LLM arithmetic dependencies.
- `recommendation_engine.py`: Deterministic profiling and priority ranking.
- `explainable_ai.py`: Transparency generator.
- `rag_engine.py`: Vector search and anti-hallucination controller.
- `ai_assistant.py`: Gemini API connector with deterministic fallback.
- `database.py`: SQLite schema, migration, and rule seeding.

---

### 21. Testing
Unit, RAG, security, and integration tests are in `test_taxwise.py`:
- 19 automated tests cover zero-tax threshold validation, marginal relief, deduction caps, resident rebate eligibility, senior-citizen slabs, unsupported-year rejection, recommendation statuses, retrieval abstention, citation metadata, and protected API routes.

---

### 22. Results
- **Zero Tax Salaried Threshold**: Accurately computes ₹0 tax on ₹12,75,000 under FY 2025-26 New Regime (₹75,000 std deduction + ₹60,000 87A rebate).
- **Marginal Relief**: Accurately caps tax before cess at ₹10,000 for ₹12,85,000 gross salary.
- **Retrieval evaluation**: Retrieval precision and answer faithfulness are not formally benchmarked. Responses display the source metadata currently stored with each passage.

---

### 23. Limitations
- Covers resident individual taxpayers and professionals; does not cover complex corporate taxation or partnership firms.
- Presumes standard capital gains treatment and does not substitute for signed audit filings.

---

### 24. Future Scope
- Automated Form 16 PDF parsing using OCR.
- Integration with Sandbox GST / ITR filing sandbox APIs.
- Multi-lingual vernacular support (Hindi, Tamil, Telugu, Marathi).

---

### 25. Conclusion
TaxWise AI proves that modern AI applications in sensitive financial-legal domains succeed best through a hybrid architecture. By strictly separating deterministic rule calculation from generative language explanation, the platform delivers trustworthy, explainable, and accessible tax guidance to empower every Indian citizen.

---

### 26. References
1. Income Tax Act, 1961 (Act No. 43 of 1961), Government of India.
2. Finance Act 2024 and Union Budget 2025 Documents, Ministry of Finance, New Delhi.
3. Central Board of Direct Taxes (CBDT) Circulars on Section 115BAC & Section 87A.
4. Lewis, P., et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. NeurIPS 2020.
5. Income Tax Department of India Official e-Filing Portal: `https://www.incometax.gov.in`.
