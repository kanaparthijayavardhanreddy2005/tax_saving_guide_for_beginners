"""
TaxWise AI - Main Application Server & REST API
Exposes endpoints for:
- User Authentication (Register, Login, Logout, Reset Password, Current User)
- Tax Calculation & Comparison Engine (Rule-based, versioned)
- Personalized Recommendations & Explainable AI
- Grounded RAG AI Assistant
- Tax Education Center & Document Explainer
- Admin Telemetry & Rule Management
"""

import os
import json
import hmac
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv

import database
import auth
from tax_engine import TaxCalculator, default_calculator
from recommendation_engine import evaluate_recommendations
from explainable_ai import explain_all_recommendations, generate_explanation
import rag_engine
import ai_assistant
import education_content
import admin_engine

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or os.urandom(32)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"


# -------------------------------------------------------------
# Main Web Application Route
# -------------------------------------------------------------
@app.route("/")
def index():
    """Renders the comprehensive single-page TaxWise AI application."""
    user_id = session.get("user_id")
    user_data = None
    if user_id:
        try:
            profile = auth.get_user_profile(user_id)
            if "user" in profile:
                user_data = profile["user"]
        except Exception:
            pass
    return render_template("index.html", user=user_data)


# -------------------------------------------------------------
# Authentication Endpoints (Specification Section 26)
# -------------------------------------------------------------
@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip()
    password = str(data.get("password", "")).strip()

    result = auth.register_user(name, email, password)
    if result.get("success"):
        session.clear()
        session["user_id"] = result["user"]["id"]
        session["user_name"] = result["user"]["name"]
        return jsonify(result), 201
    return jsonify(result), 400


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip()
    password = str(data.get("password", "")).strip()

    result = auth.authenticate_user(email, password)
    if result.get("success"):
        session.clear()
        session["user_id"] = result["user"]["id"]
        session["user_name"] = result["user"]["name"]
        return jsonify(result)
    return jsonify(result), 401


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully."})


@app.route("/api/auth/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json(silent=True) or {}
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Sign in before changing your password."}), 401

    current_password = str(data.get("current_password", ""))
    new_password = str(data.get("new_password", "")).strip()
    profile = auth.get_user_profile(user_id)
    user = profile.get("user")
    if not user or not auth.authenticate_user(user["email"], current_password).get("success"):
        return jsonify({"error": "Your current password is incorrect."}), 400

    result = auth.reset_user_password(user["email"], new_password)
    if result.get("success"):
        return jsonify(result)
    return jsonify(result), 400


@app.route("/api/auth/me", methods=["GET"])
def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"authenticated": False, "user": None})
    try:
        profile = auth.get_user_profile(user_id)
        return jsonify({"authenticated": True, "user": profile.get("user"), "profile": profile})
    except Exception:
        return jsonify({"authenticated": False, "user": None})


# -------------------------------------------------------------
# Profile Endpoints
# -------------------------------------------------------------
@app.route("/api/profile", methods=["GET", "PUT"])
def profile_handler():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Please sign in to access your tax profile."}), 401

    if request.method == "GET":
        profile = auth.get_user_profile(user_id)
        return jsonify(profile)

    # PUT
    data = request.get_json(silent=True) or {}
    result = auth.update_user_profile(user_id, data)
    return jsonify(result)


