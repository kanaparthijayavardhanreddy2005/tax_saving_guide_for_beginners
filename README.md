# TaxWise AI: Intelligent Tax Saving Guide for Beginners 🇮🇳

TaxWise AI is a responsive Indian income-tax guidance prototype for beginners, students, and young professionals.

The platform combines the **five mandatory architectural pillars**:
1. **RAG (Retrieval-Augmented Generation)**: Local TF-IDF retrieval over curated tax passages, filtered by financial year and returned with source metadata. The current prototype does not ingest PDFs or use an external vector database.
2. **NLP + LLM Conversational Layer**: Natural language question understanding with an "Explain Like I'm a Beginner" toggle and multi-turn context retention.
3. **Rule-Based Tax Calculation Engine**: Versioned by Financial Year (`FY 2024-25` and `FY 2025-26`). Deterministic calculations that never rely on LLMs for financial arithmetic.
4. **Personalized Tax-Saving Recommendation Engine**: Evaluates financial profiles against statutory rules and classifies opportunities into *Eligible*, *Potentially Eligible*, *Requires Additional Information*, and *Not Applicable*.
5. **Explainable AI (XAI) Layer**: Visible "Why am I seeing this?" transparency expander detailing triggering inputs, rules, logic, and missing information for every recommendation.

---

## 🏛️ System Architecture

```text
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

## 📦 Project Structure

```text
TaxWise AI/
├── app.py                      # Flask server & REST API endpoints
├── tax_engine.py               # Deterministic Rule-Based Tax Calculator (TaxCalculator class)
├── recommendation_engine.py    # Personalized Tax Recommendation & Ranking Engine
├── explainable_ai.py           # Explainable AI layer ("Why am I seeing this?")
├── rag_engine.py               # In-memory TF-IDF retrieval over maintained passages
├── ai_assistant.py             # NLP + LLM assistant with Gemini API & grounded knowledge base
├── education_content.py        # Tax Education Center & Document Explainer data
├── admin_engine.py             # Admin telemetry, rule versioning, and document viewer
├── auth.py                     # User authentication, password hashing, and profile management
├── database.py                 # PostgreSQL connections and explicit schema/rule initialization
├── schema.sql                  # Supabase PostgreSQL schema
├── migrate_sqlite_to_postgres.py # One-off additive migration of the legacy local database
├── vercel.json                 # Vercel Python function routing
├── api/
│   └── index.py                # Vercel Flask application entry point
├── test_taxwise.py             # Comprehensive test suite covering calculations, RAG, and APIs
├── PROJECT_DOCUMENTATION.md    # 26-chapter technical documentation specification
├── requirements.txt            # Python dependencies
├── .env.example                # Environment configuration template
├── templates/
│   └── index.html              # Modern, responsive single-page application with 10 navigation views
└── static/
    ├── css/
    │   └── style.css           # Premium FinTech design system (Navy/Blue/Green, responsive)
    └── js/
        └── app.js              # 8-step wizard controller, Chart.js donut chart, RAG chat controller
```

---

## ⚡ Quick Start Guide

### 1. Prerequisites
- Python 3.10 or higher installed.

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Configure Local Secrets
```powershell
Copy-Item .env.example .env
```
Create a Supabase project and set `DATABASE_URL` in `.env` to its PostgreSQL connection string. For Vercel, use the Supabase session or transaction pooler connection string and keep the password private. Set a private random `SECRET_KEY` and a separate `ADMIN_API_TOKEN`. Leave `SESSION_COOKIE_SECURE=0` for local HTTP; set it to `1` when serving the app over HTTPS.
`FLASK_DEBUG` defaults to `0`; enable it only for local development. The Werkzeug reloader is disabled to keep startup compatible with hosted/threaded environments.

### 4. Create the Supabase schema
In the Supabase SQL Editor, execute the contents of [`schema.sql`](./schema.sql). It creates all seven application tables, including `financial_inputs`, which persists itemized profile data. The application does not connect to PostgreSQL, create tables, or seed data merely by importing `app.py`.

Alternatively, after setting `DATABASE_URL` in `.env`, the explicit local initializer runs the schema and seeds default tax rules if that table is empty:
```powershell
python database.py
```

### 5. Preserve data from the old SQLite database
Back up the existing `taxwise.db` before migrating. After applying `schema.sql` and configuring `DATABASE_URL`, run:
```powershell
python migrate_sqlite_to_postgres.py
```
The utility copies rows from all existing tables in dependency order, preserves IDs and timestamps, updates PostgreSQL identity sequences, and skips only identical existing rows on retry. It is additive: it never changes or deletes the SQLite source or existing PostgreSQL rows. Conflicting rows fail the transaction and must be resolved before retrying. `sqlite3` is used only by this one-off migration utility, not by application/runtime database operations.

### 6. Run the Automated Test Suite
```powershell
python test_taxwise.py
```

### 7. Run the Application
```powershell
python app.py
```

Open your browser at:
👉 **[http://localhost:5000](http://localhost:5000)**

## Vercel Deployment
1. Push the project to GitHub and import that repository in Vercel. The included [`vercel.json`](./vercel.json) routes requests to the Flask function in [`api/index.py`](./api/index.py), including the existing templates and static assets.
2. In Vercel **Project Settings → Environment Variables**, configure `DATABASE_URL`, `SECRET_KEY`, `ADMIN_API_TOKEN`, `SESSION_COOKIE_SECURE=1`, and (if enabled) `GEMINI_API_KEY` / `GEMINI_MODEL`. Add them for every environment you use (Production, Preview, and Development).
3. Apply [`schema.sql`](./schema.sql) in the Supabase SQL Editor. From a trusted local machine with the production `DATABASE_URL` set, run `python database.py` once to seed default tax rules (the schema creation is idempotent). Vercel does not create tables or seed rules during application startup. Database access requires `DATABASE_URL`; never commit `.env` or database credentials.
4. To deploy later changes, push them to the connected GitHub branch; Vercel redeploys automatically. You can also trigger a redeployment from the Vercel project’s **Deployments** page.

Typical GitHub push steps (replace `<branch>` with the branch you intend to deploy):
```powershell
git add README.md .env.example admin_engine.py app.py auth.py database.py requirements.txt test_taxwise.py api/index.py migrate_sqlite_to_postgres.py schema.sql vercel.json
git commit -m "Migrate TaxWise AI to Supabase PostgreSQL"
git push origin <branch>
```

`taxwise.db` remains ignored by Git and is not deployed; migrate it from the machine where the file exists using the utility above.

## Prototype Boundaries
- Knowledge passages and their citation metadata are maintained in code; PDF/web ingestion, embedding generation, and persistent vector indexing are not implemented.
- Source links currently point to the Income Tax Department portal, not to an independently verified document page for every passage. Verify current statutes before relying on a tax claim.
- Password changes require an authenticated session and the current password. Email-based forgotten-password recovery is not configured.
- Admin telemetry and rule writes require the separately configured `ADMIN_API_TOKEN`.
- Tax estimates are not certified filing calculations; the supported years are FY 2024-25 and FY 2025-26.

---

## ⚖️ Disclaimer

TaxWise AI provides educational information and estimates based on the information available in its knowledge base. Tax rules may change, and eligibility depends on individual circumstances. Always verify current rules using official sources or consult a qualified tax professional before filing or making financial decisions.
