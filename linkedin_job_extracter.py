import json
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox

from extract import extract_jobs_from_data


class LinkedInExtractorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("LinkedIn Job JSON Extractor")
        self.root.geometry("1200x760")

        self.rows = []
        self.display_rows = []
        self.sort_column = None
        self.sort_desc = False

        self._build_ui()

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        input_frame = ttk.LabelFrame(main, text="Input LinkedIn JSON")
        input_frame.pack(fill=tk.BOTH, expand=False)

        self.json_text = tk.Text(input_frame, height=14, wrap=tk.WORD)
        self.json_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        controls = ttk.Frame(main)
        controls.pack(fill=tk.X, pady=(8, 8))

        self.extract_btn = ttk.Button(controls, text="Extract", command=self.on_extract)
        self.extract_btn.pack(side=tk.LEFT)

        ttk.Button(controls, text="Clear", command=self.on_clear).pack(side=tk.LEFT, padx=(8, 0))

        self.status_var = tk.StringVar(
            value="Paste LinkedIn JSON and click Extract. Extract again to append new jobs (duplicates skipped)."
        )
        ttk.Label(controls, textvariable=self.status_var).pack(side=tk.LEFT, padx=(12, 0))

        filters = ttk.LabelFrame(main, text="Filters")
        filters.pack(fill=tk.X, expand=False, pady=(0, 8))

        ttk.Label(filters, text="Apply Type (multi-select)").grid(row=0, column=0, padx=(8, 4), pady=(8, 0), sticky="nw")
        self.apply_type_list = tk.Listbox(
            filters,
            height=5,
            selectmode=tk.EXTENDED,
            exportselection=False,
        )
        self.apply_type_list.grid(row=1, column=0, padx=(8, 4), pady=(0, 8), sticky="nw")

        ttk.Label(filters, text="Job Type (multi-select)").grid(row=0, column=1, padx=(8, 4), pady=(8, 0), sticky="nw")
        self.job_type_list = tk.Listbox(
            filters,
            height=5,
            selectmode=tk.EXTENDED,
            exportselection=False,
        )
        self.job_type_list.grid(row=1, column=1, padx=(8, 4), pady=(0, 8), sticky="nw")

        ttk.Label(filters, text="Reposted (multi-select)").grid(row=0, column=2, padx=(8, 4), pady=(8, 0), sticky="nw")
        self.reposted_list = tk.Listbox(
            filters,
            height=5,
            selectmode=tk.EXTENDED,
            exportselection=False,
        )
        self.reposted_list.grid(row=1, column=2, padx=(8, 4), pady=(0, 8), sticky="nw")

        ttk.Label(filters, text="Applied (multi-select)").grid(row=0, column=3, padx=(8, 4), pady=(8, 0), sticky="nw")
        self.applied_list = tk.Listbox(
            filters,
            height=5,
            selectmode=tk.EXTENDED,
            exportselection=False,
        )
        self.applied_list.grid(row=1, column=3, padx=(8, 4), pady=(0, 8), sticky="nw")

        ttk.Button(filters, text="Apply Filters", command=self.apply_filters).grid(
            row=1, column=4, padx=(12, 4), pady=(0, 8), sticky="nw"
        )
        ttk.Button(filters, text="Reset", command=self.reset_filters).grid(
            row=1, column=5, padx=(0, 8), pady=(0, 8), sticky="nw"
        )

        output_frame = ttk.LabelFrame(main, text="Extracted Jobs")
        output_frame.pack(fill=tk.BOTH, expand=True)

        table_wrap = ttk.Frame(output_frame)
        table_wrap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 4), pady=8)
        table_wrap.grid_rowconfigure(0, weight=1)
        table_wrap.grid_columnconfigure(0, weight=1)

        self.table_columns = (
            "posted",
            "job_title",
            "company",
            "location",
            "job_type",
            "apply_type",
            "applicant_tracking_system",
            "reposted",
            "applied",
            "applied_at",
            "apply_url",
        )
        self.jobs_table = ttk.Treeview(
            table_wrap,
            columns=self.table_columns,
            show="headings",
            height=20,
        )
        self.jobs_table.grid(row=0, column=0, sticky="nsew")
        self.jobs_table.bind("<<TreeviewSelect>>", self.on_select_job)
        self.jobs_table.bind("<Double-1>", self.on_double_click_open_apply_url)

        self.jobs_table.heading("posted", text="Posted", command=lambda: self.sort_by_column("posted"))
        self.jobs_table.heading("job_title", text="Job Title", command=lambda: self.sort_by_column("job_title"))
        self.jobs_table.heading("company", text="Company", command=lambda: self.sort_by_column("company"))
        self.jobs_table.heading("location", text="Location", command=lambda: self.sort_by_column("location"))
        self.jobs_table.heading("job_type", text="Job Type", command=lambda: self.sort_by_column("job_type"))
        self.jobs_table.heading("apply_type", text="Apply Type", command=lambda: self.sort_by_column("apply_type"))
        self.jobs_table.heading(
            "applicant_tracking_system",
            text="Applicant Tracking System",
            command=lambda: self.sort_by_column("applicant_tracking_system"),
        )
        self.jobs_table.heading("reposted", text="Reposted", command=lambda: self.sort_by_column("reposted"))
        self.jobs_table.heading("applied", text="Applied", command=lambda: self.sort_by_column("applied"))
        self.jobs_table.heading("applied_at", text="Applied At", command=lambda: self.sort_by_column("applied_at"))
        self.jobs_table.heading("apply_url", text="Apply URL", command=lambda: self.sort_by_column("apply_url"))

        self.jobs_table.column("posted", width=150, anchor=tk.W, stretch=False)
        self.jobs_table.column("job_title", width=220, anchor=tk.W)
        self.jobs_table.column("company", width=180, anchor=tk.W)
        self.jobs_table.column("location", width=180, anchor=tk.W)
        self.jobs_table.column("job_type", width=100, anchor=tk.CENTER, stretch=False)
        self.jobs_table.column("apply_type", width=110, anchor=tk.CENTER, stretch=False)
        self.jobs_table.column("applicant_tracking_system", width=170, anchor=tk.W)
        self.jobs_table.column("reposted", width=80, anchor=tk.CENTER, stretch=False)
        self.jobs_table.column("applied", width=80, anchor=tk.CENTER, stretch=False)
        self.jobs_table.column("applied_at", width=130, anchor=tk.W, stretch=False)
        self.jobs_table.column("apply_url", width=260, anchor=tk.W)

        # Row color coding by job type for quick scanning.
        self.jobs_table.tag_configure("remote", background="#e9f7ef")
        self.jobs_table.tag_configure("hybrid", background="#eaf2ff")
        self.jobs_table.tag_configure("onsite", background="#fff3e6")

        table_scroll_y = ttk.Scrollbar(table_wrap, orient=tk.VERTICAL, command=self.jobs_table.yview)
        table_scroll_y.grid(row=0, column=1, sticky="ns")
        table_scroll_x = ttk.Scrollbar(table_wrap, orient=tk.HORIZONTAL, command=self.jobs_table.xview)
        table_scroll_x.grid(row=1, column=0, sticky="ew")
        self.jobs_table.configure(yscrollcommand=table_scroll_y.set, xscrollcommand=table_scroll_x.set)

        table_actions = ttk.Frame(table_wrap)
        table_actions.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        ttk.Button(
            table_actions,
            text="Open visible apply URLs & remove those rows",
            command=self.on_open_visible_urls_and_remove,
        ).pack(side=tk.LEFT)

        details_wrap = ttk.Frame(output_frame)
        details_wrap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 8), pady=8)

        self.details_text = tk.Text(details_wrap, wrap=tk.WORD)
        self.details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        details_scroll = ttk.Scrollbar(details_wrap, orient=tk.VERTICAL, command=self.details_text.yview)
        details_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.details_text.config(yscrollcommand=details_scroll.set)

    def on_clear(self):
        self.json_text.delete("1.0", tk.END)
        self.jobs_table.delete(*self.jobs_table.get_children())
        self.details_text.delete("1.0", tk.END)
        self.rows = []
        self.display_rows = []
        self.sort_column = None
        self.sort_desc = False
        self.reset_filters()
        self.status_var.set("Cleared.")

    def on_extract(self):
        raw = self.json_text.get("1.0", tk.END).strip()
        if not raw:
            messagebox.showwarning("Missing Input", "Please paste LinkedIn JSON first.")
            return

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            messagebox.showerror("Invalid JSON", f"JSON parse error:\n{exc}")
            return

        try:
            new_rows = extract_jobs_from_data(payload)
        except Exception as exc:
            messagebox.showerror("Extraction Error", f"Failed to extract jobs:\n{exc}")
            return

        if not new_rows:
            if not self.rows:
                self.rows = []
                self.display_rows = []
                self.sort_column = None
                self.sort_desc = False
                self._populate_table([])
                self.status_var.set(
                    "Extracted 0 jobs. This JSON may be a feed payload without any job cards/postings."
                )
                messagebox.showinfo(
                    "No Jobs Found",
                    "No job postings were detected in this JSON.\n"
                    "Use a LinkedIn Jobs search payload (or a feed payload that contains job cards).",
                )
            else:
                kept = len(self.rows)
                self.status_var.set(
                    f"No jobs in this payload; kept {kept} job(s) already in the list."
                )
                messagebox.showinfo(
                    "No Jobs Found",
                    "No job postings were detected in this JSON.\n"
                    "Your existing list was not changed.",
                )
            return

        if self.rows:
            self.rows, added, skipped = self._merge_job_rows(self.rows, new_rows)
            total = len(self.rows)
            if added == 0:
                self.status_var.set(
                    f"No new jobs added ({skipped} duplicate(s) already in list). Total {total}."
                )
            elif skipped == 0:
                self.status_var.set(f"Added {added} new job(s). Total {total}.")
            else:
                self.status_var.set(
                    f"Added {added} new job(s); skipped {skipped} duplicate(s). Total {total}."
                )
        else:
            self.rows = new_rows
            self.status_var.set(
                f"Extracted {len(self.rows)} jobs. Extract again to merge another payload (duplicates skipped)."
            )

        self.sort_column = None
        self.sort_desc = False
        self._update_filter_options(self.rows)
        self.apply_filters(update_status=False)

        first_iid = "0"
        self.jobs_table.selection_set(first_iid)
        self.jobs_table.focus(first_iid)
        self.on_select_job(None)

    def _populate_table(self, rows):
        self.jobs_table.delete(*self.jobs_table.get_children())
        self.details_text.delete("1.0", tk.END)

        for i, row in enumerate(rows, start=1):
            title = row.get("job_title") or "N/A"
            company = row.get("company") or "N/A"
            location = row.get("location") or "N/A"
            job_type = self._job_type_label(row.get("job_type"))
            posted = row.get("posted_on_text") or str(row.get("posted_at") or "N/A")
            apply_type = row.get("apply_type") or "N/A"
            applicant_tracking_system = row.get("applicant_tracking_system") or "N/A"
            reposted = row.get("reposted")
            applied = row.get("applied")
            applied_at = row.get("applied_at")
            apply_url = row.get("apply_url") or "N/A"

            reposted_text = "True" if reposted is True else "False" if reposted is False else "N/A"
            applied_text = "True" if applied is True else "False" if applied is False else "N/A"
            applied_at_text = str(applied_at) if applied_at is not None else "N/A"

            raw_job_type = str(row.get("job_type") or "").lower()
            row_tag = raw_job_type if raw_job_type in {"remote", "hybrid", "onsite"} else ""
            self.jobs_table.insert(
                "",
                tk.END,
                iid=str(i - 1),
                values=(
                    posted,
                    title,
                    company,
                    location,
                    job_type,
                    apply_type,
                    applicant_tracking_system,
                    reposted_text,
                    applied_text,
                    applied_at_text,
                    apply_url,
                ),
                tags=(row_tag,) if row_tag else (),
            )

    def _sort_value(self, row, column):
        if column == "posted":
            posted_at = row.get("posted_at")
            if posted_at is not None:
                return (0, posted_at)
            return (1, str(row.get("posted_on_text") or "").lower())
        if column == "reposted":
            value = row.get("reposted")
            if value is None:
                return (2, 0)
            return (0, 1 if value else 0)
        if column == "applied":
            value = row.get("applied")
            if value is None:
                return (2, 0)
            return (0, 1 if value else 0)
        if column == "applied_at":
            value = row.get("applied_at")
            if value is None:
                return (1, 0)
            return (0, value)
        if column == "job_type":
            return self._job_type_label(row.get("job_type")).lower()
        return str(row.get(column) or "").lower()

    def _job_type_label(self, value):
        text = str(value or "").strip().lower()
        if not text or text == "unknown":
            return "N/A"
        return text

    def _job_row_dedupe_key(self, row):
        posting_urn = (row.get("job_posting_urn") or "").strip()
        if posting_urn:
            return ("job_posting_urn", posting_urn)
        card_urn = (row.get("job_posting_card_urn") or "").strip()
        if card_urn:
            return ("job_posting_card_urn", card_urn)
        feed_update = (row.get("feed_update_urn") or "").strip()
        if feed_update:
            return ("feed_update_urn", feed_update)
        job_id = str(row.get("job_id") or "").strip()
        if job_id and not job_id.startswith("feed_job_"):
            return ("job_id", job_id)
        url = (row.get("apply_url") or "").strip().lower()
        if url.startswith(("http://", "https://")):
            return ("apply_url", url)
        tracking = (row.get("tracking_urn") or "").strip()
        if tracking:
            return ("tracking_urn", tracking)
        title = (row.get("job_title") or "").strip().lower()
        company = (row.get("company") or "").strip().lower()
        return ("weak", job_id, title, company, url)

    def _merge_job_rows(self, existing, incoming):
        keys = {self._job_row_dedupe_key(r) for r in existing}
        merged = list(existing)
        added = 0
        skipped = 0
        for row in incoming:
            key = self._job_row_dedupe_key(row)
            if key in keys:
                skipped += 1
                continue
            keys.add(key)
            merged.append(row)
            added += 1
        return merged, added, skipped

    def _update_filter_options(self, rows):
        apply_types = sorted({str(row.get("apply_type") or "N/A") for row in rows}, key=str.lower)
        job_types = sorted({self._job_type_label(row.get("job_type")) for row in rows}, key=str.lower)

        self._fill_listbox(self.apply_type_list, apply_types)
        self._fill_listbox(self.job_type_list, job_types)

        self._fill_listbox(self.reposted_list, ["True", "False", "N/A"])
        self._fill_listbox(self.applied_list, ["True", "False", "N/A"])

        self._select_all_listbox(self.apply_type_list)
        self._select_all_listbox(self.job_type_list)
        self._select_all_listbox(self.reposted_list)
        self._select_all_listbox(self.applied_list)

    def _fill_listbox(self, listbox, values):
        listbox.delete(0, tk.END)
        for value in values:
            listbox.insert(tk.END, value)

    def _select_all_listbox(self, listbox):
        if listbox.size() == 0:
            return
        listbox.selection_set(0, tk.END)

    def _listbox_selected_values(self, listbox):
        return [listbox.get(i) for i in listbox.curselection()]

    def _bool_label(self, value):
        if value is True:
            return "True"
        if value is False:
            return "False"
        return "N/A"

    def _row_matches_filters(self, row):
        apply_types_selected = self._listbox_selected_values(self.apply_type_list)
        if apply_types_selected:
            row_apply_type = str(row.get("apply_type") or "N/A")
            if row_apply_type not in apply_types_selected:
                return False

        reposted_selected = self._listbox_selected_values(self.reposted_list)
        if reposted_selected:
            if self._bool_label(row.get("reposted")) not in reposted_selected:
                return False

        applied_selected = self._listbox_selected_values(self.applied_list)
        if applied_selected:
            if self._bool_label(row.get("applied")) not in applied_selected:
                return False

        job_types_selected = self._listbox_selected_values(self.job_type_list)
        if job_types_selected:
            row_job_type = self._job_type_label(row.get("job_type"))
            if row_job_type not in job_types_selected:
                return False

        return True

    def apply_filters(self, update_status=True):
        if not self.rows:
            self.display_rows = []
            self._populate_table(self.display_rows)
            if update_status:
                self.status_var.set("No extracted rows to filter.")
            return

        self.display_rows = [row for row in self.rows if self._row_matches_filters(row)]

        if self.sort_column:
            self.display_rows = sorted(
                self.display_rows,
                key=lambda row: self._sort_value(row, self.sort_column),
                reverse=self.sort_desc,
            )

        self._populate_table(self.display_rows)

        if self.display_rows:
            first_iid = "0"
            self.jobs_table.selection_set(first_iid)
            self.jobs_table.focus(first_iid)
            self.on_select_job(None)

        if update_status:
            self.status_var.set(f"Showing {len(self.display_rows)} of {len(self.rows)} jobs after filters.")

    def reset_filters(self):
        self._select_all_listbox(self.apply_type_list)
        self._select_all_listbox(self.job_type_list)
        self._select_all_listbox(self.reposted_list)
        self._select_all_listbox(self.applied_list)

        if self.rows:
            self.apply_filters(update_status=True)

    def sort_by_column(self, column):
        if not self.rows:
            return

        if self.sort_column == column:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_column = column
            self.sort_desc = False

        self.display_rows = sorted(
            self.display_rows,
            key=lambda row: self._sort_value(row, column),
            reverse=self.sort_desc,
        )
        self._populate_table(self.display_rows)

        if self.display_rows:
            first_iid = "0"
            self.jobs_table.selection_set(first_iid)
            self.jobs_table.focus(first_iid)
            self.on_select_job(None)

        direction = "descending" if self.sort_desc else "ascending"
        self.status_var.set(f"Sorted by {column} ({direction}).")

    def on_select_job(self, _event):
        selected = self.jobs_table.selection()
        if not selected:
            return

        idx = self.jobs_table.index(selected[0])
        if idx >= len(self.display_rows):
            return

        row = self.display_rows[idx]
        pretty = json.dumps(row, indent=2, ensure_ascii=False)
        self.details_text.delete("1.0", tk.END)
        self.details_text.insert(tk.END, pretty)

    def _http_apply_url_from_row(self, row):
        url = (row.get("apply_url") or "").strip()
        if not url or url.upper() == "N/A":
            return None
        lower = url.lower()
        if lower.startswith("http://") or lower.startswith("https://"):
            return url
        return None

    def on_double_click_open_apply_url(self, event):
        item = self.jobs_table.identify_row(event.y)
        if not item:
            return

        try:
            idx = self.jobs_table.index(item)
        except tk.TclError:
            return

        if idx < 0 or idx >= len(self.display_rows):
            return

        row = self.display_rows[idx]
        url = self._http_apply_url_from_row(row)
        if not url:
            raw = (row.get("apply_url") or "").strip()
            if not raw or raw.upper() == "N/A":
                messagebox.showinfo("No apply URL", "This row has no apply URL to open.")
            else:
                messagebox.showwarning("Invalid URL", f"Apply URL is not a web link:\n{raw}")
            return

        webbrowser.open(url, new=0, autoraise=True)

    def on_open_visible_urls_and_remove(self):
        visible = list(self.display_rows)
        if not visible:
            messagebox.showinfo("No rows", "The table has no jobs in the current view (check filters).")
            return

        openable = sum(1 for row in visible if self._http_apply_url_from_row(row) is not None)
        n = len(visible)
        if not messagebox.askyesno(
            "Open URLs and remove rows",
            f"This will open {openable} browser tab(s) for http(s) apply links among the "
            f"{n} visible row(s), then remove all {n} of those rows from the list "
            f"(including rows without a valid link).\n\nContinue?",
        ):
            return

        for row in visible:
            url = self._http_apply_url_from_row(row)
            if url:
                webbrowser.open(url, new=0, autoraise=True)

        remove_ids = {id(row) for row in visible}
        self.rows = [row for row in self.rows if id(row) not in remove_ids]

        self.sort_column = None
        self.sort_desc = False
        self._update_filter_options(self.rows)
        self.apply_filters(update_status=False)

        remaining = len(self.rows)
        shown = len(self.display_rows)
        if remaining == 0:
            self.status_var.set(f"Removed {n} row(s); list is empty.")
        else:
            self.status_var.set(
                f"Removed {n} row(s) ({openable} URL(s) opened). {shown} of {remaining} jobs in current filter view."
            )


def main():
    root = tk.Tk()
    app = LinkedInExtractorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
