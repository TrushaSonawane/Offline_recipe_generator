import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import scrolledtext
import random, json, os

# =========================================
# Config
# =========================================
LOCAL_DB_PATH = "recipes_local.json"   # Single source of truth (JSON file)


# =========================================
# Data loading (JSON only)
# =========================================
def load_local_db():
    """
    Load recipes from recipes_local.json.
    Expected schema for each recipe:
    {
      "name": str,
      "minutes": int,
      "ingredients": [str, ...],
      "steps": [str, ...],
      "area": str,
      "category": str,
      "source_url": str (optional)
    }
    """
    if not os.path.exists(LOCAL_DB_PATH):
        messagebox.showerror(
            "Missing recipes_local.json",
            f"Couldn't find {LOCAL_DB_PATH} in the app folder.\n\n"
            "Create the file and add recipes in JSON format."
        )
        return []

    try:
        with open(LOCAL_DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("Top-level JSON must be a list of recipes.")
        # Light validation & normalization
        fixed = []
        for rec in data:
            if not isinstance(rec, dict):
                continue
            name = str(rec.get("name", "")).strip()
            minutes = int(rec.get("minutes", 0) or 0)
            ings = rec.get("ingredients", [])
            steps = rec.get("steps", [])
            area = str(rec.get("area", "")).strip()
            category = str(rec.get("category", "")).strip()
            src = rec.get("source_url", None)

            if not name or minutes <= 0 or not isinstance(ings, list) or not ings:
                continue

            # Normalize ingredients to simple strings
            norm_ings = []
            for x in ings:
                if isinstance(x, str) and x.strip():
                    norm_ings.append(x.strip().lower())
            if not norm_ings:
                continue

            # Normalize steps to strings (placeholder allowed)
            norm_steps = []
            for s in steps if isinstance(steps, list) else []:
                if isinstance(s, str) and s.strip():
                    norm_steps.append(s.strip())
            if not norm_steps:
                norm_steps = ["(Add steps)"]

            rec_fixed = {
                "name": name,
                "minutes": minutes,
                "ingredients": norm_ings,
                "steps": norm_steps,
                "area": area,
                "category": category,
            }
            if isinstance(src, str) and src.strip():
                rec_fixed["source_url"] = src.strip()

            fixed.append(rec_fixed)
        return fixed
    except Exception as e:
        messagebox.showerror(
            "Invalid recipes_local.json",
            f"Couldn't read {LOCAL_DB_PATH}.\n\nError: {e}\n\n"
            "Fix the JSON (valid array of recipe objects) and try again."
        )
        return []


def all_local_ingredients(recipes):
    s = set()
    for r in recipes:
        s.update([i.lower() for i in r["ingredients"]])
    return s


def normalize_tokens(s: str):
    # comma/space separated, lowercase, trimmed; merge a couple of multi-words
    tokens = []
    for chunk in s.split(","):
        for t in chunk.split():
            t = t.strip().lower()
            if t:
                tokens.append(t)
    merged = []
    i = 0
    while i < len(tokens):
        if i + 1 < len(tokens) and f"{tokens[i]} {tokens[i+1]}" in {"olive oil", "soy sauce"}:
            merged.append(f"{tokens[i]} {tokens[i+1]}")
            i += 2
        else:
            merged.append(tokens[i])
            i += 1
    return set(merged)


def format_local_recipe(r: dict) -> str:
    parts = [f"{r['name']}  •  {r['minutes']} min"]
    sub = " / ".join([x for x in [r.get("category", ""), r.get("area", "")] if x])
    if sub:
        parts.append(sub)
    parts.append("")
    parts.append("Ingredients:")
    for ing in sorted(set(i.title() for i in r["ingredients"])):
        parts.append(f"• {ing}")
    parts.append("")
    parts.append("Steps:")
    for i, step in enumerate(r["steps"], 1):
        parts.append(f"{i}. {step}")
    if r.get("source_url"):
        parts.append("")
        parts.append(f"Source: {r['source_url']}")
    return "\n".join(parts)


# =========================================
# UI App
# =========================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🍓 Strawberry Recipe Picker")
        self.geometry("840x700")
        self.minsize(760, 620)
        self.configure(bg="#fff5f8")  # strawberry milk

        # Palette
        self.c_bg = "#fff5f8"
        self.c_card = "#ffe4ec"
        self.c_accent = "#ff6b9a"
        self.c_accent2 = "#ff8fb3"
        self.c_text = "#4a1631"

        # Style
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TLabel", background=self.c_bg, foreground=self.c_text)
        style.configure("Card.TFrame", background=self.c_card, relief="flat")
        style.configure("Accent.TButton", padding=8, font=("Segoe UI", 14))
        style.map("Accent.TButton",
                  background=[("!disabled", self.c_accent)],
                  foreground=[("!disabled", "white")])
        style.configure("TEntry", fieldbackground="white")

        # Build UI
        self._build_header()
        self._build_form()
        self._build_output()

        # Data
        self.local_recipes = load_local_db()
        self.local_ingredients = all_local_ingredients(self.local_recipes) if self.local_recipes else set()

        # UX: Enter key triggers Generate
        self.bind("<Return>", lambda _e: self.generate())

    # ---------- Header ----------
    def _build_header(self):
        self.header = ttk.Frame(self, style="Card.TFrame")
        self.header.place(relx=0.5, rely=0.04, anchor="n", relwidth=0.94, height=80)

        ttk.Label(self.header, text="🍓 Strawberry Recipe Picker",
                  font=("Segoe UI", 22, "bold"), background=self.c_card).pack(pady=(10, 2))
        ttk.Label(self.header, text="Offline recipe generator — fast & light.",
                  font=("Segoe UI", 10), background=self.c_card).pack()

        # Add Recipe button in the header (top-right)
        self.add_btn = ttk.Button(self.header, text="➕ Add Recipe", style="Accent.TButton",
                                  command=self.add_recipe_dialog)
        self.add_btn.place(relx=1.0, x=-12, y=12, anchor="ne")

    # ---------- Form ----------
    def _build_form(self):
        card = ttk.Frame(self, style="Card.TFrame")
        # height 240 to allow breathing room below the grey bar
        card.place(relx=0.5, rely=0.17, anchor="n", relwidth=0.94, height=240)

        ttk.Label(card, text="Ingredients to include (comma-separated):",
                  background=self.c_card).place(x=16, y=12)

        self.ing_entry = ttk.Entry(card, width=95, font=("Segoe UI", 12))
        self.ing_entry.place(x=16, y=36, height=30)

        ttk.Label(card, text="Max cooking time (minutes):",
                  background=self.c_card).place(x=16, y=78)

        self.time_var = tk.IntVar(value=20)
        self.time_scale = ttk.Scale(card, from_=5, to=120, orient="horizontal",
                                    variable=self.time_var)
        self.time_scale.place(x=16, y=100, width=580)

        self.time_label = ttk.Label(card, text="20 min", background=self.c_card,
                                    foreground=self.c_accent, font=("Segoe UI", 12, "bold"))
        self.time_label.place(x=606, y=98)

        def update_time_label(*_):
            self.time_label.config(text=f"{int(self.time_var.get())} min")
        self.time_var.trace_add("write", update_time_label)

        # ---- Buttons bar aligned to the right, with extra spacing below slider ----
        button_bar = ttk.Frame(card, style="Card.TFrame")
        button_bar.place(relx=1.0, x=-16, y=130, anchor="ne")

        self.btn_gen = ttk.Button(button_bar, text="Generate", style="Accent.TButton",
                                  command=self.generate)
        self.btn_gen.pack(side="left", padx=(0, 8))

        self.btn_surprise = ttk.Button(button_bar, text="Surprise Me 🎲", style="Accent.TButton",
                                       command=self.surprise)
        self.btn_surprise.pack(side="left")

    # ---------- Output ----------
    def _build_output(self):
        card = ttk.Frame(self, style="Card.TFrame")
        card.place(relx=0.5, rely=0.48, anchor="n", relwidth=0.94, relheight=0.48)

        self.mode_label = ttk.Label(card, text="", background=self.c_card,
                                    foreground=self.c_text)
        self.mode_label.pack(anchor="w", padx=12, pady=(10, 0))

        container = ttk.Frame(card, style="Card.TFrame")
        container.pack(fill="both", expand=True, padx=12, pady=10)

        self.text = tk.Text(container, wrap="word", font=("Segoe UI", 11),
                            bg="white", fg=self.c_text, relief="flat",
                            padx=12, pady=12, highlightthickness=1,
                            highlightbackground=self.c_accent2)
        self.text.configure(state="disabled")
        self.text.pack(fill="both", expand=True)

    # ---------- Helpers ----------
    def _clear_field_and_output(self):
        self.ing_entry.delete(0, "end")
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")
        self.mode_label.config(text="")

    def _show_text(self, s: str, mode_text: str = ""):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", s)
        self.text.configure(state="disabled")
        self.mode_label.config(text=mode_text)

    # ---------- Add Recipe Dialog ----------
    def add_recipe_dialog(self):
        win = tk.Toplevel(self)
        win.title("Add New Recipe")
        win.geometry("440x560")
        win.configure(bg=self.c_card)
        win.transient(self)
        win.grab_set()

        def make_label(text, pady=(10, 0)):
            tk.Label(win, text=text, bg=self.c_card, fg=self.c_text).pack(anchor="w", padx=12, pady=pady)

        make_label("Recipe Name:")
        name_var = tk.Entry(win, width=44)
        name_var.pack(padx=12)

        make_label("Minutes:")
        mins_var = tk.Entry(win, width=12)
        mins_var.pack(padx=12)

        make_label("Ingredients (comma-separated):")
        ing_var = tk.Entry(win, width=44)
        ing_var.pack(padx=12)

        make_label("Steps (one per line):")
        steps_var = scrolledtext.ScrolledText(win, width=44, height=8, wrap="word")
        steps_var.pack(padx=12)

        make_label("Area (e.g., Italian):")
        area_var = tk.Entry(win, width=44)
        area_var.pack(padx=12)

        make_label("Category (e.g., Pasta):")
        cat_var = tk.Entry(win, width=44)
        cat_var.pack(padx=12)

        def save_new_recipe():
            try:
                name = name_var.get().strip()
                minutes = int(mins_var.get().strip())
                ings = [i.strip().lower() for i in ing_var.get().split(",") if i.strip()]
                steps = [s.strip() for s in steps_var.get("1.0", "end").split("\n") if s.strip()]
                area = area_var.get().strip()
                cat = cat_var.get().strip()

                if not name or not ings or minutes <= 0:
                    messagebox.showerror("Error", "Please fill in name, valid minutes (>0), and at least one ingredient.")
                    return

                new_recipe = {
                    "name": name,
                    "minutes": minutes,
                    "ingredients": ings,
                    "steps": steps if steps else ["(Add steps)"],
                    "area": area,
                    "category": cat
                }

                # Append to JSON file (create if missing)
                recipes = []
                if os.path.exists(LOCAL_DB_PATH):
                    recipes = load_local_db()
                recipes.append(new_recipe)
                with open(LOCAL_DB_PATH, "w", encoding="utf-8") as f:
                    json.dump(recipes, f, indent=2)

                # Reload app recipes
                self.local_recipes = load_local_db()
                self.local_ingredients = all_local_ingredients(self.local_recipes) if self.local_recipes else set()

                messagebox.showinfo("Success", f"Recipe '{name}' added!")
                win.destroy()

            except ValueError:
                messagebox.showerror("Error", "Minutes must be a valid number.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save recipe: {e}")

        ttk.Button(win, text="Save Recipe", style="Accent.TButton", command=save_new_recipe).pack(pady=16)

    # ---------- Core actions ----------
    def generate(self):
        if not self.local_recipes:
            messagebox.showinfo("No recipes loaded",
                                "Add recipes to recipes_local.json and restart.")
            return

        wanted_ing = normalize_tokens(self.ing_entry.get())
        max_mins = int(self.time_var.get())

        # Clear input after click
        self.ing_entry.delete(0, "end")

        if not wanted_ing:
            self._clear_field_and_output()
            messagebox.showinfo("Add ingredients", "Please enter at least one ingredient.")
            return

        # Shortage check: ingredient not present in any recipe
        missing = wanted_ing - self.local_ingredients
        if missing:
            self._clear_field_and_output()
            miss_str = ", ".join(sorted(m.title() for m in missing))
            messagebox.showwarning("shortage on recipes",
                                   f"We don't have any recipes with: {miss_str}")
            self.mode_label.config(text=f"shortage on recipes — missing: {miss_str}")
            return

        # TIME RULE: Only block if time < 12 minutes
        if max_mins < 12:
            self._clear_field_and_output()
            messagebox.showinfo("No recipe",
                                f"No recipe for {max_mins} min is available, please select ≥ 12 minutes.")
            return

        # Strict filter: must meet time AND include all requested ingredients
        candidates = [
            r for r in self.local_recipes
            if r["minutes"] <= max_mins and set(r["ingredients"]).issuperset(wanted_ing)
        ]

        if not candidates:
            self._clear_field_and_output()
            messagebox.showinfo("No recipe",
                                f"No recipe within {max_mins} min found that matches all ingredients.")
            return

        r = random.choice(candidates)
        header = f"Looking for: {', '.join(sorted(w.title() for w in wanted_ing))}  •  ≤ {max_mins} min\n\n"
        self._show_text(header + format_local_recipe(r), mode_text="Local match ✅")

    def surprise(self):
        if not self.local_recipes:
            messagebox.showinfo("No recipes loaded",
                                "Add recipes to recipes_local.json and restart.")
            return

        # Strict time-only random pick. Clears any prior text.
        self._clear_field_and_output()

        max_mins = int(self.time_var.get())

        # Same rule: only block if < 12
        if max_mins < 12:
            messagebox.showinfo("No recipe",
                                f"No recipe for {max_mins} min is available, please select ≥ 12 minutes.")
            return

        pool = [r for r in self.local_recipes if r["minutes"] <= max_mins]
        if not pool:
            messagebox.showinfo("No recipe",
                                f"No recipe found within {max_mins} min.")
            return

        r = random.choice(pool)
        self._show_text(format_local_recipe(r), mode_text="Surprise 🎲")


if __name__ == "__main__":
    App().mainloop()
