"""
library_management.py
---------------------
Library Management System  -  GUI front-end (Activity 2 & 3)

A simple desktop application built with Tkinter (Python's built-in GUI
toolkit) on top of an SQLite database (see database.py).

Run it with:

    python library_management.py

The window is organised as a dashboard strip on top and four tabs:

    1. Books         -  add / edit / delete / search the catalogue
    2. Members       -  add / edit / delete / search library members
    3. Issue / Return-  lend a book to a member and take it back
    4. Reports       -  all transactions, overdue list, stock summary

Tkinter is event-driven: widgets (buttons, etc.) are bound to handler
functions that run when the user interacts with them. Each handler calls
into database.py, then refreshes the on-screen tables.
"""

import tkinter as tk
from tkinter import ttk, messagebox

import database as db


class LibraryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Library Management System")
        self.geometry("980x640")
        self.minsize(880, 560)

        # Make sure the database and tables exist before anything is drawn.
        db.init_db()

        self._build_dashboard()
        self._build_tabs()
        self.refresh_all()

    # ------------------------------------------------------------------ #
    #  Dashboard (headline stats across the top)
    # ------------------------------------------------------------------ #
    def _build_dashboard(self):
        bar = tk.Frame(self, bg="#1f3a5f", height=70)
        bar.pack(side="top", fill="x")

        tk.Label(
            bar, text="📚  Library Management System",
            bg="#1f3a5f", fg="white", font=("Segoe UI", 16, "bold"),
        ).pack(side="left", padx=20)

        self.stats_label = tk.Label(
            bar, text="", bg="#1f3a5f", fg="#dfe7f2", font=("Segoe UI", 10),
            justify="right",
        )
        self.stats_label.pack(side="right", padx=20)

    def refresh_dashboard(self):
        s = db.dashboard_stats()
        self.stats_label.config(
            text=(
                f"Titles: {s['titles']}    Copies: {s['total_books']}    "
                f"Members: {s['members']}    Issued: {s['issued']}    "
                f"Overdue: {s['overdue']}"
            )
        )

    # ------------------------------------------------------------------ #
    #  Tabs
    # ------------------------------------------------------------------ #
    def _build_tabs(self):
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=10)

        self.books_tab = BooksTab(self.tabs, self)
        self.members_tab = MembersTab(self.tabs, self)
        self.issue_tab = IssueReturnTab(self.tabs, self)
        self.reports_tab = ReportsTab(self.tabs, self)

        self.tabs.add(self.books_tab, text="  Books  ")
        self.tabs.add(self.members_tab, text="  Members  ")
        self.tabs.add(self.issue_tab, text="  Issue / Return  ")
        self.tabs.add(self.reports_tab, text="  Reports  ")

        # Refresh data whenever the user switches tabs.
        self.tabs.bind("<<NotebookTabChanged>>", lambda e: self.refresh_all())

    def refresh_all(self):
        self.refresh_dashboard()
        self.books_tab.refresh()
        self.members_tab.refresh()
        self.issue_tab.refresh()
        self.reports_tab.refresh()


