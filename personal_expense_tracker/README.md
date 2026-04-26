# Personal Expense Tracker

This project is now a Flask-based web app for managing personal expenses with a modern interface and SQLite database storage.

## Features

- Add expenses from a browser form
- View spending in a clean dashboard
- Search and filter by category
- See total, average, and top category insights
- Edit and delete saved expenses
- Category summaries powered by SQL queries
- Export all expenses to Excel (`.xlsx`)
- Keep data stored locally in SQLite

## Run the project

```bash
pip install -r requirements.txt
python3 main.py
```

Then open `http://127.0.0.1:5001`

## Data storage

The app stores live data in `expenses.db`. Existing data from `newfile.json` is imported automatically the first time the database is created.
