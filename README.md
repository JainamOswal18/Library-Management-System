# Library Management System (Python)

A simple desktop **Library Management System** built with **Python + Tkinter (GUI)** and
**SQLite (database)**. It lets a librarian manage a book catalogue and members, issue and
return books, and generate reports — all from a single window.

This project was written to satisfy **BCAB3206L: Software Lab – XII (Minor Project)**,
covering all three required activities (project idea, GUI form design, and event-handling
code with database connectivity and report generation).

---

## 1. Project Overview (Activity 1)

The application stores all data in a back-end **SQLite** database (`library.db`) and presents
it through **Tkinter** GUI forms. The user interacts with forms; the program handles the
events, runs SQL queries against the database, and displays the retrieved data and reports
back on screen.

It demonstrates the full required cycle:

| Requirement | Where it is met |
|-------------|-----------------|
| GUI forms for user interaction | Tkinter window with 4 tabs + dashboard |
| Data stored at the back end | SQLite database `library.db` |
| Retrieval of data from database | Search boxes, tables, and report queries |
| Report generation | Reports tab: transactions, overdue, stock |
| Database connectivity | `database.py` using Python's `sqlite3` module |

**Why this stack?** Both Tkinter and SQLite ship with the standard Python installation, so
the project runs anywhere Python is installed — **no libraries to install and no database
server to configure**.

---

## 2. Tech Stack

- **Language:** Python 3
- **GUI:** Tkinter / ttk (built-in)
- **Database:** SQLite via the `sqlite3` module (built-in)

No `pip install` step is required.

---

## 3. Setup & How to Run

### Prerequisites
- **Python 3.8 or newer.** Check with `python3 --version`.
- No third-party packages are required. The app uses only the standard library
  (`tkinter` for the GUI, `sqlite3` for the database).

> **Tkinter note:** It ships with the python.org and Homebrew Python installers on
> macOS/Windows. On some Linux distributions it is a separate system package:
> `sudo apt install python3-tk` (Debian/Ubuntu) or `sudo dnf install python3-tkinter` (Fedora).

### Steps

1. **Get the code** (clone, or download and unzip):
   ```bash
   git clone git@github.com:JainamOswal18/Library-Management-System.git
   cd Library-Management-System
   ```

2. **Run the application:**
   ```bash
   python3 library_management.py
   ```

   > On macOS/Linux use `python3`. On Windows use `python`.

A desktop window titled **"Library Management System"** opens. On first launch the program
automatically creates `library.db` and seeds a few sample books and members so the screens
are not empty.

> **Tip:** the GUI runs in its own window — while it is open the terminal will look "busy".
> That is normal; closing the window returns the terminal to a prompt.

To (re)create the database only, without opening the GUI:

```bash
python3 database.py
```

---

## 4. Database Design (ER)

Three tables, linked by foreign keys:

```
 books                         members                    transactions
 ----------------------        --------------------       --------------------------
 book_id (PK)                  member_id (PK)             txn_id (PK)
 title                         name                       book_id    (FK -> books)
 author                        email                      member_id  (FK -> members)
 isbn (unique)                 phone                      issue_date
 total_copies                  join_date                  due_date
 available                                                return_date
                                                          status (ISSUED / RETURNED)
```

**Relationships**

- One **book** can appear in many **transactions** (one-to-many).
- One **member** can appear in many **transactions** (one-to-many).
- `available` tracks how many copies of a book are free to lend; it goes **down** on issue
  and **up** on return, and never exceeds `total_copies`.

---

## 5. GUI Forms (Activity 2)

The window has a **dashboard strip** on top (live counts of titles, copies, members, issued,
and overdue books) and a **tabbed form layout**:

1. **Books** — form to add / update / delete a book, a live search box, and a table of the
   catalogue showing total vs available copies.
2. **Members** — form to add / update / delete members, with search and a member table.
3. **Issue / Return** — pick a book and a member to **issue**; the lower table lists all
   books currently on loan, and a button **returns** the selected one.
4. **Reports** — a dropdown selects one of three reports, displayed in a table:
   - **All Transactions** — full issue/return history.
   - **Overdue Books** — issued books whose due date has passed.
   - **Stock Summary** — per-title inventory (total / available / on loan).

> For the lab record, take a screenshot of each tab and attach it next to the code, as the
> assignment asks for snapshots of all forms.

---

## 6. Event Handling & Logic (Activity 3)

Tkinter is **event-driven**: each button is bound to a handler function that runs when
clicked. The handlers validate input, call a function in `database.py`, then refresh the
on-screen tables. The interesting business logic:

**Issue a book — algorithm**

```
1. Read the selected book and member.
2. If the book's available count <= 0  -> show error, stop.
3. Insert a transaction:
       issue_date = today
       due_date   = today + 14 days
       status     = 'ISSUED'
4. Decrement books.available by 1.
```

**Return a book — algorithm**

```
1. Read the selected (ISSUED) transaction.
2. If already RETURNED -> show error, stop.
3. Set return_date = today, status = 'RETURNED'.
4. Increment books.available by 1.
```

**Overdue report — algorithm**

```
Select every transaction where status = 'ISSUED'
                          and due_date < today.
```

Safety rules enforced in `database.py`:

- A book cannot be deleted while copies are still issued.
- A member cannot be deleted while they still hold an issued book.
- Editing a book's copy count keeps copies currently on loan accounted for.

---

## 7. File Structure

```
Library-MS-Python/
├── library_management.py   # GUI front-end (Tkinter) + event handlers
├── database.py             # Database layer (SQLite, all SQL lives here)
├── library.db              # Auto-created on first run (git-ignored)
├── .gitignore              # Excludes the generated db and caches
└── README.md               # This document
```

The clean split — **GUI in one file, all SQL in another** — makes the code easy to read and
to explain in the viva: the GUI never writes SQL, it only calls named functions like
`db.issue_book(...)` or `db.report_overdue()`.

---

## 8. Sample Walkthrough (for the viva)

1. Open the app — note the dashboard counts.
2. **Books tab** → add a new book → it appears in the table and the dashboard count rises.
3. **Members tab** → add a member.
4. **Issue / Return tab** → issue that book to the member → the book's *available* count
   drops by one and the loan shows in the table.
5. **Reports tab** → *All Transactions* shows the ISSUED row; *Stock Summary* reflects the
   reduced availability.
6. Back on **Issue / Return** → select the loan → *Return* → availability is restored and
   *All Transactions* now shows it as RETURNED.
```
