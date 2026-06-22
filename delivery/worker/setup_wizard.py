# ===== worker/setup_wizard.py =====

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
import socket
import threading

# Theme colors
BG_COLOR = "#000000"
ACCENT_COLOR = "#B76E79"
FG_COLOR = "#FFFFFF"
GRAY_COLOR = "#333333"
LIGHT_GRAY = "#AAAAAA"


def discover_controller(timeout_s=5):
    """Try to discover the controller via UDP broadcast."""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout_s)
        sock.sendto(b"RENDERAGENT_DISCOVER", ("255.255.255.255", 8766))
        data, addr = sock.recvfrom(1024)
        response = data.decode()
        if response.startswith("RENDERAGENT_CONTROLLER "):
            url = response.split(" ", 1)[1].strip()
            return url
    except Exception:
        return None


def run_wizard() -> dict:
    result = {}

    root = tk.Tk()
    root.title("RenderAgent Worker Setup")
    root.geometry("560x480")
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
    tk.Label(root, text="RenderAgent Worker", font=("Inter", 18, "bold"), bg=BG_COLOR, fg=ACCENT_COLOR).pack()
    tk.Label(root, text="Setup Wizard", font=("Inter", 12), bg=BG_COLOR, fg=LIGHT_GRAY).pack(pady=(0, 20))

    # Controller IP / URL
    frame_url = tk.Frame(root, bg=BG_COLOR)
    frame_url.pack(padx=30, pady=5, fill="x")
    tk.Label(frame_url, text="Controller IP:", font=("Inter", 10), bg=BG_COLOR, fg=FG_COLOR, width=15, anchor="e").pack(side="left")
    url_var = tk.StringVar()
    url_entry = tk.Entry(frame_url, textvariable=url_var, bg=GRAY_COLOR, fg=FG_COLOR, insertbackground=FG_COLOR, font=("Inter", 10), width=30)
    url_entry.pack(side="left", padx=5)

    discover_btn = tk.Button(frame_url, text="AUTO-DISCOVER", bg=GRAY_COLOR, fg=ACCENT_COLOR, font=("Inter", 8, "bold"))
    discover_btn.pack(side="left")

    # Auto-discover status label
    discover_status = tk.Label(root, text="", font=("Inter", 9), bg=BG_COLOR, fg=FG_COLOR)
    discover_status.pack()

    def do_discover():
        discover_status.config(text="Searching...", fg=LIGHT_GRAY)
        discover_btn.config(state="disabled")
        root.update()
        found = discover_controller(timeout_s=5)
        if found:
            url_var.set(found)
            discover_status.config(text=f"Found: {found}", fg="#00FF00")
        else:
            discover_status.config(text="No controller found. Please enter manually.", fg="#FF5555")
        discover_btn.config(state="normal")

    discover_btn.config(command=do_discover)

    # Output Folder
    frame_output = tk.Frame(root, bg=BG_COLOR)
    frame_output.pack(padx=30, pady=5, fill="x")
    tk.Label(frame_output, text="Output Folder:", font=("Inter", 10), bg=BG_COLOR, fg=FG_COLOR, width=15, anchor="e").pack(side="left")
    output_var = tk.StringVar(value="C:\\RenderAgent\\output")
    tk.Entry(frame_output, textvariable=output_var, bg=GRAY_COLOR, fg=FG_COLOR, insertbackground=FG_COLOR, font=("Inter", 10), width=30).pack(side="left", padx=5)
    tk.Button(frame_output, text="Browse", bg=GRAY_COLOR, fg=FG_COLOR, font=("Inter", 8), command=lambda: output_var.set(filedialog.askdirectory())).pack(side="left")

    # Divider
    tk.Frame(root, bg=ACCENT_COLOR, height=2).pack(fill="x", padx=30, pady=15)

    # Save Button
    def on_save():
        controller_url = url_var.get().strip()
        output_folder = output_var.get().strip()

        errors = []
        if not controller_url:
            errors.append("Controller IP/URL is required. Click AUTO-DISCOVER or enter manually.")
        if not output_folder:
            errors.append("Output folder is required")

        if errors:
            messagebox.showerror("Validation Error", "\n".join(errors))
            return

        # Create folder if needed
        try:
            os.makedirs(output_folder, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Could not create output folder:\n{e}")
            return

        result["controller_url"] = controller_url
        result["output_folder"] = output_folder
        root.destroy()
        messagebox.showinfo("Success", "Setup saved! You can now start using RenderAgent Worker.")

    save_btn = tk.Button(root, text="SAVE", font=("Inter", 12, "bold"), bg=ACCENT_COLOR, fg="white", activebackground="#D4939D", activeforeground="white", command=on_save, padx=30, pady=8)
    save_btn.pack(pady=20)

    # Footer
    tk.Label(root, text="RenderAgent Worker Setup", font=("Inter", 8), bg=BG_COLOR, fg=LIGHT_GRAY).pack(side="bottom", pady=5)

    root.mainloop()
    return result
