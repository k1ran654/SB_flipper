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

# --- CONFIG & THEME ---
load_dotenv("api.env")
API_KEY = os.getenv("HYPIXEL_API_KEY")

BG_MAIN = "#0b0f19"
BG_CARD = "#161b26"
ACCENT = "#38bdf8"
TEXT_PRIMARY = "#f8fafc"
TEXT_SECONDARY = "#64748b"
GREEN = "#10b981"
RED = "#f43f5e"
WATCHLIST_FILE = "watchlist.txt"

class MarketTerminal:
    def __init__(self, root):
        self.root = root
        self.root.title("Market Flipper (EZ MONEY)")
        self.root.geometry("1100x950")
        self.root.configure(bg=BG_MAIN)
        
        self.history_prices = []
        self.history_times = []
        self.is_running = False
        self.current_task_id = 0
        self.item_list = {} 
        self.selected_profile_id = None
        self.user_uuid = None
        
        self.build_ui()
        self.load_watchlist()
        
        # Load official Hypixel Item List for Name -> ID mapping
        threading.Thread(target=self.fetch_item_list, daemon=True).start()

    def build_ui(self):
        # --- SIDEBAR ---
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

        # --- HEADER ---
        header = tk.Frame(self.main_container, bg=BG_MAIN, pady=20)
        header.pack(fill="x", padx=30)
        tk.Label(header, text="Market Flipper", font=("Segoe UI", 22, "bold"), fg=TEXT_PRIMARY, bg=BG_MAIN).pack(side="left")
        self.lbl_status = tk.Label(header, text="● SYSTEM STANDBY", font=("Segoe UI", 9, "bold"), fg=TEXT_SECONDARY, bg=BG_MAIN)
        self.lbl_status.pack(side="right")

        # --- USERNAME BAR (WITH COMMENTS) ---
        user_frame = tk.Frame(self.main_container, bg=BG_CARD, padx=25, pady=15, highlightthickness=1, highlightbackground="#1e293b")
        user_frame.pack(fill="x", padx=30, pady=5)
        tk.Label(user_frame, text="MC USERNAME (Press Enter to load profiles)", bg=BG_CARD, fg=TEXT_SECONDARY, font=("Segoe UI", 7, "bold")).pack(anchor="w")
        self.ent_name = tk.Entry(user_frame, bg="#0b0f19", fg="white", borderwidth=0, font=("Consolas", 12), insertbackground="white")
        self.ent_name.pack(fill="x", pady=(5, 0))
        self.ent_name.bind("<Return>", lambda e: self.show_profile_selector())

        # --- INPUT BARS (WITH COMMENTS) ---
        input_frame = tk.Frame(self.main_container, bg=BG_CARD, padx=25, pady=25, highlightthickness=1, highlightbackground="#1e293b")
        input_frame.pack(fill="x", padx=30, pady=10)

        tk.Label(input_frame, text="ITEM NAME OR ID", bg=BG_CARD, fg=TEXT_SECONDARY, font=("Segoe UI", 8, "bold")).grid(row=0, column=0, sticky="w")
        self.ent_item = tk.Entry(input_frame, bg="#0b0f19", fg="white", borderwidth=0, font=("Consolas", 13), insertbackground="white")
        self.ent_item.grid(row=1, column=0, sticky="ew", pady=(5, 10), padx=(0, 20))

        tk.Label(input_frame, text="BUDGET (Auto-synced from Purse)", bg=BG_CARD, fg=TEXT_SECONDARY, font=("Segoe UI", 8, "bold")).grid(row=0, column=1, sticky="w")
        self.ent_budget = tk.Entry(input_frame, bg="#0b0f19", fg="white", borderwidth=0, font=("Consolas", 13), insertbackground="white")
        self.ent_budget.grid(row=1, column=1, sticky="ew", pady=(5, 10))
        input_frame.grid_columnconfigure(0, weight=1); input_frame.grid_columnconfigure(1, weight=1)

        self.btn_action = tk.Button(input_frame, text="Start Tracking", command=self.toggle, bg=ACCENT, fg=BG_MAIN, font=("Segoe UI", 10, "bold"), borderwidth=0)
        self.btn_action.grid(row=2, column=0, columnspan=2, sticky="ew")

        # --- STATS BOXES ---
        self.chart_frame = tk.Frame(self.main_container, bg=BG_MAIN)
        self.chart_frame.pack(fill="both", expand=True, padx=30, pady=10)
        plt.style.use('dark_background')
        self.fig, self.ax = plt.subplots(figsize=(6, 4), dpi=100)
        self.fig.patch.set_facecolor(BG_MAIN); self.ax.set_facecolor(BG_MAIN)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        self.stats_frame = tk.Frame(self.main_container, bg=BG_CARD, padx=30, pady=15, highlightthickness=1, highlightbackground="#1e293b")
        self.stats_frame.pack(fill="x", padx=30, pady=(0, 30))
        
        self.val_unit_cost = self.create_box(self.stats_frame, "UNIT COST", 0, 0)
        self.val_sell_price = self.create_box(self.stats_frame, "UNIT SELL (TAXED)", 0, 1)
        self.val_can_craft = self.create_box(self.stats_frame, "CAN CRAFT", 0, 2)
        self.val_unit_profit = self.create_box(self.stats_frame, "PROFIT PER ITEM", 1, 0)
        self.val_roi = self.create_box(self.stats_frame, "ROI %", 1, 1)
        self.val_total_profit = self.create_box(self.stats_frame, "EST. TOTAL PROFIT", 1, 2)

    def create_box(self, parent, label, r, c):
        f = tk.Frame(parent, bg=BG_CARD); f.grid(row=r, column=c, sticky="nsew", pady=10); parent.grid_columnconfigure(c, weight=1)
        tk.Label(f, text=label, bg=BG_CARD, fg=TEXT_SECONDARY, font=("Segoe UI", 7, "bold")).pack(anchor="w")
        v = tk.Label(f, text="---", bg=BG_CARD, fg=TEXT_PRIMARY, font=("Consolas", 14, "bold")); v.pack(anchor="w")
        return v

    def fetch_item_list(self):
        try:
            url = "https://api.hypixel.net/v2/resources/skyblock/items"
            res = requests.get(url, timeout=10).json()
            if res.get("success"):
                self.item_list = {item['name'].lower(): item['id'] for item in res.get("items", [])}
                print(f"[*] LOADED {len(self.item_list)} ITEMS FROM HYPIXEL.")
        except Exception as e:
            print(f"[!] FAILED TO LOAD ITEM NAMES: {e}")

    def get_internal_id(self, user_input):
        cleaned = user_input.strip().lower()
        if cleaned in self.item_list: return self.item_list[cleaned]
        matches = difflib.get_close_matches(cleaned, list(self.item_list.keys()), n=1, cutoff=0.7)
        if matches: return self.item_list[matches[0]]
        return user_input.upper().replace(" ", "_").strip()

    def show_profile_selector(self):
        username = self.ent_name.get().strip()
        if not username: return
        try:
            uuid_res = requests.get(f"https://api.mojang.com/users/profiles/minecraft/{username}").json()
            self.user_uuid = uuid_res["id"]
            data = requests.get(f"https://api.hypixel.net/v2/skyblock/profiles?key={API_KEY}&uuid={self.user_uuid}").json()
            
            # --- STYLED POPUP ---
            popup = tk.Toplevel(self.root); popup.configure(bg=BG_CARD); popup.geometry("300x400")
            tk.Label(popup, text="SELECT PROFILE", bg=BG_CARD, fg=ACCENT, font=("Segoe UI", 10, "bold"), pady=15).pack()
            for p in data.get("profiles", []):
                btn = tk.Button(popup, text=p.get("cute_name").upper(), bg="#1e293b", fg="white", font=("Consolas", 10), pady=10, borderwidth=0,
                               command=lambda pid=p["profile_id"], n=p["cute_name"]: [self.set_profile(pid, n, popup)])
                btn.pack(fill="x", padx=20, pady=5)
        except: pass

    def set_profile(self, pid, name, win):
        self.selected_profile_id = pid; win.destroy()
        messagebox.showinfo("Profile Ready", f"Linked to {name}")

    def get_purse_balance(self):
        if not API_KEY or not self.selected_profile_id or not self.user_uuid: return None
        try:
            url = f"https://api.hypixel.net/v2/skyblock/profile?key={API_KEY}&profile={self.selected_profile_id}"
            res = requests.get(url, timeout=10).json()
            if not res.get("success"): return None
            prof = res.get("profile", {}); members = prof.get("members", {})
            my_uuid = self.user_uuid.replace("-", "")
            for m_id, m_data in members.items():
                if m_id.replace("-", "") == my_uuid:
                    purse = m_data.get("currencies", {}).get("coin_purse", 0) or m_data.get("coin_purse", 0)
                    bank = m_data.get("banking", {}).get("balance", 0) or prof.get("banking", {}).get("balance", 0)
                    return purse + bank
            return None
        except: return None

    def format_num(self, n):
        if n >= 1e6: return f"{n/1e6:.2f}M"
        if n >= 1e3: return f"{n/1e3:.1f}k"
        return f"{n:,.0f}"

    def load_watchlist(self):
        if os.path.exists(WATCHLIST_FILE):
            with open(WATCHLIST_FILE, "r") as f:
                for line in f: self.listbox.insert(tk.END, line.strip())

    def save_watchlist(self):
        with open(WATCHLIST_FILE, "w") as f:
            for item in self.listbox.get(0, tk.END): f.write(f"{item}\n")

    def add_to_watchlist(self):
        item = self.ent_item.get().upper().strip()
        if item and item not in self.listbox.get(0, tk.END): self.listbox.insert(tk.END, item); self.save_watchlist()

    def remove_from_watchlist(self):
        sel = self.listbox.curselection()
        if sel: self.listbox.delete(sel); self.save_watchlist()

    def on_select_favorite(self, e):
        sel = self.listbox.curselection()
        if sel:
            item = self.listbox.get(sel); self.ent_item.delete(0, tk.END); self.ent_item.insert(0, item)

    def toggle(self):
        if not self.is_running:
            raw_input = self.ent_item.get()
            if not raw_input: return
            target = self.get_internal_id(raw_input)
            self.is_running = True; self.current_task_id += 1
            self.btn_action.config(text="STOP TRACKING", bg=RED); self.lbl_status.config(text="● SESSION LIVE", fg=GREEN)
            threading.Thread(target=self.worker, args=(target, self.current_task_id), daemon=True).start()
        else:
            self.is_running = False
            self.btn_action.config(text="Start Tracking", bg=ACCENT); self.lbl_status.config(text="● SYSTEM STANDBY", fg=TEXT_SECONDARY)

    def worker(self, raw_id, t_id):
        print(f"[*] TARGET ACQUIRED: {raw_id}")
        try:
            # NEU SUBFOLDER PATHING
            first_letter = raw_id[0].upper()
            url = f"https://raw.githubusercontent.com/NotEnoughUpdates/NotEnoughUpdates-Repo/master/items/{first_letter}/{raw_id}.json"
            res_raw = requests.get(url, timeout=10)
            if res_raw.status_code != 200:
                url = f"https://raw.githubusercontent.com/NotEnoughUpdates/NotEnoughUpdates-Repo/master/items/{raw_id}.json"
                res_raw = requests.get(url, timeout=10)
            
            data = res_raw.json()
            raw_rec = data.get("recipe") or data.get("slayer_recipe") or (data.get("recipes") and data["recipes"][0])
            if not raw_rec:
                self.root.after(0, lambda: messagebox.showwarning("No Recipe", f"{raw_id} is not craftable."))
                self.root.after(0, self.toggle); return

            recipe = {}
            rec_items = raw_rec.values() if isinstance(raw_rec, dict) else raw_rec
            for entry in rec_items:
                if isinstance(entry, str) and ":" in entry:
                    parts = entry.split(":"); ing_id = parts[0].split(".")[0]; amount = int(parts[1])
                    recipe[ing_id] = recipe.get(ing_id, 0) + amount
            print(f"[*] RECIPE LOADED: {len(recipe)} ingredients.")
        except Exception as e:
            print(f"[!] RECIPE ERROR: {e}")
            self.root.after(0, self.toggle); return

        while self.is_running and t_id == self.current_task_id:
            try:
                # 1. BAZAAR (Fast)
                bz = requests.get("https://api.hypixel.net/v2/skyblock/bazaar", timeout=5).json()["products"]
                
                # 2. PURSE
                bal = self.get_purse_balance()
                if bal is not None:
                    self.root.after(0, lambda b=bal: [self.ent_budget.delete(0, tk.END), self.ent_budget.insert(0, str(int(b)))])

                # 3. SMART PRICE FETCH (Lazy-load AH)
                ah = {}
                needs_ah = any(ing not in bz for ing in recipe.keys()) or raw_id not in bz
                if needs_ah:
                    print("[!] AH FETCH REQUIRED...")
                    ah = requests.get("https://moulberry.codes/lowestbin.json", timeout=10).json()

                crafting_cost = sum((bz[ing]["quick_status"]["sellPrice"] if ing in bz else ah.get(ing, 0)) * amt for ing, amt in recipe.items())
                sell_val = bz[raw_id]["quick_status"]["buyPrice"] if raw_id in bz else ah.get(raw_id, 0)
                sell_taxed = sell_val * 0.9875; profit = sell_taxed - crafting_cost
                
                # 4. CALCS
                try:
                    budget = float(self.ent_budget.get().replace(",", ""))
                    can_craft = int(budget // crafting_cost) if crafting_cost > 0 else 0
                    total_profit = profit * can_craft
                except: can_craft = 0; total_profit = 0

                # 5. UI UPDATE
                self.history_prices.append(sell_val); self.history_times.append(datetime.now())
                self.root.after(0, self.update_display, crafting_cost, sell_taxed, profit, (profit/crafting_cost*100) if crafting_cost>0 else 0, total_profit, can_craft)
                time.sleep(15)
            except Exception as e:
                print(f"[!] DATA LOOP ERROR: {e}"); time.sleep(5)

    def update_display(self, cost, sell, profit, roi, total_p, can_craft):
        self.val_unit_cost.config(text=self.format_num(cost))
        self.val_sell_price.config(text=self.format_num(sell))
        self.val_unit_profit.config(text=self.format_num(profit), fg=GREEN if profit>0 else RED)
        self.val_roi.config(text=f"{roi:.2f}%", fg=GREEN if roi>0 else RED)
        self.val_total_profit.config(text=self.format_num(total_p), fg=GREEN if total_p>0 else RED)
        self.val_can_craft.config(text=str(can_craft))

        # --- FIX THE CHART SCALE ---
        self.ax.clear()
        self.ax.plot(self.history_times, self.history_prices, color=ACCENT, linewidth=2)
        
        # Disable the annoying scientific notation (e.g., +8.35e5)
        self.ax.get_yaxis().get_major_formatter().set_useOffset(False)
        self.ax.get_yaxis().get_major_formatter().set_scientific(False)
        
        # Add a 5% "buffer" to the top and bottom so the line isn't touching the edges
        if len(self.history_prices) > 1:
            ymin, ymax = min(self.history_prices), max(self.history_prices)
            margin = (ymax - ymin) * 0.05 if ymax != ymin else ymin * 0.01
            self.ax.set_ylim(ymin - margin, ymax + margin)

        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        self.fig.tight_layout()
        self.canvas.draw()

if __name__ == "__main__":
    root = tk.Tk(); app = MarketTerminal(root); root.mainloop()