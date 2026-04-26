from __future__ import annotations

import json
import os
import secrets
import sqlite3
from datetime import date, datetime
from functools import wraps
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from openpyxl import Workbook
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = Path(__file__).resolve().parent
JSON_DATA_FILE = BASE_DIR / "newfile.json"
DATABASE_FILE = BASE_DIR / "expenses.db"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "expense-tracker-dev-key")

OAUTH_PROVIDERS = {
    "google": {
        "label": "Google",
        "client_id_env": "GOOGLE_CLIENT_ID",
        "client_secret_env": "GOOGLE_CLIENT_SECRET",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
        "scope": "openid email profile",
        "user_id_key": "sub",
    },
    "facebook": {
        "label": "Facebook",
        "client_id_env": "FACEBOOK_CLIENT_ID",
        "client_secret_env": "FACEBOOK_CLIENT_SECRET",
        "auth_url": "https://www.facebook.com/v19.0/dialog/oauth",
        "token_url": "https://graph.facebook.com/v19.0/oauth/access_token",
        "userinfo_url": "https://graph.facebook.com/me",
        "scope": "email,public_profile",
        "user_id_key": "id",
    },
}


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        connection = sqlite3.connect(DATABASE_FILE)
        connection.row_factory = sqlite3.Row
        g.db = connection
    return g.db


@app.teardown_appcontext
def close_db(_: Any) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


@app.before_request
def load_logged_in_user() -> None:
    user_id = session.get("user_id")
    g.user = get_user_by_id(user_id) if user_id else None


@app.context_processor
def inject_auth_state() -> dict[str, Any]:
    return {
        "oauth_enabled": {
            provider: oauth_is_configured(provider) for provider in OAUTH_PROVIDERS
        }
    }


def login_required(view):
    @wraps(view)
    def wrapped_view(*args: Any, **kwargs: Any):
        if g.user is None:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def normalize_json_item(raw_expense: dict[str, Any]) -> dict[str, Any] | None:
    raw_date = str(raw_expense.get("date", "")).strip()
    parsed_date = None

    for date_format in ("%Y-%m-%d", "%d-%m-%Y"):
        try:
            parsed_date = datetime.strptime(raw_date, date_format).date()
            break
        except ValueError:
            continue

    if parsed_date is None:
        return None

    title = str(raw_expense.get("title", "")).strip()
    category = str(raw_expense.get("category", "Other")).strip() or "Other"

    try:
        amount = float(raw_expense.get("amount", 0))
    except (TypeError, ValueError):
        return None

    if not title or amount <= 0:
        return None

    return {
        "title": title,
        "category": category,
        "expense_date": parsed_date.strftime("%Y-%m-%d"),
        "amount": amount,
    }


def load_json_expenses() -> list[dict[str, Any]]:
    if not JSON_DATA_FILE.exists():
        return []

    try:
        with JSON_DATA_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        return []

    normalized: list[dict[str, Any]] = []
    for item in data:
        if isinstance(item, dict):
            prepared = normalize_json_item(item)
            if prepared:
                normalized.append(prepared)
    return normalized


