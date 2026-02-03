import tkinter as tk
from tkinter import ttk, messagebox
import requests
import threading
import time
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import os
import difflib
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("HYPIXEL_API_KEY")

BG_MAIN = "#0b0f19"
BG_CARD = "#161b26"
ACCENT = "#38bdf8"
TEXT_PRIMARY = "#f8fafc"
TEXT_SECONDARY = "#64748b"
GREEN = "#10b981"
RED = "#f43f5e"
GOLD = "#fbbf24"
WATCHLIST_FILE = "watchlist.txt"

class MarketTerminal:
    def __init__(self, root):
        self.root = root
        self.root.title("Market Flipper (EZ MONEY) - Public Edition")
        self.root.geometry("1100x900")
        self.root.configure(bg=BG_MAIN)
        
        self.history_prices = []
        self.history_times = []
        self.is_running = False
        self.current_task_id = 0
        self.item_list = []
        self.selected_profile_id = None
        self.user_uuid = None
        
        self.build_ui()
        self.load_watchlist()
        
        if not API_KEY:
            messagebox.showwarning("API Key Missing", "No HYPIXEL_API_KEY found in .env.\nBudget sync disabled.")
            
        threading.Thread(target=self.fetch_item_list, daemon=True).start()

    def build_ui(self):
        # Sidebar
        self.sidebar = tk.Frame(self.root, bg=BG_CARD, width=200, padx=15, pady=20)
        self.sidebar.pack(side="left", fill="y")
        
        tk.Label(self.sidebar, text="WATCHLIST", font=("Segoe UI", 10, "bold"), fg=ACCENT, bg=BG_CARD).pack(pady=(0, 10))
        self.listbox = tk.Listbox(self.sidebar, bg="#0b0f19", fg=TEXT_PRIMARY, borderwidth=0, 
                                 highlightthickness=0, font=("Consolas", 10), selectbackground=ACCENT)
        self.listbox.pack(fill="both", expand=True, pady=5)
        self.listbox.bind('<<ListboxSelect>>', self.on_select_favorite)
        
        tk.Button(self.sidebar, text="+ ADD CURRENT", command=self.add_to_watchlist, bg="#1e293b", fg=TEXT_PRIMARY, borderwidth=0, pady=5).pack(fill="x", pady=5)
        tk.Button(self.sidebar, text="- REMOVE", command=self.remove_from_watchlist, bg="#1e293b", fg=RED, borderwidth=0, pady=5).pack(fill="x")

        self.main_container = tk.Frame(self.root, bg=BG_MAIN)
        self.main_container.pack(side="right", fill="both", expand=True)

        header = tk.Frame(self.main_container, bg=BG_MAIN, pady=20)
        header.pack(fill="x", padx=30)
        tk.Label(header, text="Market Flipper", font=("Segoe UI", 22, "bold"), fg=TEXT_PRIMARY, bg=BG_MAIN).pack(side="left")
        self.lbl_status = tk.Label(header, text="● SYSTEM STANDBY", font=("Segoe UI", 9, "bold"), fg=TEXT_SECONDARY, bg=BG_MAIN)
        self.lbl_status.pack(side="right")

        # Username Field (Now with Enter key binding)
        user_frame = tk.Frame(self.main_container, bg=BG_CARD, padx=25, pady=15, highlightthickness=1, highlightbackground="#1e293b")
        user_frame.pack(fill="x", padx=30, pady=5)
        
        tk.Label(user_frame, text="MC USERNAME (Press Enter to load profiles)", bg=BG_CARD, fg=TEXT_SECONDARY, font=("Segoe UI", 7, "bold")).pack(anchor="w")
        self.ent_name = tk.Entry(user_frame, bg="#0b0f19", fg="white", borderwidth=0, font=("Consolas", 12), insertbackground="white")
        self.ent_name.pack(fill="x", pady=(5, 0))
        self.ent_name.bind("<Return>", lambda e: self.show_profile_selector())

        # Main Inputs
        input_frame = tk.Frame(self.main_container, bg=BG_CARD, padx=25, pady=25, highlightthickness=1, highlightbackground="#1e293b")
        input_frame.pack(fill="x", padx=30, pady=10)

        tk.Label(input_frame, text="ITEM ID", bg=BG_CARD, fg=TEXT_SECONDARY, font=("Segoe UI", 8, "bold")).grid(row=0, column=0, sticky="w")
        self.ent_item = tk.Entry(input_frame, bg="#0b0f19", fg="white", borderwidth=0, font=("Consolas", 13), insertbackground="white")
        self.ent_item.grid(row=1, column=0, sticky="ew", pady=(5, 10), padx=(0, 20))

        tk.Label(input_frame, text="BUDGET", bg=BG_CARD, fg=TEXT_SECONDARY, font=("Segoe UI", 8, "bold")).grid(row=0, column=1, sticky="w")
        self.ent_budget = tk.Entry(input_frame, bg="#0b0f19", fg="white", borderwidth=0, font=("Consolas", 13), insertbackground="white")
        self.ent_budget.grid(row=1, column=1, sticky="ew", pady=(5, 10))

        self.btn_action = tk.Button(input_frame, text="Start Tracking", command=self.toggle, bg=ACCENT, fg=BG_MAIN, font=("Segoe UI", 10, "bold"), borderwidth=0)
        self.btn_action.grid(row=2, column=0, columnspan=2, sticky="ew")

        # Stats and Chart
        self.chart_frame = tk.Frame(self.main_container, bg=BG_MAIN)
        self.chart_frame.pack(fill="both", expand=True, padx=30, pady=10)
        plt.style.use('dark_background')
        self.fig, self.ax = plt.subplots(figsize=(6, 4), dpi=100)
        self.fig.patch.set_facecolor(BG_MAIN); self.ax.set_facecolor(BG_MAIN)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        self.stats_frame = tk.Frame(self.main_container, bg=BG_CARD, padx=30, pady=25, highlightthickness=1, highlightbackground="#1e293b")
        self.stats_frame.pack(fill="x", padx=30, pady=(0, 30))
        self.val_unit_cost = self.create_box(self.stats_frame, "UNIT COST", 0, 0)
        self.val_sell_price = self.create_box(self.stats_frame, "UNIT SELL (TAXED)", 0, 1)
        self.val_volume = self.create_box(self.stats_frame, "24H VOLUME (BZ)", 0, 2)
        self.val_unit_profit = self.create_box(self.stats_frame, "PROFIT PER ITEM", 1, 0)
        self.val_roi = self.create_box(self.stats_frame, "ROI %", 1, 1)
        self.val_total_profit = self.create_box(self.stats_frame, "EST. TOTAL PROFIT", 1, 2)

    def create_box(self, parent, label, r, c):
        f = tk.Frame(parent, bg=BG_CARD); f.grid(row=r, column=c, sticky="nsew", pady=10); parent.grid_columnconfigure(c, weight=1)
        tk.Label(f, text=label, bg=BG_CARD, fg=TEXT_SECONDARY, font=("Segoe UI", 7, "bold")).pack(anchor="w")
        v = tk.Label(f, text="---", bg=BG_CARD, fg=TEXT_PRIMARY, font=("Consolas", 14, "bold")); v.pack(anchor="w")
        return v

    def show_profile_selector(self):
        username = self.ent_name.get().strip()
        if not API_KEY or not username:
            messagebox.showerror("Error", "Need both API Key in .env and a Username.")
            return

        try:
            uuid_res = requests.get(f"https://api.mojang.com/users/profiles/minecraft/{username}").json()
            self.user_uuid = uuid_res["id"]
            data = requests.get(f"https://api.hypixel.net/v2/skyblock/profiles?key={API_KEY}&uuid={self.user_uuid}").json()
            
            if not data.get("profiles"):
                messagebox.showerror("Error", "No SkyBlock profiles found.")
                return

            # Popup Window
            popup = tk.Toplevel(self.root)
            popup.title("Select Profile")
            popup.geometry("300x400")
            popup.configure(bg=BG_CARD)
            popup.transient(self.root)
            popup.grab_set()

            tk.Label(popup, text="CHOOSE PROFILE", bg=BG_CARD, fg=ACCENT, font=("Segoe UI", 10, "bold")).pack(pady=20)

            for profile in data["profiles"]:
                name = profile.get("cute_name", "Unknown")
                p_id = profile.get("profile_id")
                is_selected = " (ACTIVE)" if profile.get("selected") else ""
                
                btn = tk.Button(popup, text=f"{name}{is_selected}", 
                               command=lambda pid=p_id, n=name: self.set_profile(pid, n, popup),
                               bg="#1e293b", fg="white", borderwidth=0, pady=10, font=("Segoe UI", 9))
                btn.pack(fill="x", padx=20, pady=5)

        except Exception as e:
            messagebox.showerror("Error", f"Could not load profiles: {e}")

    def set_profile(self, profile_id, name, window):
        self.selected_profile_id = profile_id
        window.destroy()
        messagebox.showinfo("Success", f"Tracking profile: {name}")

    def get_purse_balance(self):
        if not API_KEY or not self.selected_profile_id or not self.user_uuid: return None
        try:
            res = requests.get(f"https://api.hypixel.net/v2/skyblock/profile?key={API_KEY}&profile={self.selected_profile_id}").json()
            member = res["profile"]["members"][self.user_uuid]
            purse = member.get("currencies", {}).get("coin_purse", 0)
            bank = member.get("banking", {}).get("balance", 0)
            return purse + bank
        except: return None

    def fetch_item_list(self):
        try:
            res = requests.get("https://raw.githubusercontent.com/NotEnoughUpdates/NotEnoughUpdates-Repo/master/index/items.json")
            if res.status_code == 200: self.item_list = res.json()
        except: pass

    def load_watchlist(self):
        if os.path.exists(WATCHLIST_FILE):
            with open(WATCHLIST_FILE, "r") as f:
                for line in f:
                    item = line.strip()
                    if item: self.listbox.insert(tk.END, item)

    def save_watchlist(self):
        items = self.listbox.get(0, tk.END)
        with open(WATCHLIST_FILE, "w") as f:
            for item in items: f.write(f"{item}\n")

    def add_to_watchlist(self):
        item = self.ent_item.get().upper().strip()
        if item and item not in self.listbox.get(0, tk.END): self.listbox.insert(tk.END, item); self.save_watchlist()

    def remove_from_watchlist(self):
        selection = self.listbox.curselection()
        if selection: self.listbox.delete(selection); self.save_watchlist()

    def on_select_favorite(self, event):
        selection = self.listbox.curselection()
        if selection:
            item = self.listbox.get(selection); self.ent_item.delete(0, tk.END); self.ent_item.insert(0, item)
            if self.is_running: self.toggle()

    def format_num(self, n):
        try:
            if n >= 1_000_000: return f"{n/1_000_000:.2f}M"
            if n >= 1_000: return f"{n/1_000:.1f}k"
            return f"{n:,.0f}"
        except: return "0"

    def update_chart(self):
        self.ax.clear(); self.ax.set_facecolor(BG_MAIN)
        if len(self.history_prices) > 1:
            self.ax.plot(self.history_times, self.history_prices, color=ACCENT, linewidth=2)
            self.ax.fill_between(self.history_times, self.history_prices, min(self.history_prices)*0.99, color=ACCENT, alpha=0.1)
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            self.fig.autofmt_xdate()
        self.ax.grid(color='#1e293b', linestyle='--', linewidth=0.5); self.canvas.draw()

    def toggle(self):
        if not self.is_running:
            target = self.ent_item.get().upper().replace(" ", "_").strip()
            if not target: messagebox.showwarning("Warning", "Enter a Target ID"); return
            self.is_running = True; self.current_task_id += 1
            self.btn_action.config(text="STOP TRACKING", bg=RED); self.lbl_status.config(text="● SESSION LIVE", fg=GREEN)
            self.history_prices = []; self.history_times = []
            threading.Thread(target=self.worker, args=(target, self.current_task_id), daemon=True).start()
        else:
            self.is_running = False; self.btn_action.config(text="Start Tracking", bg=ACCENT)
            self.lbl_status.config(text="● SYSTEM STANDBY", fg=TEXT_SECONDARY)

    def worker(self, raw_id, task_id):
        if self.item_list and raw_id not in self.item_list:
            matches = difflib.get_close_matches(raw_id, self.item_list, n=1, cutoff=0.6)
            if matches:
                correct_id = matches[0]
                if messagebox.askyesno("Typo?", f"Mean '{correct_id}'?"):
                    raw_id = correct_id
                    self.root.after(0, lambda: [self.ent_item.delete(0, tk.END), self.ent_item.insert(0, correct_id)])
                else: self.root.after(0, self.toggle); return
        try:
            res = requests.get(f"https://raw.githubusercontent.com/NotEnoughUpdates/NotEnoughUpdates-Repo/master/items/{raw_id}.json", timeout=10)
            data = res.json()
            raw_rec = data.get("recipe") or data.get("slayer_recipe") or (data.get("recipes") and data["recipes"][0])
            recipe = {p[0].split(".")[0]: int(p[1]) for s in (raw_rec.values() if isinstance(raw_rec, dict) else raw_rec) if isinstance(s, str) and ":" in s for p in [s.split(":")]}
        except: self.root.after(0, lambda: messagebox.showerror("Error", "Recipe not found")); self.root.after(0, self.toggle); return

        while self.is_running and task_id == self.current_task_id:
            try:
                balance = self.get_purse_balance()
                if balance is not None:
                    self.root.after(0, lambda b=balance: [self.ent_budget.delete(0, tk.END), self.ent_budget.insert(0, str(int(b)))])
                
                bz = requests.get("https://api.hypixel.net/v2/skyblock/bazaar").json()["products"]
                ah = requests.get("https://moulberry.codes/lowestbin.json").json()
                cost = sum((bz[ing]["quick_status"]["sellPrice"] if ing in bz else ah.get(ing, 0)) * amt for ing, amt in recipe.items())
                sell_raw = bz[raw_id]["quick_status"]["buyPrice"] if raw_id in bz else ah.get(raw_id, 0)
                vol = bz[raw_id]["quick_status"]["sellVolume"] if raw_id in bz else 0
                tax = 0.0125 if raw_id in bz else 0.02
                sell_taxed = sell_raw * (1 - tax); profit = sell_taxed - cost; roi = (profit / cost * 100) if cost > 0 else 0
                
                try:
                    mult = {'k': 1e3, 'm': 1e6, 'b': 1e9}
                    b_str = self.ent_budget.get().lower()
                    b_val = float(b_str[:-1]) * mult[b_str[-1]] if b_str[-1] in mult else float(b_str)
                    total_p = profit * (b_val // cost)
                except: total_p = 0
                
                self.history_prices.append(sell_raw); self.history_times.append(datetime.now())
                self.root.after(0, self.update_display, cost, sell_taxed, profit, roi, total_p, vol)
                time.sleep(15)
            except: time.sleep(5)

    def update_display(self, cost, sell, profit, roi, total_p, vol):
        self.val_unit_cost.config(text=self.format_num(cost))
        self.val_sell_price.config(text=self.format_num(sell))
        self.val_unit_profit.config(text=self.format_num(profit), fg=GREEN if profit > 0 else RED)
        self.val_roi.config(text=f"{roi:.2f}%", fg=GREEN if roi > 0 else RED)
        self.val_total_profit.config(text=self.format_num(total_p), fg=GREEN if total_p > 0 else RED)
        self.val_volume.config(text=self.format_num(vol))
        self.update_chart()

if __name__ == "__main__":
    root = tk.Tk(); app = MarketTerminal(root); root.mainloop()