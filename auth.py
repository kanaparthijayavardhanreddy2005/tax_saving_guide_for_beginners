"""
TaxWise AI - Authentication & User Profile Management
Implements:
- User Registration with hashed passwords (Werkzeug security)
- Login & Session Authentication
- Password Reset
- Profile persistence & retrieval
- Protection against unauthorized data access
"""

from typing import Dict, Any, Optional
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection


def register_user(name: str, email: str, password: str) -> Dict[str, Any]:
    """Registers a new user with secure password hashing."""
    name = name.strip()
    email = email.strip().lower()

    if not name or len(name) < 2:
        return {"success": False, "error": "Please enter a valid name (at least 2 characters)."}
    if not email or "@" not in email or "." not in email:
        return {"success": False, "error": "Please enter a valid email address."}
    if not password or len(password) < 12:
        return {"success": False, "error": "Password must be at least 12 characters long."}

    password_hash = generate_password_hash(password)
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            conn.close()
            return {"success": False, "error": "An account with this email already exists."}

        cursor.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s) RETURNING id",
            (name, email, password_hash)
        )
        user_id = cursor.fetchone()["id"]

        # Initialize default tax profile for this user
        cursor.execute(
            "INSERT INTO tax_profiles (user_id, financial_year, income, employment_type, age, other_income, regime) "
            "VALUES (%s, 'FY 2025-26', 1200000.0, 'salaried', 28, 0.0, 'new')",
            (user_id,)
        )
        conn.commit()

        return {
            "success": True,
            "user": {
                "id": user_id,
                "name": name,
                "email": email
            }
        }
    except Exception as e:
        return {"success": False, "error": f"Registration failed: {str(e)}"}
    finally:
        conn.close()


def authenticate_user(email: str, password: str) -> Dict[str, Any]:
    """Validates user credentials and returns safe user data."""
    email = email.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, name, email, password_hash FROM users WHERE email = %s", (email,))
        row = cursor.fetchone()
        if not row:
            return {"success": False, "error": "Invalid email or password."}

        if not check_password_hash(row["password_hash"], password):
            return {"success": False, "error": "Invalid email or password."}

        return {
            "success": True,
            "user": {
                "id": row["id"],
                "name": row["name"],
                "email": row["email"]
            }
        }
    finally:
        conn.close()


def reset_user_password(email: str, new_password: str) -> Dict[str, Any]:
    """Resets user password securely."""
    email = email.strip().lower()
    if not new_password or len(new_password) < 12:
        return {"success": False, "error": "Password must be at least 12 characters long."}

    password_hash = generate_password_hash(new_password)
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        row = cursor.fetchone()
        if not row:
            return {"success": False, "error": "No account found with this email address."}

        cursor.execute("UPDATE users SET password_hash = %s WHERE email = %s", (password_hash, email))
        conn.commit()
        return {"success": True, "message": "Password updated successfully."}
    finally:
        conn.close()


def get_user_profile(user_id: int) -> Dict[str, Any]:
    """Retrieves full tax profile and saved financial inputs for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, name, email FROM users WHERE id = %s", (user_id,))
        user_row = cursor.fetchone()
        if not user_row:
            return {"error": "User not found"}

        cursor.execute(
            "SELECT * FROM tax_profiles WHERE user_id = %s ORDER BY id DESC LIMIT 1",
            (user_id,)
        )
        profile_row = cursor.fetchone()

        cursor.execute(
            "SELECT category, amount, description FROM financial_inputs WHERE user_id = %s",
            (user_id,)
        )
        inputs_rows = cursor.fetchall()
        financial_inputs = {r["category"]: float(r["amount"]) for r in inputs_rows}

        profile_data = {
            "user": {
                "id": user_row["id"],
                "name": user_row["name"],
                "email": user_row["email"]
            },
            "financial_year": profile_row["financial_year"] if profile_row else "FY 2025-26",
            "income": float(profile_row["income"]) if profile_row else 1200000.0,
            "employment_type": profile_row["employment_type"] if profile_row else "salaried",
            "age": int(profile_row["age"]) if profile_row else 28,
            "other_income": float(profile_row["other_income"]) if profile_row else 0.0,
            "regime": profile_row["regime"] if profile_row else "new",
            "financial_inputs": financial_inputs
        }
        return profile_data
    finally:
        conn.close()


def update_user_profile(user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Updates user tax profile and financial inputs atomically."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        income = max(0.0, float(data.get("income", data.get("gross_income", 0.0))))
        employment_type = str(data.get("employment_type", "salaried"))
        age = int(data.get("age", 28))
        other_income = max(0.0, float(data.get("other_income", 0.0)))
        regime = str(data.get("regime", "new")).lower()
        fy = str(data.get("financial_year", "FY 2025-26"))

        # Upsert tax profile
        cursor.execute("SELECT id FROM tax_profiles WHERE user_id = %s", (user_id,))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("""
            UPDATE tax_profiles
            SET financial_year = %s, income = %s, employment_type = %s, age = %s, other_income = %s, regime = %s, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
            """, (fy, income, employment_type, age, other_income, regime, user_id))
        else:
            cursor.execute("""
            INSERT INTO tax_profiles (user_id, financial_year, income, employment_type, age, other_income, regime)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, fy, income, employment_type, age, other_income, regime))

        # Update itemized financial inputs
        inputs = data.get("financial_inputs", {})
        cursor.execute("DELETE FROM financial_inputs WHERE user_id = %s", (user_id,))

        for category, amount in inputs.items():
            if amount is not None and float(amount) >= 0:
                cursor.execute("""
                INSERT INTO financial_inputs (user_id, category, amount, financial_year)
                VALUES (%s, %s, %s, %s)
                """, (user_id, category, float(amount), fy))

        conn.commit()
        return {"success": True, "message": "Tax profile updated successfully."}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()