# -------------------------------------------------------------
# Tax Calculation Endpoints (Rule-Based & Deterministic)
# -------------------------------------------------------------
@app.route("/api/tax/calculate", methods=["POST"])
@app.route("/api/calculate", methods=["POST"])  # Backwards compatibility
def calculate_tax_api():
    try:
        data = request.get_json(silent=True) or {}
        gross_income = float(data.get("gross_income", 0.0))

        if gross_income < 0:
            return jsonify({"error": "Gross income cannot be a negative number."}), 400

        financial_year = str(data.get("financial_year", "FY 2025-26"))
        is_salaried = bool(data.get("is_salaried", True))
        regime = str(data.get("regime", "new")).lower()
        age = int(data.get("age", 28))
        if age < 0 or age > 120:
            return jsonify({"error": "Age must be between 0 and 120."}), 400
        is_resident = (
            data.get("is_resident") is True
            if "is_resident" in data
            else str(data.get("residential_status", "resident")).lower() == "resident"
        )
        if regime not in {"new", "old"}:
            return jsonify({"error": "Choose either the new or old tax regime."}), 400

        # Deduction items
        sec_80c = float(data.get("sec_80c", 0.0))
        sec_80d = float(data.get("sec_80d", 0.0))
        hra = float(data.get("hra_exemption", data.get("rent_paid", 0.0)))
        nps = float(data.get("sec_80ccd_1b", 0.0))
        home_loan = float(data.get("home_loan_24b", 0.0))
        edu_loan = float(data.get("education_loan_80e", 0.0))
        donations = float(data.get("donations_80g", 0.0))
        tta = float(data.get("savings_interest_80tta", 0.0))
        nps_employer = float(data.get("nps_employer_80ccd2", 0.0))
        other_ded = float(data.get("other_deductions", 0.0))

        # Check for negative amounts
        for name, val in [("80C", sec_80c), ("80D", sec_80d), ("HRA", hra), ("NPS", nps)]:
            if val < 0:
                return jsonify({"error": f"{name} deduction cannot be negative."}), 400

        calc = TaxCalculator(financial_year=financial_year)

        # Calculate for selected regime
        result = calc.calculateFinalTax(
            gross_income=gross_income,
            is_salaried=is_salaried,
            regime=regime,
            age=age,
            is_resident=is_resident,
            sec_80c=sec_80c,
            sec_80d=sec_80d,
            hra_exemption=hra,
            sec_80ccd_1b=nps,
            home_loan_interest_24b=home_loan,
            education_loan_interest_80e=edu_loan,
            donations_80g=donations,
            savings_interest_80tta=tta,
            nps_employer_80ccd2=nps_employer,
            other_deductions=other_ded
        )

        # Full comparison
        comparison = calc.compareRegimes(
            gross_income=gross_income,
            is_salaried=is_salaried,
            age=age,
            is_resident=is_resident,
            sec_80c=sec_80c,
            sec_80d=sec_80d,
            hra_exemption=hra,
            sec_80ccd_1b=nps,
            home_loan_interest_24b=home_loan,
            education_loan_interest_80e=edu_loan,
            donations_80g=donations,
            savings_interest_80tta=tta,
            nps_employer_80ccd2=nps_employer,
            other_deductions=other_ded
        )

        # Personalized recommendations & Explainable AI
        user_profile_payload = dict(data)
        raw_recommendations = evaluate_recommendations(user_profile_payload, financial_year=financial_year)
        explained_recommendations = explain_all_recommendations(raw_recommendations, user_profile_payload)

        return jsonify({
            "status": "success",
            "active_regime": regime,
            "financial_year": financial_year,
            "result": result,
            "comparison": comparison,
            "recommendations": explained_recommendations,
            "meta": {
                "disclaimer": rag_engine.OFFICIAL_DISCLAIMER,
                "source": "Income Tax Department of India & Union Budget 2025"
            }
        })
    except ValueError as e:
        return jsonify({"error": f"Invalid numerical value: {str(e)}"}), 400
    except Exception as e:
        app.logger.exception("Calculation error")
        return jsonify({"error": f"An error occurred during calculation: {str(e)}"}), 500


@app.route("/api/tax/compare", methods=["POST"])
def compare_tax_api():
    """Generates side-by-side scenario comparison with neutral explanation."""
    try:
        data = request.get_json(silent=True) or {}
        gross_income = max(0.0, float(data.get("gross_income", 0.0)))
        financial_year = str(data.get("financial_year", "FY 2025-26"))
        is_salaried = bool(data.get("is_salaried", True))
        age = int(data.get("age", 28))
        is_resident = (
            data.get("is_resident") is True
            if "is_resident" in data
            else str(data.get("residential_status", "resident")).lower() == "resident"
        )

        calc = TaxCalculator(financial_year=financial_year)
        comparison = calc.compareRegimes(
            gross_income=gross_income,
            is_salaried=is_salaried,
            age=age,
            is_resident=is_resident,
            sec_80c=float(data.get("sec_80c", 0.0)),
            sec_80d=float(data.get("sec_80d", 0.0)),
            hra_exemption=float(data.get("hra_exemption", 0.0)),
            sec_80ccd_1b=float(data.get("sec_80ccd_1b", 0.0)),
            home_loan_interest_24b=float(data.get("home_loan_24b", 0.0)),
            education_loan_interest_80e=float(data.get("education_loan_80e", 0.0)),
            donations_80g=float(data.get("donations_80g", 0.0)),
            savings_interest_80tta=float(data.get("savings_interest_80tta", 0.0))
        )
        return jsonify(comparison)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# -------------------------------------------------------------
