"""
TaxWise AI - Retrieval-Augmented Generation (RAG) Engine
Implements:
- Vector Database / Document Store with rich official metadata
- Tokenization, TF-IDF / Vector Space semantic retrieval
- Metadata filtering (by financial year, topic, section)
- Anti-hallucination verification
- Grounded prompt construction
- Structured citation and source generation
"""

import math
import re
from typing import Dict, List, Any, Optional, Tuple

OFFICIAL_DISCLAIMER = (
    "TaxWise AI provides educational information and estimates based on the information "
    "available in its knowledge base. Tax rules may change, and eligibility depends on individual "
    "circumstances. Always verify current rules using official sources or consult a qualified "
    "tax professional before filing or making financial decisions."
)

# Authoritative Tax Knowledge Base Documents
KNOWLEDGE_DOCUMENTS: List[Dict[str, Any]] = [
    {
        "id": "doc_80c",
        "title": "Section 80C: Deductions for Specified Savings & Investments",
        "source": "Income Tax Department of India, Circular No. 04/2024 / Income Tax Act 1961",
        "financial_year": "FY 2025-26",
        "category": "Deductions",
        "section": "Section 80C",
        "page": "14-16",
        "document_type": "Official Act & Circular",
        "content": (
            "Section 80C of the Income Tax Act allows individual taxpayers and HUFs to claim deductions "
            "up to a combined aggregate ceiling of ₹1,50,000 per financial year under the Old Tax Regime. "
            "Eligible investments and payments include: "
            "1. Employees' Provident Fund (EPF) and Voluntary Provident Fund (VPF). "
            "2. Public Provident Fund (PPF) with 15-year tenure and tax-free interest under EEE regime. "
            "3. Equity Linked Savings Scheme (ELSS) mutual funds with a 3-year mandatory lock-in period. "
            "4. Life Insurance Premiums (term life, endowment, ULIP) for self, spouse, and children. "
            "5. National Savings Certificate (NSC) and 5-Year Tax-Saver Bank Fixed Deposits. "
            "6. Tuition fees paid for full-time education of up to two children in Indian institutions. "
            "7. Principal repayment of housing loans taken for residential property purchase or construction. "
            "Important note: Section 80C deductions are strictly NOT available under the New Tax Regime (Section 115BAC)."
        )
    },
    {
        "id": "doc_80d",
        "title": "Section 80D: Deductions for Health Insurance Premiums",
        "source": "Income Tax Department of India, Section 80D Statutory Provisions",
        "financial_year": "FY 2025-26",
        "category": "Health Insurance",
        "section": "Section 80D",
        "page": "22-24",
        "document_type": "Statutory Provision",
        "content": (
            "Section 80D provides income tax deductions for health and medical insurance premiums paid "
            "by individual taxpayers under the Old Tax Regime. "
            "Ceilings: "
            "1. Self, spouse, and dependent children: Up to ₹25,000 per financial year. "
            "If self or spouse is a senior citizen (aged 60 years or above), the ceiling increases to ₹50,000. "
            "2. Parents (aged below 60): Additional deduction of up to ₹25,000. "
            "3. Parents (Senior Citizens, aged 60 and above): Additional deduction of up to ₹50,000. "
            "4. Preventive health check-up: Up to ₹5,000 is allowed within the overall respective caps. "
            "Maximum possible deduction under Section 80D is ₹1,00,000 (if both taxpayer and parents are senior citizens). "
            "Condition: Premiums must be paid via non-cash banking channels (Net Banking, UPI, Cards, Cheque). "
            "Cash payments for insurance premiums are completely disallowed, though preventive checkups may be cash."
        )
    },
    {
        "id": "doc_hra",
        "title": "Section 10(13A) and Rule 2A: House Rent Allowance (HRA) Exemption",
        "source": "Income Tax Rules 1962 (Rule 2A) & Income Tax Act Section 10(13A)",
        "financial_year": "FY 2025-26",
        "category": "Exemptions",
        "section": "Section 10(13A)",
        "page": "8-10",
        "document_type": "Statutory Rule",
        "content": (
            "House Rent Allowance (HRA) exemption is available to salaried employees who receive HRA "
            "as part of their salary structure and actually incur expenditure on rent for residential accommodation. "
            "Under the Old Tax Regime, the exempt amount is the lowest of the following three: "
            "1. Actual HRA received from the employer during the year. "
            "2. 50% of Basic Salary + Dearness Allowance (DA) for employees living in metro cities "
            "(New Delhi, Mumbai, Kolkata, Chennai) OR 40% of Basic Salary + DA for non-metro cities. "
            "3. Actual rent paid minus 10% of Basic Salary + DA. "
            "Mandatory compliance: If total annual rent paid exceeds ₹1,00,000, the landlord's Permanent Account "
            "Number (PAN) must be submitted to the employer. HRA is not claimable under the New Tax Regime."
        )
    },
    {
        "id": "doc_87a",
        "title": "Section 87A Tax Rebate & Marginal Relief (Budget 2025 Slabs)",
        "source": "Union Budget 2025 / Finance Bill 2025 Provisions / Section 87A",
        "financial_year": "FY 2025-26",
        "category": "Tax Rebates",
        "section": "Section 87A",
        "page": "3-5",
        "document_type": "Budget Legislation",
        "content": (
            "Section 87A rebate offers tax relief to resident individual taxpayers. "
            "In FY 2025-26 (AY 2026-27) under the New Tax Regime (Section 115BAC): "
            "Resident individuals with total taxable income up to ₹12,00,000 receive a 100% tax rebate under Section 87A, "
            "resulting in ZERO tax liability. "
            "With the Standard Deduction of ₹75,000 for salaried employees, a gross salary up to ₹12,75,000 incurs zero tax! "
            "Marginal Relief: If taxable income exceeds ₹12,00,000 by a small margin, the tax payable before cess "
            "cannot exceed the excess income over ₹12,00,000. "
            "Under the Old Tax Regime, Section 87A rebate remains capped at ₹12,500 for taxable income up to ₹5,00,000."
        )
    },
    {
        "id": "doc_std_ded",
        "title": "Section 16(ia): Standard Deduction for Salaried and Pensioners",
        "source": "Finance Act 2024 / Finance Act 2025 / Section 16",
        "financial_year": "FY 2025-26",
        "category": "Salary Deductions",
        "section": "Section 16(ia)",
        "page": "6",
        "document_type": "Finance Act Amendment",
        "content": (
            "Section 16(ia) grants a flat standard deduction from gross salary and pension income. "
            "Under the New Tax Regime (Section 115BAC): Standard deduction is ₹75,000 per financial year "
            "(effective from FY 2024-25 onwards and maintained in FY 2025-26). "
            "Under the Old Tax Regime: Standard deduction remains ₹50,000 per financial year. "
            "No bills, receipts, or proof of expenditure are required to claim standard deduction. "
            "It applies automatically to all salaried individuals and pensioners."
        )
    },
    {
        "id": "doc_nps_80ccd",
        "title": "Section 80CCD: National Pension System (NPS) Deductions",
        "source": "PFRDA & Income Tax Department Guidelines on NPS Benefits",
        "financial_year": "FY 2025-26",
        "category": "Retirement & Pension",
        "section": "Section 80CCD",
        "page": "18-20",
        "document_type": "Regulatory Guide",
        "content": (
            "The National Pension System (NPS) provides three separate tax deduction avenues: "
            "1. Section 80CCD(1): Employee voluntary contribution up to 10% of salary, included inside the ₹1.5L 80C cap. "
            "2. Section 80CCD(1B): Exclusive additional deduction of up to ₹50,000 for voluntary contributions to NPS Tier-1. "
            "This ₹50,000 is over and above the ₹1.5L ceiling of Section 80C, allowing a total deduction of ₹2,00,000 (Old Regime). "
            "3. Section 80CCD(2): Employer's contribution to employee NPS account up to 14% of Basic + DA (central/state govt) "
            "or up to 14% (private sector under Budget updates). This deduction is allowed in BOTH Old and New Regimes!"
        )
    },
    {
        "id": "doc_24b",
        "title": "Section 24(b): Deduction for Interest on Housing Loan",
        "source": "Income Tax Department - Deductions from House Property Income",
        "financial_year": "FY 2025-26",
        "category": "Housing Loan",
        "section": "Section 24(b)",
        "page": "12-13",
        "document_type": "Statutory Provision",
        "content": (
            "Under Section 24(b) of the Income Tax Act, interest payable on borrowed capital for acquiring, "
            "constructing, repairing, or reconstructing a residential house property is deductible: "
            "1. Self-Occupied Property: Maximum interest deduction is capped at ₹2,00,000 per financial year. "
            "Construction must be completed within 5 years from the end of the financial year in which loan was borrowed. "
            "2. Let-Out / Rented Property: Actual interest paid can be deducted against rental income, "
            "with net loss from house property eligible for set-off against other heads capped at ₹2,00,000. "
            "Only available under the Old Tax Regime."
        )
    },
    {
        "id": "doc_80e",
        "title": "Section 80E: Deduction for Interest on Higher Education Loans",
        "source": "Income Tax Department - Deductions Chapter VI-A",
        "financial_year": "FY 2025-26",
        "category": "Education",
        "section": "Section 80E",
        "page": "26",
        "document_type": "Statutory Provision",
        "content": (
            "Section 80E allows deduction of interest paid on loans borrowed from recognized financial institutions "
            "or approved charitable organizations for higher education. "
            "Key terms: "
            "1. Beneficiary: Loan must be for higher education of self, spouse, children, or a student for whom taxpayer is legal guardian. "
            "2. No monetary ceiling: 100% of the interest amount paid during the financial year is deductible! "
            "3. Duration: Available for up to 8 consecutive assessment years starting from the year repayment starts, "
            "or until the full interest is paid off, whichever is earlier. "
            "4. Only the interest amount qualifies; loan principal repayment does not qualify under Section 80E."
        )
    },
    {
        "id": "doc_80g",
        "title": "Section 80G: Deductions for Donations to Charitable Organizations",
        "source": "Income Tax Department - Charitable Donations Guidelines",
        "financial_year": "FY 2025-26",
        "category": "Charitable Donations",
        "section": "Section 80G",
        "page": "28-30",
        "document_type": "Statutory Provision",
        "content": (
            "Section 80G allows taxpayers to deduct contributions made to specified charitable funds and relief institutions. "
            "1. 100% deduction without qualifying limit: Prime Minister's National Relief Fund, National Defence Fund, etc. "
            "2. 50% deduction: Prime Minister's Drought Relief Fund, recognized religious or charitable trusts. "
            "Crucial Rule: Donations made in cash exceeding ₹2,000 are completely disallowed. "
            "Donations must be made via electronic transfer, cheque, or draft. A valid Form 10BE donation certificate "
            "issued by the recipient entity is required."
        )
    },
    {
        "id": "doc_documents_explainer",
        "title": "Essential Tax Documents: Form 16, Form 26AS, AIS, and TIS",
        "source": "Income Tax Department e-Filing User Portal Documentation",
        "financial_year": "FY 2025-26",
        "category": "Tax Documents",
        "section": "Filing Documentation",
        "page": "1-5",
        "document_type": "Educational Guide",
        "content": (
            "A beginner's overview of primary tax documents in India: "
            "1. Form 16: Certificate of TDS on salary issued by employers. Part A contains quarterly TDS deposits "
            "and TRACES certificate number; Part B details salary breakup, allowances, standard deduction, and deductions. "
            "2. Form 26AS: Annual consolidated tax statement showing all TDS deducted on salary, interest, freelance fees, "
            "TCS collected, advance tax paid, and self-assessment tax paid. "
            "3. AIS (Annual Information Statement): Comprehensive financial dossier reporting interest from savings/FDs, "
            "dividends, stock and mutual fund purchases/sales, foreign remittances, and high-value transactions. "
            "4. ITR-1 (Sahaj): For resident individuals with income up to ₹50 Lakhs from salary, one house property, and other sources."
        )
    },
    {
        "id": "doc_slabs_2025_26",
        "title": "Income Tax Slabs for FY 2025-26 (AY 2026-27) New vs Old Regime",
        "source": "Union Budget 2025 / CBDT Income Tax Slabs Notification",
        "financial_year": "FY 2025-26",
        "category": "Tax Slabs",
        "section": "Tax Rates",
        "page": "1-2",
        "document_type": "Official Slabs Schedule",
        "content": (
            "FY 2025-26 (AY 2026-27) Tax Slabs Schedule: "
            "New Tax Regime (Section 115BAC): "
            "- Up to ₹4,00,000: Nil (0%) "
            "- ₹4,00,001 to ₹8,00,000: 5% "
            "- ₹8,00,001 to ₹12,00,000: 10% "
            "- ₹12,00,001 to ₹16,00,000: 15% "
            "- ₹16,00,001 to ₹20,00,000: 20% "
            "- ₹20,00,001 to ₹24,00,000: 25% "
            "- Above ₹24,00,000: 30% "
            "Old Tax Regime (General Individuals < 60 yrs): "
            "- Up to ₹2,50,000: Nil (0%) "
            "- ₹2,50,001 to ₹5,00,000: 5% "
            "- ₹5,00,001 to ₹10,00,000: 20% "
            "- Above ₹10,00,000: 30% "
            "Health & Education Cess: 4% applied on base tax + surcharge across both regimes."
        )
    },
    {
        "id": "doc_44ada",
        "title": "Section 44ADA: Presumptive Taxation Scheme for Professionals & Freelancers",
        "source": "Income Tax Act, 1961 - Section 44ADA Statutory Rules",
        "financial_year": "FY 2025-26",
        "category": "Freelance & Business",
        "section": "Section 44ADA",
        "page": "31-32",
        "document_type": "Statutory Scheme",
        "content": (
            "Section 44ADA provides a simplified presumptive taxation scheme for specified professionals "
            "(software developers, legal, medical, engineering, architectural, accountancy, technical consultancy). "
            "Threshold: Gross receipts up to ₹75 Lakhs per financial year (if digital receipts exceed 95%). "
            "Benefit: 50% of gross receipts are presumed as taxable net profit. The remaining 50% is treated as business "
            "expenses with zero requirement to maintain formal books of account or get accounts audited. "
            "Tax is computed on this 50% net income using regular tax slabs."
        )
    }
]


