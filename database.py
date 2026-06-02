"""
database.py
-----------
Data-access layer for the Library Management System.

All SQL lives here so the GUI code (library_management.py) only ever
calls plain Python functions and never touches SQL directly. This keeps
the two Activities of the project cleanly separated:

    * Activity 2  -> GUI forms          (library_management.py)
    * Activity 3  -> DB connectivity    (this file)

The database is a single SQLite file (`library.db`) created next to this
script the first time it runs. SQLite ships with Python, so there is
nothing to install or configure.

Schema
======
    books         (book_id, title, author, isbn, total_copies, available)
    members       (member_id, name, email, phone, join_date)
    transactions  (txn_id, book_id, member_id, issue_date, due_date,
                   return_date, status)
"""

import os
import sqlite3
from datetime import date, timedelta

# Database file sits in the same folder as this script.
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "library.db")

# A book is on loan for this many days before it becomes overdue.
LOAN_DAYS = 14


def get_connection():
    """Open a connection to the SQLite database.

    `row_factory = sqlite3.Row` lets us access columns by name
    (row["title"]) instead of by index, which makes the GUI code readable.
    Foreign keys are enabled so the schema stays consistent.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create the tables if they do not exist, then seed sample data once."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            book_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            title         TEXT    NOT NULL,
            author        TEXT    NOT NULL,
            isbn          TEXT    UNIQUE,
            total_copies  INTEGER NOT NULL DEFAULT 1,
            available     INTEGER NOT NULL DEFAULT 1
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS members (
            member_id  INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            email      TEXT,
            phone      TEXT,
            join_date  TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            txn_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id      INTEGER NOT NULL,
            member_id    INTEGER NOT NULL,
            issue_date   TEXT NOT NULL,
            due_date     TEXT NOT NULL,
            return_date  TEXT,
            status       TEXT NOT NULL DEFAULT 'ISSUED',
            FOREIGN KEY (book_id)   REFERENCES books(book_id),
            FOREIGN KEY (member_id) REFERENCES members(member_id)
        )
        """
    )

    conn.commit()
    _seed_sample_data(conn)
    conn.close()


def _seed_sample_data(conn):
    """Insert a few demo rows the very first time, so the app isn't empty."""
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM books")
    if cur.fetchone()[0] == 0:
        sample_books = [
            ("The Pragmatic Programmer", "Hunt & Thomas", "9780201616224", 3, 3),
            ("Clean Code", "Robert C. Martin", "9780132350884", 2, 2),
            ("Introduction to Algorithms", "Cormen et al.", "9780262033848", 2, 2),
            ("Python Crash Course", "Eric Matthes", "9781593279288", 4, 4),
            ("The C Programming Language", "Kernighan & Ritchie", "9780131103627", 2, 2),
        ]
        cur.executemany(
            "INSERT INTO books (title, author, isbn, total_copies, available) "
            "VALUES (?, ?, ?, ?, ?)",
            sample_books,
        )

    cur.execute("SELECT COUNT(*) FROM members")
    if cur.fetchone()[0] == 0:
        today = date.today().isoformat()
        sample_members = [
            ("Aarav Sharma", "aarav@example.com", "9876543210", today),
            ("Diya Patel", "diya@example.com", "9876500011", today),
            ("Kabir Singh", "kabir@example.com", "9811122233", today),
        ]
        cur.executemany(
            "INSERT INTO members (name, email, phone, join_date) VALUES (?, ?, ?, ?)",
            sample_members,
        )

    conn.commit()


# --------------------------------------------------------------------------- #
#  BOOKS
# --------------------------------------------------------------------------- #
def add_book(title, author, isbn, copies):
    """Add a new book. New books start with all copies available."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO books (title, author, isbn, total_copies, available) "
        "VALUES (?, ?, ?, ?, ?)",
        (title, author, isbn, copies, copies),
    )
    conn.commit()
    conn.close()


def update_book(book_id, title, author, isbn, copies):
    """Edit an existing book.

    `available` is shifted by the change in `total_copies` so that copies
    currently on loan are still accounted for and availability never goes
    negative.
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT total_copies, available FROM books WHERE book_id = ?", (book_id,)
    ).fetchone()
    on_loan = row["total_copies"] - row["available"]
    new_available = max(0, copies - on_loan)
    conn.execute(
        "UPDATE books SET title=?, author=?, isbn=?, total_copies=?, available=? "
        "WHERE book_id=?",
        (title, author, isbn, copies, new_available, book_id),
    )
    conn.commit()
    conn.close()


def delete_book(book_id):
    """Delete a book. Refuses if any copy is still on loan."""
    conn = get_connection()
    active = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE book_id=? AND status='ISSUED'",
        (book_id,),
    ).fetchone()[0]
    if active:
        conn.close()
        raise ValueError("Cannot delete: this book has copies currently issued.")
    conn.execute("DELETE FROM books WHERE book_id=?", (book_id,))
    conn.commit()
    conn.close()


def get_books(search=""):
    """Return all books, optionally filtered by a title/author/ISBN search."""
    conn = get_connection()
    if search:
        like = f"%{search}%"
        rows = conn.execute(
            "SELECT * FROM books WHERE title LIKE ? OR author LIKE ? OR isbn LIKE ? "
            "ORDER BY title",
            (like, like, like),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM books ORDER BY title").fetchall()
    conn.close()
    return rows


# --------------------------------------------------------------------------- #
#  MEMBERS
# --------------------------------------------------------------------------- #
def add_member(name, email, phone):
    conn = get_connection()
    conn.execute(
        "INSERT INTO members (name, email, phone, join_date) VALUES (?, ?, ?, ?)",
        (name, email, phone, date.today().isoformat()),
    )
    conn.commit()
    conn.close()


def update_member(member_id, name, email, phone):
    conn = get_connection()
    conn.execute(
        "UPDATE members SET name=?, email=?, phone=? WHERE member_id=?",
        (name, email, phone, member_id),
    )
    conn.commit()
    conn.close()


def delete_member(member_id):
    """Delete a member. Refuses if they still hold any issued book."""
    conn = get_connection()
    active = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE member_id=? AND status='ISSUED'",
        (member_id,),
    ).fetchone()[0]
    if active:
        conn.close()
        raise ValueError("Cannot delete: this member still has books issued.")
    conn.execute("DELETE FROM members WHERE member_id=?", (member_id,))
    conn.commit()
    conn.close()


