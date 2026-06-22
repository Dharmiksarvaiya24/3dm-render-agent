# ===== controller/setup_wizard.py =====

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
import socket

# Theme colors
BG_COLOR = "#000000"
ACCENT_COLOR = "#B76E79"
FG_COLOR = "#FFFFFF"
GRAY_COLOR = "#333333"
LIGHT_GRAY = "#AAAAAA"


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
    root.title("RenderAgent Controller Setup")
    root.geometry("560x520")
    root.resizable(False, False)
    root.configure(bg=BG_COLOR)

    # Logo
    try:
        logo_img = tk.PhotoImage(file=os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png"))
        logo_label = tk.Label(root, image=logo_img, bg=BG_COLOR)
        logo_label.image = logo_img
        logo_label.pack(pady=(20, 10))
    except Exception:
        pass

    # Title
    tk.Label(root, text="RenderAgent Controller", font=("Inter", 18, "bold"), bg=BG_COLOR, fg=ACCENT_COLOR).pack()
    tk.Label(root, text="Setup Wizard", font=("Inter", 12), bg=BG_COLOR, fg=LIGHT_GRAY).pack(pady=(0, 20))

    # iJewel Email
    frame_email = tk.Frame(root, bg=BG_COLOR)
    frame_email.pack(padx=30, pady=5, fill="x")
    tk.Label(frame_email, text="iJewel Email:", font=("Inter", 10), bg=BG_COLOR, fg=FG_COLOR, width=15, anchor="e").pack(side="left")
    email_var = tk.StringVar()
    tk.Entry(frame_email, textvariable=email_var, bg=GRAY_COLOR, fg=FG_COLOR, insertbackground=FG_COLOR, font=("Inter", 10), width=35).pack(side="left", padx=5)

    # Password
    frame_pass = tk.Frame(root, bg=BG_COLOR)
    frame_pass.pack(padx=30, pady=5, fill="x")
    tk.Label(frame_pass, text="Password:", font=("Inter", 10), bg=BG_COLOR, fg=FG_COLOR, width=15, anchor="e").pack(side="left")
    pass_var = tk.StringVar()
    pass_entry = tk.Entry(frame_pass, textvariable=pass_var, bg=GRAY_COLOR, fg=FG_COLOR, insertbackground=FG_COLOR, font=("Inter", 10), width=32, show="*")
    pass_entry.pack(side="left", padx=5)
    show_btn = tk.Button(frame_pass, text="Show", bg=GRAY_COLOR, fg=FG_COLOR, font=("Inter", 8), command=lambda: toggle_show())
    show_btn.pack(side="left")

    def toggle_show():
        if pass_entry.cget("show") == "*":
            pass_entry.config(show="")
            show_btn.config(text="Hide")
        else:
            pass_entry.config(show="*")
            show_btn.config(text="Show")

    # Input Folder
    frame_input = tk.Frame(root, bg=BG_COLOR)
    frame_input.pack(padx=30, pady=5, fill="x")
    tk.Label(frame_input, text="Input Folder:", font=("Inter", 10), bg=BG_COLOR, fg=FG_COLOR, width=15, anchor="e").pack(side="left")
    input_var = tk.StringVar(value="C:\\RenderAgent\\input")
    tk.Entry(frame_input, textvariable=input_var, bg=GRAY_COLOR, fg=FG_COLOR, insertbackground=FG_COLOR, font=("Inter", 10), width=32).pack(side="left", padx=5)
    tk.Button(frame_input, text="Browse", bg=GRAY_COLOR, fg=FG_COLOR, font=("Inter", 8), command=lambda: input_var.set(filedialog.askdirectory())).pack(side="left")

    # Output Folder
    frame_output = tk.Frame(root, bg=BG_COLOR)
    frame_output.pack(padx=30, pady=5, fill="x")
    tk.Label(frame_output, text="Output Folder:", font=("Inter", 10), bg=BG_COLOR, fg=FG_COLOR, width=15, anchor="e").pack(side="left")
    output_var = tk.StringVar(value="C:\\RenderAgent\\output")
    tk.Entry(frame_output, textvariable=output_var, bg=GRAY_COLOR, fg=FG_COLOR, insertbackground=FG_COLOR, font=("Inter", 10), width=32).pack(side="left", padx=5)
    tk.Button(frame_output, text="Browse", bg=GRAY_COLOR, fg=FG_COLOR, font=("Inter", 8), command=lambda: output_var.set(filedialog.askdirectory())).pack(side="left")

    # Divider
    tk.Frame(root, bg=ACCENT_COLOR, height=2).pack(fill="x", padx=30, pady=15)

    # Save Button
    def on_save():
        email = email_var.get().strip()
        password = pass_var.get()
        input_folder = input_var.get().strip()
        output_folder = output_var.get().strip()

        errors = []
        if not email:
            errors.append("iJewel Email is required")
        if not password:
            errors.append("Password is required")
        if not input_folder:
            errors.append("Input folder is required")
        if not output_folder:
            errors.append("Output folder is required")

        if errors:
            messagebox.showerror("Validation Error", "\n".join(errors))
            return

        # Create folders if they don't exist
        try:
            os.makedirs(input_folder, exist_ok=True)
            os.makedirs(output_folder, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Could not create folders:\n{e}")
            return

        result["ijewel_email"] = email
        result["ijewel_password"] = password
        result["input_folder"] = input_folder
        result["output_folder"] = output_folder
        root.destroy()
        messagebox.showinfo("Success", "Setup saved! You can now start using RenderAgent.")

    save_btn = tk.Button(root, text="SAVE", font=("Inter", 12, "bold"), bg=ACCENT_COLOR, fg="white", activebackground="#D4939D", activeforeground="white", command=on_save, padx=30, pady=8)
    save_btn.pack(pady=20)

    # Footer
    tk.Label(root, text="RenderAgent Controller Setup", font=("Inter", 8), bg=BG_COLOR, fg=LIGHT_GRAY).pack(side="bottom", pady=5)

    root.mainloop()
    return result
