from datetime import date
from pathlib import Path
import sqlite3
import urllib.parse

# Compatibility for older Flask installations paired with newer Werkzeug.
try:
    import importlib.metadata
    import werkzeug.urls
    if not hasattr(werkzeug, "__version__"):
        werkzeug.__version__ = importlib.metadata.version("Werkzeug")
    if not hasattr(werkzeug.urls, "url_quote"):
        werkzeug.urls.url_quote = urllib.parse.quote
    if not hasattr(werkzeug.urls, "url_parse"):
        werkzeug.urls.url_parse = urllib.parse.urlparse
except ImportError:
    pass

from flask import Flask, flash, redirect, render_template, request, url_for


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "expenses.db"
DEFAULT_CATEGORIES = ["Food", "Transport", "Study", "Entertainment", "Shopping", "Other"]

app = Flask(__name__)
app.config["SECRET_KEY"] = "student-expense-tracker-local"


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_db() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL CHECK(amount > 0),
                category TEXT NOT NULL,
                expense_date TEXT NOT NULL,
                note TEXT DEFAULT ''
            )
            """
        )


def selected_month(value):
    return value if value and len(value) == 7 else date.today().strftime("%Y-%m")


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        amount_text = request.form.get("amount", "").strip()
        category = request.form.get("category", "").strip()
        expense_date = request.form.get("expense_date", "").strip()
        note = request.form.get("note", "").strip()

        try:
            amount = float(amount_text)
        except ValueError:
            amount = 0

        if amount <= 0:
            flash("Please enter an amount greater than zero.", "error")
        elif not category or not expense_date:
            flash("Please choose a category and date.", "error")
        else:
            with get_db() as connection:
                connection.execute(
                    "INSERT INTO expenses (amount, category, expense_date, note) VALUES (?, ?, ?, ?)",
                    (amount, category, expense_date, note),
                )
            flash("Expense added successfully!", "success")
            return redirect(url_for("index"))

    month = selected_month(request.args.get("month"))
    category_filter = request.args.get("category", "All")

    query = "SELECT * FROM expenses WHERE strftime('%Y-%m', expense_date) = ?"
    parameters = [month]
    if category_filter and category_filter != "All":
        query += " AND category = ?"
        parameters.append(category_filter)
    query += " ORDER BY expense_date DESC, id DESC"

    with get_db() as connection:
        expenses = connection.execute(query, parameters).fetchall()
        monthly_total = connection.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE strftime('%Y-%m', expense_date) = ?",
            (month,),
        ).fetchone()[0]
        category_totals = connection.execute(
            """
            SELECT category, SUM(amount) AS total
            FROM expenses
            WHERE strftime('%Y-%m', expense_date) = ?
            GROUP BY category ORDER BY total DESC
            """,
            (month,),
        ).fetchall()

    return render_template(
        "index.html",
        expenses=expenses,
        monthly_total=monthly_total,
        category_totals=category_totals,
        categories=DEFAULT_CATEGORIES,
        selected_month=month,
        category_filter=category_filter,
        today=date.today().isoformat(),
    )


@app.post("/delete/<int:expense_id>")
def delete_expense(expense_id):
    with get_db() as connection:
        connection.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    flash("Expense deleted.", "success")
    return redirect(url_for("index"))


init_db()

if __name__ == "__main__":
    app.run(debug=True)