def get_members(search=""):
    conn = get_connection()
    if search:
        like = f"%{search}%"
        rows = conn.execute(
            "SELECT * FROM members WHERE name LIKE ? OR email LIKE ? OR phone LIKE ? "
            "ORDER BY name",
            (like, like, like),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM members ORDER BY name").fetchall()
    conn.close()
    return rows


# --------------------------------------------------------------------------- #
#  ISSUE / RETURN
# --------------------------------------------------------------------------- #
def issue_book(book_id, member_id):
    """Issue one copy of a book to a member.

    Steps (the event-handling algorithm):
        1. Check the book has at least one available copy.
        2. Insert an ISSUED transaction with today's date and a due date
           LOAN_DAYS in the future.
        3. Decrement the book's `available` count.
    """
    conn = get_connection()
    book = conn.execute(
        "SELECT available FROM books WHERE book_id=?", (book_id,)
    ).fetchone()
    if book is None:
        conn.close()
        raise ValueError("Book not found.")
    if book["available"] <= 0:
        conn.close()
        raise ValueError("No copies available for this book.")

    issue_dt = date.today()
    due_dt = issue_dt + timedelta(days=LOAN_DAYS)
    conn.execute(
        "INSERT INTO transactions (book_id, member_id, issue_date, due_date, status) "
        "VALUES (?, ?, ?, ?, 'ISSUED')",
        (book_id, member_id, issue_dt.isoformat(), due_dt.isoformat()),
    )
    conn.execute(
        "UPDATE books SET available = available - 1 WHERE book_id=?", (book_id,)
    )
    conn.commit()
    conn.close()


def return_book(txn_id):
    """Return a previously issued book.

        1. Mark the transaction RETURNED and stamp today's return date.
        2. Increment the book's `available` count back up.
    """
    conn = get_connection()
    txn = conn.execute(
        "SELECT book_id, status FROM transactions WHERE txn_id=?", (txn_id,)
    ).fetchone()
    if txn is None:
        conn.close()
        raise ValueError("Transaction not found.")
    if txn["status"] == "RETURNED":
        conn.close()
        raise ValueError("This book has already been returned.")

    conn.execute(
        "UPDATE transactions SET return_date=?, status='RETURNED' WHERE txn_id=?",
        (date.today().isoformat(), txn_id),
    )
    conn.execute(
        "UPDATE books SET available = available + 1 WHERE book_id=?", (txn["book_id"],)
    )
    conn.commit()
    conn.close()


def get_issued_transactions():
    """Return all currently-issued (not yet returned) loans, with names joined."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT t.txn_id, b.title, m.name AS member, t.issue_date, t.due_date
        FROM transactions t
        JOIN books   b ON b.book_id   = t.book_id
        JOIN members m ON m.member_id = t.member_id
        WHERE t.status = 'ISSUED'
        ORDER BY t.due_date
        """
    ).fetchall()
    conn.close()
    return rows


# --------------------------------------------------------------------------- #
#  REPORTS
# --------------------------------------------------------------------------- #
def report_all_transactions():
    """Full transaction history (issued + returned), newest first."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT t.txn_id, b.title, m.name AS member, t.issue_date,
               t.due_date, t.return_date, t.status
        FROM transactions t
        JOIN books   b ON b.book_id   = t.book_id
        JOIN members m ON m.member_id = t.member_id
        ORDER BY t.txn_id DESC
        """
    ).fetchall()
    conn.close()
    return rows


def report_overdue():
    """Issued books whose due date is in the past."""
    today = date.today().isoformat()
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT t.txn_id, b.title, m.name AS member, t.issue_date, t.due_date
        FROM transactions t
        JOIN books   b ON b.book_id   = t.book_id
        JOIN members m ON m.member_id = t.member_id
        WHERE t.status = 'ISSUED' AND t.due_date < ?
        ORDER BY t.due_date
        """,
        (today,),
    ).fetchall()
    conn.close()
    return rows


def report_stock():
    """Inventory snapshot: total vs available copies per book."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT title, author, total_copies, available, "
        "(total_copies - available) AS on_loan FROM books ORDER BY title"
    ).fetchall()
    conn.close()
    return rows


def dashboard_stats():
    """A few headline numbers for the dashboard at the top of the window."""
    conn = get_connection()
    stats = {
        "total_books": conn.execute(
            "SELECT COALESCE(SUM(total_copies), 0) FROM books"
        ).fetchone()[0],
        "titles": conn.execute("SELECT COUNT(*) FROM books").fetchone()[0],
        "members": conn.execute("SELECT COUNT(*) FROM members").fetchone()[0],
        "issued": conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE status='ISSUED'"
        ).fetchone()[0],
        "overdue": conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE status='ISSUED' AND due_date < ?",
            (date.today().isoformat(),),
        ).fetchone()[0],
    }
    conn.close()
    return stats


if __name__ == "__main__":
    # Running this file directly just (re)initialises the database.
    init_db()
    print(f"Database ready at: {DB_PATH}")
