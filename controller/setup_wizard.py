# ===== controller/setup_wizard.py =====

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox


def is_config_complete() -> bool:
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from shared.config import Config

        config = Config()
        return config.is_complete()
    except Exception:
        return False


def run_wizard() -> dict:
    result = {}

    root = tk.Tk()
    root.title("RenderAgent Setup")
    root.geometry("520x260")
    root.resizable(False, False)

    frame = tk.Frame(root, padx=20, pady=20)
    frame.pack(fill="both", expand=True)

    row = 0

    tk.Label(frame, text="RenderAgent Setup", font=("Arial", 16, "bold")).grid(
        row=row, column=0, columnspan=3, pady=(0, 15)
    )
    row += 1

    tk.Label(frame, text="Input Folder:", anchor="e", width=15).grid(
        row=row, column=0, sticky="e", pady=4
    )
    input_var = tk.StringVar()
    tk.Entry(frame, textvariable=input_var, width=28).grid(
        row=row, column=1, padx=5, pady=4, sticky="w"
    )
    tk.Button(
        frame,
        text="Browse",
        command=lambda: input_var.set(filedialog.askdirectory()),
    ).grid(row=row, column=2, padx=2, pady=4)
    row += 1

    tk.Label(frame, text="Output Folder:", anchor="e", width=15).grid(
        row=row, column=0, sticky="e", pady=4
    )
    output_var = tk.StringVar()
    tk.Entry(frame, textvariable=output_var, width=28).grid(
        row=row, column=1, padx=5, pady=4, sticky="w"
    )
    tk.Button(
        frame,
        text="Browse",
        command=lambda: output_var.set(filedialog.askdirectory()),
    ).grid(row=row, column=2, padx=2, pady=4)
    row += 1

    def on_submit():
        input_folder = input_var.get().strip()
        output_folder = output_var.get().strip()

        errors = []
        if not input_folder:
            errors.append("Input folder is required")
        elif not os.path.exists(input_folder):
            try:
                os.makedirs(input_folder, exist_ok=True)
            except Exception:
                errors.append("Cannot create input folder")
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

        result["input_folder"] = input_folder
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