def ensure_column(database: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in database.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        database.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def initialize_database() -> None:
    database = sqlite3.connect(DATABASE_FILE)
    database.row_factory = sqlite3.Row
    try:
        database.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT,
                google_id TEXT UNIQUE,
                facebook_id TEXT UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        database.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                expense_date TEXT NOT NULL,
                amount REAL NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        ensure_column(database, "expenses", "user_id", "INTEGER REFERENCES users(id)")

        database.execute(
            """
            CREATE TABLE IF NOT EXISTS user_monthly_budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                month_key TEXT NOT NULL,
                amount REAL NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, month_key),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        database.execute(
            "CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, expense_date)"
        )

        existing_count = database.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        if existing_count == 0:
            records = load_json_expenses()
            if records:
                database.executemany(
                    """
                    INSERT INTO expenses (title, category, expense_date, amount)
                    VALUES (:title, :category, :expense_date, :amount)
                    """,
                    records,
                )
        database.commit()
    finally:
        database.close()


def serialize_expense(row: sqlite3.Row) -> dict[str, Any]:
    expense_date = datetime.strptime(row["expense_date"], "%Y-%m-%d").date()
    return {
        "id": row["id"],
        "title": row["title"],
        "category": row["category"],
        "date": row["expense_date"],
        "display_date": expense_date.strftime("%d %b %Y"),
        "amount": float(row["amount"]),
        "created_at": row["created_at"],
    }


def get_user_by_id(user_id: int | None) -> sqlite3.Row | None:
    if user_id is None:
        return None
    return get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def get_user_by_email(email: str) -> sqlite3.Row | None:
    return get_db().execute(
        "SELECT * FROM users WHERE lower(email) = lower(?)",
        (email.strip(),),
    ).fetchone()


def validate_registration_form(form: Any) -> tuple[dict[str, str] | None, str | None]:
    full_name = form.get("full_name", "").strip()
    email = form.get("email", "").strip().lower()
    password = form.get("password", "")
    confirm_password = form.get("confirm_password", "")

    if not full_name:
        return None, "Please enter your full name."
    if not email or "@" not in email:
        return None, "Please enter a valid email address."
    if len(password) < 6:
        return None, "Password must be at least 6 characters long."
    if password != confirm_password:
        return None, "Passwords do not match."

    return {"full_name": full_name, "email": email, "password": password}, None


def validate_login_form(form: Any) -> tuple[dict[str, str] | None, str | None]:
    email = form.get("email", "").strip().lower()
    password = form.get("password", "")

    if not email or "@" not in email:
        return None, "Please enter a valid email address."
    if not password:
        return None, "Please enter your password."

    return {"email": email, "password": password}, None


def validate_expense_form(form: Any) -> tuple[dict[str, Any] | None, str | None]:
    title = form.get("title", "").strip()
    category = form.get("category", "").strip() or "Other"
    date_value = form.get("date", "").strip()
    amount_value = form.get("amount", "").strip()

    if not title:
        return None, "Please enter an expense title."

    try:
        expense_date = parse_date(date_value).strftime("%Y-%m-%d")
    except ValueError:
        return None, "Please choose a valid date."

    try:
        amount = float(amount_value)
    except ValueError:
        return None, "Amount must be a valid number."

    if amount <= 0:
        return None, "Amount must be greater than zero."

    return {
        "title": title,
        "category": category,
        "expense_date": expense_date,
        "amount": amount,
    }, None


def validate_budget_form(form: Any) -> tuple[float | None, str | None]:
    amount_value = form.get("budget_amount", "").strip()

    try:
        amount = float(amount_value)
    except ValueError:
        return None, "Monthly budget must be a valid number."

    if amount <= 0:
        return None, "Monthly budget must be greater than zero."

    return amount, None


def validate_profile_form(form: Any) -> tuple[str | None, str | None]:
    full_name = form.get("full_name", "").strip()
    if not full_name:
        return None, "Please enter your name."
    return full_name, None


def validate_password_change(form: Any, has_existing_password: bool) -> tuple[str | None, str | None]:
    current_password = form.get("current_password", "")
    new_password = form.get("new_password", "")
    confirm_password = form.get("confirm_password", "")

    if has_existing_password and not current_password:
        return None, "Please enter your current password."
    if len(new_password) < 6:
        return None, "New password must be at least 6 characters long."
    if new_password != confirm_password:
        return None, "New passwords do not match."
    return current_password, None


def fetch_expenses(user_id: int, selected_category: str, query_text: str) -> list[dict[str, Any]]:
    sql = """
        SELECT id, title, category, expense_date, amount, created_at
        FROM expenses
        WHERE user_id = ?
    """
    params: list[Any] = [user_id]

    if selected_category:
        sql += " AND category = ?"
        params.append(selected_category)

    if query_text:
        like_term = f"%{query_text}%"
        sql += " AND (title LIKE ? OR category LIKE ?)"
        params.extend([like_term, like_term])

    sql += " ORDER BY expense_date DESC, datetime(created_at) DESC, id DESC"
    rows = get_db().execute(sql, params).fetchall()
    return [serialize_expense(row) for row in rows]


def build_summary(user_id: int) -> dict[str, Any]:
    database = get_db()
    current_month_key = date.today().strftime("%Y-%m")
    totals = database.execute(
        """
        SELECT
            COUNT(*) AS entry_count,
            COALESCE(SUM(amount), 0) AS total_amount,
            COALESCE(AVG(amount), 0) AS average_amount
        FROM expenses
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()

    categories = [
        row["category"]
        for row in database.execute(
            """
            SELECT DISTINCT category
            FROM expenses
            WHERE user_id = ?
            ORDER BY category ASC
            """,
            (user_id,),
        ).fetchall()
    ]

    top_category = database.execute(
        """
        SELECT category, SUM(amount) AS total_amount
        FROM expenses
        WHERE user_id = ?
        GROUP BY category
        ORDER BY total_amount DESC, category ASC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()

    category_breakdown_rows = database.execute(
        """
        SELECT category, COUNT(*) AS entry_count, SUM(amount) AS total_amount
        FROM expenses
        WHERE user_id = ?
        GROUP BY category
        ORDER BY total_amount DESC, category ASC
        """,
        (user_id,),
    ).fetchall()

    recent_items = [
        serialize_expense(row)
        for row in database.execute(
            """
            SELECT id, title, category, expense_date, amount, created_at
            FROM expenses
            WHERE user_id = ?
            ORDER BY expense_date DESC, datetime(created_at) DESC, id DESC
            LIMIT 5
            """,
            (user_id,),
        ).fetchall()
    ]

    monthly_rows = database.execute(
        """
        SELECT substr(expense_date, 1, 7) AS month_key, SUM(amount) AS total_amount
        FROM expenses
        WHERE user_id = ?
        GROUP BY month_key
        ORDER BY month_key DESC
        LIMIT 6
        """,
        (user_id,),
    ).fetchall()

    monthly_budget_row = database.execute(
        """
        SELECT amount
        FROM user_monthly_budgets
        WHERE user_id = ? AND month_key = ?
        """,
        (user_id, current_month_key),
    ).fetchone()

    current_month_totals = database.execute(
        """
        SELECT
            COUNT(*) AS entry_count,
            COALESCE(SUM(amount), 0) AS total_amount
        FROM expenses
        WHERE user_id = ? AND substr(expense_date, 1, 7) = ?
        """,
        (user_id, current_month_key),
    ).fetchone()

    monthly_budget = float(monthly_budget_row["amount"]) if monthly_budget_row else 0.0
    monthly_spend = float(current_month_totals["total_amount"] or 0.0)
    monthly_count = int(current_month_totals["entry_count"] or 0)
    monthly_remaining = monthly_budget - monthly_spend
    monthly_progress = min((monthly_spend / monthly_budget) * 100, 100.0) if monthly_budget > 0 else 0.0

    return {
        "total": float(totals["total_amount"] or 0.0),
        "count": int(totals["entry_count"] or 0),
        "average": float(totals["average_amount"] or 0.0),
        "current_month_label": datetime.strptime(current_month_key, "%Y-%m").strftime("%B %Y"),
        "monthly_budget": monthly_budget,
        "monthly_spend": monthly_spend,
        "monthly_remaining": monthly_remaining,
        "monthly_count": monthly_count,
        "monthly_progress": monthly_progress,
        "categories": categories,
        "top_category": top_category["category"] if top_category else "No data",
        "top_category_amount": float(top_category["total_amount"]) if top_category else 0.0,
        "recent_items": recent_items,
        "monthly_breakdown": [
            {
                "label": datetime.strptime(row["month_key"], "%Y-%m").strftime("%b %Y"),
                "amount": float(row["total_amount"]),
            }
            for row in monthly_rows
        ],
        "category_breakdown": [
            {
                "category": row["category"],
                "count": int(row["entry_count"]),
                "amount": float(row["total_amount"]),
            }
            for row in category_breakdown_rows
        ],
    }


def get_expense_by_id(user_id: int, expense_id: int) -> dict[str, Any] | None:
    row = get_db().execute(
        """
        SELECT id, title, category, expense_date, amount, created_at
        FROM expenses
        WHERE id = ? AND user_id = ?
        """,
        (expense_id, user_id),
    ).fetchone()
    return serialize_expense(row) if row else None


def oauth_is_configured(provider: str) -> bool:
    config = OAUTH_PROVIDERS[provider]
    return bool(os.environ.get(config["client_id_env"])) and bool(
        os.environ.get(config["client_secret_env"])
    )


def get_oauth_credentials(provider: str) -> tuple[str, str] | tuple[None, None]:
    config = OAUTH_PROVIDERS[provider]
    client_id = os.environ.get(config["client_id_env"])
    client_secret = os.environ.get(config["client_secret_env"])
    if not client_id or not client_secret:
        return None, None
    return client_id, client_secret


def load_json_response(request_object: Request) -> dict[str, Any]:
    with urlopen(request_object, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def exchange_oauth_code(provider: str, code: str) -> dict[str, Any]:
    config = OAUTH_PROVIDERS[provider]
    client_id, client_secret = get_oauth_credentials(provider)
    if not client_id or not client_secret:
        raise ValueError(f"{config['label']} login is not configured yet.")

    redirect_uri = url_for("oauth_callback", provider=provider, _external=True)

    if provider == "google":
        payload = urlencode(
            {
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }
        ).encode("utf-8")
        request_object = Request(
            config["token_url"],
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        return load_json_response(request_object)

    request_object = Request(
        f"{config['token_url']}?{urlencode({'client_id': client_id, 'client_secret': client_secret, 'redirect_uri': redirect_uri, 'code': code})}"
    )
    return load_json_response(request_object)


def fetch_oauth_profile(provider: str, access_token: str) -> dict[str, Any]:
    config = OAUTH_PROVIDERS[provider]
    if provider == "google":
        request_object = Request(
            config["userinfo_url"],
            headers={"Authorization": f"Bearer {access_token}"},
        )
        return load_json_response(request_object)

    request_object = Request(
        f"{config['userinfo_url']}?{urlencode({'fields': 'id,name,email', 'access_token': access_token})}"
    )
    return load_json_response(request_object)


def find_or_create_oauth_user(provider: str, profile: dict[str, Any]) -> sqlite3.Row:
    provider_column = "google_id" if provider == "google" else "facebook_id"
    provider_user_id = str(profile.get(OAUTH_PROVIDERS[provider]["user_id_key"], "")).strip()
    email = str(profile.get("email", "")).strip().lower()
    full_name = str(profile.get("name", "")).strip() or "Money Note User"

    if not provider_user_id:
        raise ValueError("Social login did not return a user id.")
    if not email:
        raise ValueError("This social account did not provide an email address.")

    database = get_db()
    user = database.execute(
        f"SELECT * FROM users WHERE {provider_column} = ?",
        (provider_user_id,),
    ).fetchone()
    if user:
        return user

    user = get_user_by_email(email)
    if user:
        database.execute(
            f"""
            UPDATE users
            SET {provider_column} = ?, full_name = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (provider_user_id, full_name, user["id"]),
        )
    else:
        database.execute(
            f"""
            INSERT INTO users (full_name, email, {provider_column})
            VALUES (?, ?, ?)
            """,
            (full_name, email, provider_user_id),
        )
    database.commit()
    return get_user_by_email(email)


@app.route("/", methods=["GET"])
def home():
    if g.user is not None:
        return redirect(url_for("dashboard"))
    return render_template("home.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user is not None:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        payload, error_message = validate_login_form(request.form)
        if error_message:
            flash(error_message, "error")
            return render_template("auth.html", mode="login")

        user = get_user_by_email(payload["email"])
        if user is None or not user["password_hash"]:
            flash("No account found with email/password login for this address.", "error")
            return render_template("auth.html", mode="login")

        if not check_password_hash(user["password_hash"], payload["password"]):
            flash("Incorrect password.", "error")
            return render_template("auth.html", mode="login")

        session.clear()
        session["user_id"] = user["id"]
        flash("Welcome back.", "success")
        return redirect(url_for("dashboard"))

    return render_template("auth.html", mode="login")


@app.route("/register", methods=["GET", "POST"])
def register():
    if g.user is not None:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        payload, error_message = validate_registration_form(request.form)
        if error_message:
            flash(error_message, "error")
            return render_template("auth.html", mode="register")

        if get_user_by_email(payload["email"]):
            flash("An account with that email already exists.", "error")
            return render_template("auth.html", mode="register")

        get_db().execute(
            """
            INSERT INTO users (full_name, email, password_hash)
            VALUES (?, ?, ?)
            """,
            (
                payload["full_name"],
                payload["email"],
                generate_password_hash(payload["password"]),
            ),
        )
        get_db().commit()
        user = get_user_by_email(payload["email"])
        session.clear()
        session["user_id"] = user["id"]
        flash("Your account is ready.", "success")
        return redirect(url_for("dashboard"))

    return render_template("auth.html", mode="register")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


@app.route("/oauth/<provider>", methods=["GET"])
def oauth_start(provider: str):
    if provider not in OAUTH_PROVIDERS:
        flash("Unknown social login provider.", "error")
        return redirect(url_for("login"))

    if not oauth_is_configured(provider):
        flash(
            f"{OAUTH_PROVIDERS[provider]['label']} login needs client credentials in environment variables first.",
            "error",
        )
        return redirect(url_for("login"))

    client_id, _ = get_oauth_credentials(provider)
    state = secrets.token_urlsafe(24)
    session[f"oauth_state_{provider}"] = state

    params = {
        "client_id": client_id,
        "redirect_uri": url_for("oauth_callback", provider=provider, _external=True),
        "response_type": "code",
        "scope": OAUTH_PROVIDERS[provider]["scope"],
        "state": state,
    }
    if provider == "google":
        params["prompt"] = "select_account"
        params["access_type"] = "online"

    return redirect(f"{OAUTH_PROVIDERS[provider]['auth_url']}?{urlencode(params)}")


@app.route("/oauth/<provider>/callback", methods=["GET"])
def oauth_callback(provider: str):
    if provider not in OAUTH_PROVIDERS:
        flash("Unknown social login provider.", "error")
        return redirect(url_for("login"))

    if request.args.get("state") != session.pop(f"oauth_state_{provider}", None):
        flash("Social login could not be verified. Please try again.", "error")
        return redirect(url_for("login"))

    if "error" in request.args:
        flash("Social login was cancelled or denied.", "error")
        return redirect(url_for("login"))

    code = request.args.get("code", "").strip()
    if not code:
        flash("Social login did not return an authorization code.", "error")
        return redirect(url_for("login"))

    try:
        token_data = exchange_oauth_code(provider, code)
        access_token = token_data.get("access_token", "")
        if not access_token:
            raise ValueError("Access token was not returned.")
        profile = fetch_oauth_profile(provider, access_token)
        user = find_or_create_oauth_user(provider, profile)
    except (ValueError, HTTPError, URLError, json.JSONDecodeError) as exc:
        flash(f"Could not complete {OAUTH_PROVIDERS[provider]['label']} login: {exc}", "error")
        return redirect(url_for("login"))

    session.clear()
    session["user_id"] = user["id"]
    flash(f"Signed in with {OAUTH_PROVIDERS[provider]['label']}.", "success")
    return redirect(url_for("dashboard"))


@app.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    selected_category = request.args.get("category", "").strip()
    query_text = request.args.get("q", "").strip()
    edit_id = request.args.get("edit", type=int)

    return render_template(
        "dashboard.html",
        expenses=fetch_expenses(g.user["id"], selected_category, query_text),
        summary=build_summary(g.user["id"]),
        selected_category=selected_category,
        query=query_text,
        today=date.today().strftime("%Y-%m-%d"),
        editing_expense=get_expense_by_id(g.user["id"], edit_id) if edit_id else None,
    )


@app.route("/account", methods=["GET"])
@login_required
def account():
    return render_template("account.html")


@app.route("/account/profile", methods=["POST"])
@login_required
def update_profile():
    full_name, error_message = validate_profile_form(request.form)
    if error_message:
        flash(error_message, "error")
        return redirect(url_for("account"))

    get_db().execute(
        """
        UPDATE users
        SET full_name = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (full_name, g.user["id"]),
    )
    get_db().commit()
    flash("Profile updated.", "success")
    return redirect(url_for("account"))


@app.route("/account/password", methods=["POST"])
@login_required
def update_password():
    has_existing_password = bool(g.user["password_hash"])
    current_password, error_message = validate_password_change(request.form, has_existing_password)
    if error_message:
        flash(error_message, "error")
        return redirect(url_for("account"))

    if has_existing_password and not check_password_hash(g.user["password_hash"], current_password):
        flash("Current password is incorrect.", "error")
        return redirect(url_for("account"))

    new_password = request.form.get("new_password", "")
    get_db().execute(
        """
        UPDATE users
        SET password_hash = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (generate_password_hash(new_password), g.user["id"]),
    )
    get_db().commit()
    flash("Password updated.", "success")
    return redirect(url_for("account"))


@app.route("/add", methods=["POST"])
@login_required
def add_expense():
    payload, error_message = validate_expense_form(request.form)
    if error_message:
        flash(error_message, "error")
        return redirect(url_for("dashboard"))

    get_db().execute(
        """
        INSERT INTO expenses (user_id, title, category, expense_date, amount)
        VALUES (:user_id, :title, :category, :expense_date, :amount)
        """,
        {**payload, "user_id": g.user["id"]},
    )
    get_db().commit()
    flash("Expense added successfully.", "success")
    return redirect(url_for("dashboard"))


@app.route("/budget", methods=["POST"])
@login_required
def save_budget():
    budget_amount, error_message = validate_budget_form(request.form)
    if error_message:
        flash(error_message, "error")
        return redirect(url_for("dashboard"))

    current_month_key = date.today().strftime("%Y-%m")
    get_db().execute(
        """
        INSERT INTO user_monthly_budgets (user_id, month_key, amount, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, month_key) DO UPDATE SET
            amount = excluded.amount,
            updated_at = CURRENT_TIMESTAMP
        """,
        (g.user["id"], current_month_key, budget_amount),
    )
    get_db().commit()
    flash("Monthly budget saved successfully.", "success")
    return redirect(url_for("dashboard"))


@app.route("/edit/<int:expense_id>", methods=["POST"])
@login_required
def edit_expense(expense_id: int):
    payload, error_message = validate_expense_form(request.form)
    if error_message:
        flash(error_message, "error")
        return redirect(url_for("dashboard", edit=expense_id))

    cursor = get_db().execute(
        """
        UPDATE expenses
        SET title = :title,
            category = :category,
            expense_date = :expense_date,
            amount = :amount
        WHERE id = :id AND user_id = :user_id
        """,
        {**payload, "id": expense_id, "user_id": g.user["id"]},
    )
    get_db().commit()

    if cursor.rowcount == 0:
        flash("Expense not found.", "error")
    else:
        flash("Expense updated successfully.", "success")
    return redirect(url_for("dashboard"))


@app.route("/delete/<int:expense_id>", methods=["POST"])
@login_required
def delete_expense(expense_id: int):
    cursor = get_db().execute(
        "DELETE FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, g.user["id"]),
    )
    get_db().commit()

    if cursor.rowcount == 0:
        flash("Expense not found.", "error")
    else:
        flash("Expense deleted.", "success")
    return redirect(url_for("dashboard"))


@app.route("/export/excel", methods=["GET"])
@login_required
def export_excel():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Expenses"
    sheet.append(["ID", "Title", "Category", "Date", "Amount", "Created At"])

    rows = get_db().execute(
        """
        SELECT id, title, category, expense_date, amount, created_at
        FROM expenses
        WHERE user_id = ?
        ORDER BY expense_date DESC, datetime(created_at) DESC, id DESC
        """,
        (g.user["id"],),
    ).fetchall()

    for row in rows:
        sheet.append(
            [
                row["id"],
                row["title"],
                row["category"],
                row["expense_date"],
                row["amount"],
                row["created_at"],
            ]
        )

    for column in ("A", "B", "C", "D", "E", "F"):
        sheet.column_dimensions[column].width = 20

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    filename = f"expense_report_{date.today().strftime('%Y%m%d')}.xlsx"
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


initialize_database()


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5001)))
