# ===== worker/setup_wizard.py =====

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox


def run_wizard() -> dict:
    result = {}

    root = tk.Tk()
    root.title("RenderAgent Worker Setup")
    root.geometry("520x300")
    root.resizable(False, False)

    frame = tk.Frame(root, padx=20, pady=20)
    frame.pack(fill="both", expand=True)

    row = 0

    tk.Label(frame, text="RenderAgent Worker Setup", font=("Arial", 16, "bold")).grid(
        row=row, column=0, columnspan=3, pady=(0, 15)
    )
    row += 1

    tk.Label(frame, text="Controller URL:", anchor="e", width=18).grid(
        row=row, column=0, sticky="e", pady=4
    )
    url_var = tk.StringVar()
    url_entry = tk.Entry(frame, textvariable=url_var, width=30)
    url_entry.grid(row=row, column=1, columnspan=2, padx=5, pady=4, sticky="w")
    row += 1

    auto_discover = tk.BooleanVar(value=True)

    def toggle_url_entry():
        if auto_discover.get():
            url_entry.config(state="disabled", bg="#e5e7eb")
        else:
            url_entry.config(state="normal", bg="white")

    tk.Checkbutton(
        frame,
        text="Auto-discover on local network",
        variable=auto_discover,
        command=toggle_url_entry,
    ).grid(row=row, column=0, columnspan=3, sticky="w", pady=2)
    row += 1

    toggle_url_entry()

    tk.Label(frame, text="Output Folder:", anchor="e", width=18).grid(
        row=row, column=0, sticky="e", pady=4
    )
    output_var = tk.StringVar()
    tk.Entry(frame, textvariable=output_var, width=24).grid(
        row=row, column=1, padx=5, pady=4, sticky="w"
    )
    tk.Button(
        frame,
        text="Browse",
        command=lambda: output_var.set(filedialog.askdirectory()),
    ).grid(row=row, column=2, padx=2, pady=4)
    row += 1

    def on_submit():
        controller_url = url_var.get().strip()
        output_folder = output_var.get().strip()

        errors = []
        if not auto_discover.get() and not controller_url:
            errors.append("Controller URL is required when auto-discover is off")
        if not output_folder:
            errors.append("Output folder is required")
        elif not os.path.exists(output_folder):
            try:
                os.makedirs(output_folder, exist_ok=True)
            except Exception:
                errors.append("Cannot create output folder")

        if errors:
            messagebox.showerror("Validation Error", "\n".join(errors))
            return

        if auto_discover.get():
            result["controller_url"] = ""
        else:
            result["controller_url"] = controller_url
        result["output_folder"] = output_folder
        root.destroy()

    tk.Button(
        frame,
        text="Save & Start",
        command=on_submit,
        bg="#2563eb",
        fg="white",
        font=("Arial", 11, "bold"),
        padx=20,
        pady=6,
    ).grid(row=row, column=0, columnspan=3, pady=(20, 0))

    root.mainloop()
    return result