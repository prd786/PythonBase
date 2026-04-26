from __future__ import annotations

import json
import os
import sqlite3
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from flask import Flask, flash, g, redirect, render_template, request, send_file, url_for
from openpyxl import Workbook


BASE_DIR = Path(__file__).resolve().parent
JSON_DATA_FILE = BASE_DIR / "newfile.json"
DATABASE_FILE = BASE_DIR / "expenses.db"

app = Flask(__name__)
app.secret_key = "expense-tracker-dev-key"


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


def initialize_database() -> None:
    database = sqlite3.connect(DATABASE_FILE)
    try:
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


def fetch_expenses(selected_category: str, query_text: str) -> list[dict[str, Any]]:
    sql = """
        SELECT id, title, category, expense_date, amount, created_at
        FROM expenses
        WHERE 1 = 1
    """
    params: list[Any] = []

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


def build_summary() -> dict[str, Any]:
    database = get_db()
    totals = database.execute(
        """
        SELECT
            COUNT(*) AS entry_count,
            COALESCE(SUM(amount), 0) AS total_amount,
            COALESCE(AVG(amount), 0) AS average_amount
        FROM expenses
        """
    ).fetchone()

    categories = [
        row["category"]
        for row in database.execute(
            "SELECT DISTINCT category FROM expenses ORDER BY category ASC"
        ).fetchall()
    ]

    top_category = database.execute(
        """
        SELECT category, SUM(amount) AS total_amount
        FROM expenses
        GROUP BY category
        ORDER BY total_amount DESC, category ASC
        LIMIT 1
        """
    ).fetchone()

    category_breakdown_rows = database.execute(
        """
        SELECT category, COUNT(*) AS entry_count, SUM(amount) AS total_amount
        FROM expenses
        GROUP BY category
        ORDER BY total_amount DESC, category ASC
        """
    ).fetchall()

    recent_items = [
        serialize_expense(row)
        for row in database.execute(
            """
            SELECT id, title, category, expense_date, amount, created_at
            FROM expenses
            ORDER BY expense_date DESC, datetime(created_at) DESC, id DESC
            LIMIT 5
            """
        ).fetchall()
    ]

    monthly_rows = database.execute(
        """
        SELECT substr(expense_date, 1, 7) AS month_key, SUM(amount) AS total_amount
        FROM expenses
        GROUP BY month_key
        ORDER BY month_key DESC
        LIMIT 6
        """
    ).fetchall()

    return {
        "total": float(totals["total_amount"] or 0.0),
        "count": int(totals["entry_count"] or 0),
        "average": float(totals["average_amount"] or 0.0),
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


def get_expense_by_id(expense_id: int) -> dict[str, Any] | None:
    row = get_db().execute(
        """
        SELECT id, title, category, expense_date, amount, created_at
        FROM expenses
        WHERE id = ?
        """,
        (expense_id,),
    ).fetchone()
    return serialize_expense(row) if row else None


@app.route("/", methods=["GET"])
def index():
    selected_category = request.args.get("category", "").strip()
    query_text = request.args.get("q", "").strip()
    edit_id = request.args.get("edit", type=int)

    return render_template(
        "index.html",
        expenses=fetch_expenses(selected_category, query_text),
        summary=build_summary(),
        selected_category=selected_category,
        query=query_text,
        today=date.today().strftime("%Y-%m-%d"),
        editing_expense=get_expense_by_id(edit_id) if edit_id else None,
    )


@app.route("/add", methods=["POST"])
def add_expense():
    payload, error_message = validate_expense_form(request.form)
    if error_message:
        flash(error_message, "error")
        return redirect(url_for("index"))

    get_db().execute(
        """
        INSERT INTO expenses (title, category, expense_date, amount)
        VALUES (:title, :category, :expense_date, :amount)
        """,
        payload,
    )
    get_db().commit()
    flash("Expense added successfully.", "success")
    return redirect(url_for("index"))


@app.route("/edit/<int:expense_id>", methods=["POST"])
def edit_expense(expense_id: int):
    payload, error_message = validate_expense_form(request.form)
    if error_message:
        flash(error_message, "error")
        return redirect(url_for("index", edit=expense_id))

    cursor = get_db().execute(
        """
        UPDATE expenses
        SET title = :title,
            category = :category,
            expense_date = :expense_date,
            amount = :amount
        WHERE id = :id
        """,
        {**payload, "id": expense_id},
    )
    get_db().commit()

    if cursor.rowcount == 0:
        flash("Expense not found.", "error")
    else:
        flash("Expense updated successfully.", "success")
    return redirect(url_for("index"))


@app.route("/delete/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id: int):
    cursor = get_db().execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    get_db().commit()

    if cursor.rowcount == 0:
        flash("Expense not found.", "error")
    else:
        flash("Expense deleted.", "success")
    return redirect(url_for("index"))


@app.route("/export/excel", methods=["GET"])
def export_excel():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Expenses"
    sheet.append(["ID", "Title", "Category", "Date", "Amount", "Created At"])

    rows = get_db().execute(
        """
        SELECT id, title, category, expense_date, amount, created_at
        FROM expenses
        ORDER BY expense_date DESC, datetime(created_at) DESC, id DESC
        """
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