# Recommendations & Explainable AI Endpoints
# -------------------------------------------------------------
@app.route("/api/recommendations", methods=["GET", "POST"])
def recommendations_api():
    try:
        data = request.get_json(silent=True) or {}
        financial_year = str(data.get("financial_year", "FY 2025-26"))
        recs = evaluate_recommendations(data, financial_year=financial_year)
        explained = explain_all_recommendations(recs, data)
        return jsonify({
            "status": "success",
            "count": len(explained),
            "recommendations": explained
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# -------------------------------------------------------------
# RAG-Based AI Assistant Chat Endpoint
# -------------------------------------------------------------
@app.route("/api/chat", methods=["POST"])
def chat_api():
    try:
        data = request.get_json(silent=True) or {}
        question = str(data.get("question", "")).strip()

        if not question:
            return jsonify({"error": "Please provide a question for TaxWise AI."}), 400

        if len(question) > 2000:
            return jsonify({"error": "Please keep your question under 2,000 characters."}), 400

        user_context = data.get("user_context", {})
        conversation_history = data.get("conversation_history", [])
        beginner_mode = bool(data.get("beginner_mode", True))
        financial_year = str(data.get("financial_year", "FY 2025-26"))

        # Execute grounded RAG workflow
        response = ai_assistant.ask_taxwise_ai(
            question=question,
            user_context=user_context,
            conversation_history=conversation_history,
            beginner_mode=beginner_mode,
            financial_year=financial_year
        )

        # Store in chat history table if user is logged in
        user_id = session.get("user_id")
        if user_id:
            conn = None
            try:
                conn = database.get_db_connection()
                conn.execute(
                    "INSERT INTO chat_history (user_id, question, answer, sources) VALUES (%s, %s, %s, %s)",
                    (user_id, question, response["answer"], json.dumps(response.get("sources", [])))
                )
                conn.commit()
            except Exception:
                app.logger.exception("Unable to persist chat history")
            finally:
                if conn is not None:
                    conn.close()

        return jsonify(response)
    except Exception as e:
        app.logger.exception("Chat API error")
        return jsonify({
            "error": "Failed to process chat request.",
            "details": str(e)
        }), 500


@app.route("/api/chat/history", methods=["GET"])
def chat_history_api():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"history": []})

    conn = database.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id, question, answer, sources, timestamp FROM chat_history WHERE user_id = %s ORDER BY id DESC LIMIT 20",
            (user_id,)
        )
        rows = cursor.fetchall()
        history = []
        for r in rows:
            history.append({
                "id": r["id"],
                "question": r["question"],
                "answer": r["answer"],
                "sources": json.loads(r["sources"]) if r["sources"] else [],
                "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None
            })
        return jsonify({"history": history})
    finally:
        conn.close()


# -------------------------------------------------------------
# Tax Education Center & Document Explainer Endpoints
# -------------------------------------------------------------
@app.route("/api/education/topics", methods=["GET"])
def education_topics_api():
    return jsonify({
        "topics": education_content.get_all_education_topics(),
        "disclaimer": rag_engine.OFFICIAL_DISCLAIMER
    })


@app.route("/api/documents", methods=["GET"])
def documents_api():
    return jsonify({
        "documents": education_content.get_all_tax_documents(),
        "disclaimer": rag_engine.OFFICIAL_DISCLAIMER
    })


@app.route("/api/documents/explain", methods=["POST"])
def explain_document_api():
    data = request.get_json(silent=True) or {}
    doc_id = str(data.get("document_id", "")).strip()
    doc = education_content.get_document_by_id(doc_id)
    if not doc:
        return jsonify({"error": f"Document '{doc_id}' not found."}), 404
    return jsonify({"document": doc})


# -------------------------------------------------------------
# Tax Rules & Admin Telemetry Endpoints
# -------------------------------------------------------------
@app.route("/api/tax-rules", methods=["GET"])
def tax_rules_api():
    fy = request.args.get("financial_year")
    rules = admin_engine.get_all_tax_rules(financial_year=fy)
    return jsonify({"rules": rules})


@app.route("/api/admin/stats", methods=["GET"])
def admin_stats_api():
    if not _admin_authorized():
        return jsonify({"error": "Admin authorization is required."}), 403
    stats = admin_engine.get_system_statistics()
    return jsonify(stats)


@app.route("/api/admin/rules", methods=["POST"])
def admin_save_rule_api():
    if not _admin_authorized():
        return jsonify({"error": "Admin authorization is required."}), 403
    data = request.get_json(silent=True) or {}
    result = admin_engine.add_or_update_tax_rule(data)
    return jsonify(result)


def _admin_authorized() -> bool:
    expected_token = os.getenv("ADMIN_API_TOKEN", "")
    provided_token = request.headers.get("X-Admin-Token", "")
    return bool(expected_token) and hmac.compare_digest(provided_token, expected_token)


@app.route("/api/health")
def health():
    return jsonify({
        "status": "healthy",
        "service": "TaxWise AI",
        "version": "2.0.0",
        "rag_status": "active",
        "gemini_sdk_available": ai_assistant.GENAI_AVAILABLE
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "0").strip().lower() in {"1", "true", "yes"}
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False)