# ====================================================================== #
#  BOOKS TAB
# ====================================================================== #
class BooksTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.selected_id = None

        # ---- Form (left) ------------------------------------------------
        form = ttk.LabelFrame(self, text="Book Details")
        form.pack(side="left", fill="y", padx=10, pady=10)

        self.title_var = tk.StringVar()
        self.author_var = tk.StringVar()
        self.isbn_var = tk.StringVar()
        self.copies_var = tk.StringVar(value="1")

        self._field(form, "Title", self.title_var, 0)
        self._field(form, "Author", self.author_var, 1)
        self._field(form, "ISBN", self.isbn_var, 2)
        self._field(form, "Copies", self.copies_var, 3)

        btns = ttk.Frame(form)
        btns.grid(row=4, column=0, columnspan=2, pady=12)
        ttk.Button(btns, text="Add", command=self.add).grid(row=0, column=0, padx=3)
        ttk.Button(btns, text="Update", command=self.update).grid(row=0, column=1, padx=3)
        ttk.Button(btns, text="Delete", command=self.delete).grid(row=0, column=2, padx=3)
        ttk.Button(btns, text="Clear", command=self.clear).grid(row=0, column=3, padx=3)

        # ---- Table (right) ---------------------------------------------
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        search_row = ttk.Frame(right)
        search_row.pack(fill="x")
        ttk.Label(search_row, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        entry = ttk.Entry(search_row, textvariable=self.search_var)
        entry.pack(side="left", fill="x", expand=True, padx=6)
        entry.bind("<KeyRelease>", lambda e: self.refresh())

        cols = ("id", "title", "author", "isbn", "total", "available")
        self.tree = ttk.Treeview(right, columns=cols, show="headings", height=18)
        headings = ["ID", "Title", "Author", "ISBN", "Total", "Available"]
        widths = [40, 220, 160, 130, 60, 80]
        for c, h, w in zip(cols, headings, widths):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, pady=8)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

    def _field(self, parent, label, var, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(parent, textvariable=var, width=26).grid(row=row, column=1, padx=8, pady=6)

    # ---- event handlers -------------------------------------------------
    def add(self):
        if not self._validate():
            return
        try:
            db.add_book(
                self.title_var.get().strip(),
                self.author_var.get().strip(),
                self.isbn_var.get().strip(),
                int(self.copies_var.get()),
            )
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        self.clear()
        self.app.refresh_all()

    def update(self):
        if self.selected_id is None:
            messagebox.showinfo("Select a book", "Please select a book from the list first.")
            return
        if not self._validate():
            return
        db.update_book(
            self.selected_id,
            self.title_var.get().strip(),
            self.author_var.get().strip(),
            self.isbn_var.get().strip(),
            int(self.copies_var.get()),
        )
        self.clear()
        self.app.refresh_all()

    def delete(self):
        if self.selected_id is None:
            messagebox.showinfo("Select a book", "Please select a book from the list first.")
            return
        if not messagebox.askyesno("Confirm", "Delete the selected book?"):
            return
        try:
            db.delete_book(self.selected_id)
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return
        self.clear()
        self.app.refresh_all()

    def clear(self):
        self.selected_id = None
        self.title_var.set("")
        self.author_var.set("")
        self.isbn_var.set("")
        self.copies_var.set("1")
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())

    def on_select(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        self.selected_id = int(vals[0])
        self.title_var.set(vals[1])
        self.author_var.set(vals[2])
        self.isbn_var.set(vals[3])
        self.copies_var.set(vals[4])

    def _validate(self):
        if not self.title_var.get().strip() or not self.author_var.get().strip():
            messagebox.showwarning("Missing data", "Title and Author are required.")
            return False
        try:
            if int(self.copies_var.get()) < 1:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid data", "Copies must be a positive whole number.")
            return False
        return True

    def refresh(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        for b in db.get_books(self.search_var.get().strip()):
            self.tree.insert(
                "", "end",
                values=(b["book_id"], b["title"], b["author"], b["isbn"],
                        b["total_copies"], b["available"]),
            )


# ====================================================================== #
#  MEMBERS TAB
# ====================================================================== #
class MembersTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.selected_id = None

        form = ttk.LabelFrame(self, text="Member Details")
        form.pack(side="left", fill="y", padx=10, pady=10)

        self.name_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.phone_var = tk.StringVar()

        self._field(form, "Name", self.name_var, 0)
        self._field(form, "Email", self.email_var, 1)
        self._field(form, "Phone", self.phone_var, 2)

        btns = ttk.Frame(form)
        btns.grid(row=3, column=0, columnspan=2, pady=12)
        ttk.Button(btns, text="Add", command=self.add).grid(row=0, column=0, padx=3)
        ttk.Button(btns, text="Update", command=self.update).grid(row=0, column=1, padx=3)
        ttk.Button(btns, text="Delete", command=self.delete).grid(row=0, column=2, padx=3)
        ttk.Button(btns, text="Clear", command=self.clear).grid(row=0, column=3, padx=3)

        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        search_row = ttk.Frame(right)
        search_row.pack(fill="x")
        ttk.Label(search_row, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        entry = ttk.Entry(search_row, textvariable=self.search_var)
        entry.pack(side="left", fill="x", expand=True, padx=6)
        entry.bind("<KeyRelease>", lambda e: self.refresh())

        cols = ("id", "name", "email", "phone", "joined")
        self.tree = ttk.Treeview(right, columns=cols, show="headings", height=18)
        headings = ["ID", "Name", "Email", "Phone", "Joined"]
        widths = [40, 180, 200, 130, 110]
        for c, h, w in zip(cols, headings, widths):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, pady=8)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

    def _field(self, parent, label, var, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(parent, textvariable=var, width=26).grid(row=row, column=1, padx=8, pady=6)

    def add(self):
        if not self.name_var.get().strip():
            messagebox.showwarning("Missing data", "Name is required.")
            return
        db.add_member(
            self.name_var.get().strip(),
            self.email_var.get().strip(),
            self.phone_var.get().strip(),
        )
        self.clear()
        self.app.refresh_all()

    def update(self):
        if self.selected_id is None:
            messagebox.showinfo("Select a member", "Please select a member from the list first.")
            return
        if not self.name_var.get().strip():
            messagebox.showwarning("Missing data", "Name is required.")
            return
        db.update_member(
            self.selected_id,
            self.name_var.get().strip(),
            self.email_var.get().strip(),
            self.phone_var.get().strip(),
        )
        self.clear()
        self.app.refresh_all()

    def delete(self):
        if self.selected_id is None:
            messagebox.showinfo("Select a member", "Please select a member from the list first.")
            return
        if not messagebox.askyesno("Confirm", "Delete the selected member?"):
            return
        try:
            db.delete_member(self.selected_id)
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return
        self.clear()
        self.app.refresh_all()

    def clear(self):
        self.selected_id = None
        self.name_var.set("")
        self.email_var.set("")
        self.phone_var.set("")
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())

    def on_select(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        self.selected_id = int(vals[0])
        self.name_var.set(vals[1])
        self.email_var.set(vals[2])
        self.phone_var.set(vals[3])

    def refresh(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        for m in db.get_members(self.search_var.get().strip()):
            self.tree.insert(
                "", "end",
                values=(m["member_id"], m["name"], m["email"], m["phone"], m["join_date"]),
            )


# ====================================================================== #
#  ISSUE / RETURN TAB
# ====================================================================== #
class IssueReturnTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        # ---- Issue panel -----------------------------------------------
        issue = ttk.LabelFrame(self, text="Issue a Book")
        issue.pack(fill="x", padx=10, pady=10)

        ttk.Label(issue, text="Book").grid(row=0, column=0, padx=8, pady=8, sticky="w")
        self.book_combo = ttk.Combobox(issue, state="readonly", width=45)
        self.book_combo.grid(row=0, column=1, padx=8, pady=8)

        ttk.Label(issue, text="Member").grid(row=0, column=2, padx=8, pady=8, sticky="w")
        self.member_combo = ttk.Combobox(issue, state="readonly", width=30)
        self.member_combo.grid(row=0, column=3, padx=8, pady=8)

        ttk.Button(issue, text="Issue Book", command=self.issue).grid(
            row=0, column=4, padx=12, pady=8
        )

        # ---- Currently issued table + Return ---------------------------
        ret = ttk.LabelFrame(self, text="Currently Issued  (select a row, then Return)")
        ret.pack(fill="both", expand=True, padx=10, pady=10)

        cols = ("txn", "title", "member", "issued", "due")
        self.tree = ttk.Treeview(ret, columns=cols, show="headings", height=14)
        headings = ["Txn", "Book", "Member", "Issued On", "Due On"]
        widths = [50, 260, 180, 120, 120]
        for c, h, w in zip(cols, headings, widths):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)

        ttk.Button(ret, text="Return Selected Book", command=self.do_return).pack(
            pady=6
        )

        # Maps shown in the combo boxes -> database ids.
        self._book_ids = {}
        self._member_ids = {}

    def issue(self):
        book_label = self.book_combo.get()
        member_label = self.member_combo.get()
        if not book_label or not member_label:
            messagebox.showwarning("Select both", "Pick a book and a member first.")
            return
        try:
            db.issue_book(self._book_ids[book_label], self._member_ids[member_label])
        except ValueError as e:
            messagebox.showerror("Cannot issue", str(e))
            return
        messagebox.showinfo("Issued", "Book issued successfully.")
        self.app.refresh_all()

    def do_return(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select a loan", "Please select an issued book first.")
            return
        txn_id = int(self.tree.item(sel[0], "values")[0])
        try:
            db.return_book(txn_id)
        except ValueError as e:
            messagebox.showerror("Cannot return", str(e))
            return
        messagebox.showinfo("Returned", "Book returned successfully.")
        self.app.refresh_all()

    def refresh(self):
        # Refill the book combo (only books with available copies).
        self._book_ids.clear()
        book_labels = []
        for b in db.get_books():
            if b["available"] > 0:
                label = f'{b["title"]}  (avail: {b["available"]})'
                self._book_ids[label] = b["book_id"]
                book_labels.append(label)
        self.book_combo["values"] = book_labels
        if book_labels and self.book_combo.get() not in book_labels:
            self.book_combo.set("")

        # Refill the member combo.
        self._member_ids.clear()
        member_labels = []
        for m in db.get_members():
            label = f'{m["name"]}  (#{m["member_id"]})'
            self._member_ids[label] = m["member_id"]
            member_labels.append(label)
        self.member_combo["values"] = member_labels
        if member_labels and self.member_combo.get() not in member_labels:
            self.member_combo.set("")

        # Refill the issued-books table.
        for r in self.tree.get_children():
            self.tree.delete(r)
        for t in db.get_issued_transactions():
            self.tree.insert(
                "", "end",
                values=(t["txn_id"], t["title"], t["member"], t["issue_date"], t["due_date"]),
            )


# ====================================================================== #
#  REPORTS TAB
# ====================================================================== #
class ReportsTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=10)
        ttk.Label(top, text="Report:").pack(side="left")

        self.report_var = tk.StringVar(value="All Transactions")
        self.report_combo = ttk.Combobox(
            top, state="readonly", textvariable=self.report_var, width=28,
            values=["All Transactions", "Overdue Books", "Stock Summary"],
        )
        self.report_combo.pack(side="left", padx=8)
        self.report_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        ttk.Button(top, text="Refresh", command=self.refresh).pack(side="left", padx=4)

        self.tree = ttk.Treeview(self, show="headings", height=20)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

    def _set_columns(self, columns, widths):
        self.tree["columns"] = columns
        for c, w in zip(columns, widths):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor="w")
        for r in self.tree.get_children():
            self.tree.delete(r)

    def refresh(self):
        choice = self.report_var.get()

        if choice == "All Transactions":
            self._set_columns(
                ["Txn", "Book", "Member", "Issued", "Due", "Returned", "Status"],
                [50, 220, 150, 100, 100, 100, 90],
            )
            for t in db.report_all_transactions():
                self.tree.insert(
                    "", "end",
                    values=(t["txn_id"], t["title"], t["member"], t["issue_date"],
                            t["due_date"], t["return_date"] or "-", t["status"]),
                )

        elif choice == "Overdue Books":
            self._set_columns(
                ["Txn", "Book", "Member", "Issued", "Due"],
                [50, 260, 180, 120, 120],
            )
            rows = db.report_overdue()
            for t in rows:
                self.tree.insert(
                    "", "end",
                    values=(t["txn_id"], t["title"], t["member"], t["issue_date"], t["due_date"]),
                )
            if not rows:
                self.tree.insert("", "end", values=("", "No overdue books 🎉", "", "", ""))

        else:  # Stock Summary
            self._set_columns(
                ["Title", "Author", "Total", "Available", "On Loan"],
                [260, 200, 80, 90, 90],
            )
            for b in db.report_stock():
                self.tree.insert(
                    "", "end",
                    values=(b["title"], b["author"], b["total_copies"],
                            b["available"], b["on_loan"]),
                )


if __name__ == "__main__":
    app = LibraryApp()
    app.mainloop()