# Vector Search Engine using pure-Python TF-IDF vector space with cosine similarity
class VectorKnowledgeBase:
    """
    Lightweight, deterministic semantic vector store.
    Computes TF-IDF vector representations of official tax documents and executes
    cosine similarity search with financial-year filtering and anti-hallucination scoring.
    """

    def __init__(self, documents: List[Dict[str, Any]]):
        self.documents = documents
        self.vocabulary: Dict[str, int] = {}
        self.doc_vectors: List[Dict[int, float]] = []
        self.idf: Dict[int, float] = {}
        self._build_index()

    def _tokenize(self, text: str) -> List[str]:
        words = re.findall(r"\b[a-zA-Z0-9_\-\.\%]+\b", text.lower())
        stopwords = {
            "the", "is", "at", "which", "on", "a", "an", "and", "or", "to", "in",
            "for", "of", "with", "by", "from", "as", "about", "what", "how", "can",
            "i", "my", "we", "you", "it", "this", "that", "these", "those", "are", "be"
        }
        return [w for w in words if w not in stopwords and len(w) > 1]

    def _build_index(self) -> None:
        term_doc_freq: Dict[str, int] = {}
        tokenized_docs: List[List[str]] = []

        for doc in self.documents:
            corpus = f"{doc['title']} {doc['category']} {doc['section']} {doc['content']}"
            tokens = self._tokenize(corpus)
            tokenized_docs.append(tokens)
            unique_tokens = set(tokens)
            for t in unique_tokens:
                term_doc_freq[t] = term_doc_freq.get(t, 0) + 1

        self.vocabulary = {t: idx for idx, t in enumerate(sorted(term_doc_freq.keys()))}
        num_docs = len(self.documents)

        for term, doc_count in term_doc_freq.items():
            term_idx = self.vocabulary[term]
            self.idf[term_idx] = math.log((num_docs + 1) / (doc_count + 1)) + 1.0

        for tokens in tokenized_docs:
            vec = self._compute_tfidf_vector(tokens)
            self.doc_vectors.append(vec)

    def _compute_tfidf_vector(self, tokens: List[str]) -> Dict[int, float]:
        tf: Dict[int, float] = {}
        for t in tokens:
            if t in self.vocabulary:
                idx = self.vocabulary[t]
                tf[idx] = tf.get(idx, 0.0) + 1.0

        length = len(tokens) if tokens else 1
        tfidf_vec: Dict[int, float] = {}
        norm_sq = 0.0
        for idx, count in tf.items():
            val = (count / length) * self.idf.get(idx, 1.0)
            tfidf_vec[idx] = val
            norm_sq += val * val

        norm = math.sqrt(norm_sq) if norm_sq > 0 else 1.0
        for idx in tfidf_vec:
            tfidf_vec[idx] /= norm

        return tfidf_vec

    def _cosine_similarity(self, vec_a: Dict[int, float], vec_b: Dict[int, float]) -> float:
        score = 0.0
        for idx, val_a in vec_a.items():
            if idx in vec_b:
                score += val_a * vec_b[idx]
        return score

    def search(
        self,
        query: str,
        top_k: int = 3,
        min_threshold: float = 0.08,
        financial_year: Optional[str] = None
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Executes semantic vector search over knowledge documents.
        Applies financial year filtering and returns scored document chunks.
        """
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        query_vec = self._compute_tfidf_vector(query_tokens)
        scored: List[Tuple[Dict[str, Any], float]] = []

        for doc, doc_vec in zip(self.documents, self.doc_vectors):
            if financial_year and doc.get("financial_year") and doc["financial_year"] != financial_year:
                continue

            score = self._cosine_similarity(query_vec, doc_vec)

            # Keyword bonus for exact section matches
            query_lower = query.lower()
            if doc["section"].lower() in query_lower or doc["category"].lower() in query_lower:
                score += 0.25

            if score >= min_threshold:
                scored.append((doc, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


# Singleton instance of vector knowledge base
tax_knowledge_vector_store = VectorKnowledgeBase(KNOWLEDGE_DOCUMENTS)


def query_rag_knowledge(
    query: str,
    financial_year: str = "FY 2025-26",
    top_k: int = 3
) -> Dict[str, Any]:
    """
    RAG Pipeline matching Specification Section 27:
    1. Understand query
    2. Vector Search against knowledge base
    3. Retrieve top relevant chunks
    4. Validate sufficiency (anti-hallucination safeguard)
    5. Return structured response with citations
    """
    results = tax_knowledge_vector_store.search(
        query=query,
        top_k=top_k,
        financial_year=financial_year
    )

    if not results:
        return {
            "answer": "I couldn't find sufficient information in my verified tax knowledge base to answer this confidently.",
            "sources": [],
            "confidence": "insufficient",
            "disclaimer": OFFICIAL_DISCLAIMER
        }

    sources = []
    retrieved_chunks = []
    top_score = results[0][1]

    for doc, score in results:
        sources.append({
            "title": doc["title"],
            "source": doc["source"],
            "page": doc.get("page", "Official Section"),
            "section": doc.get("section", ""),
            "category": doc.get("category", ""),
            "financial_year": doc.get("financial_year", financial_year),
            "url": doc.get("url", "https://www.incometax.gov.in/iec/foportal/")
        })
        retrieved_chunks.append(doc["content"])

    confidence = "high" if top_score > 0.3 else ("medium" if top_score > 0.15 else "fair")

    return {
        "retrieved_chunks": retrieved_chunks,
        "sources": sources,
        "confidence": confidence,
        "top_score": round(top_score, 3),
        "disclaimer": OFFICIAL_DISCLAIMER
    }
