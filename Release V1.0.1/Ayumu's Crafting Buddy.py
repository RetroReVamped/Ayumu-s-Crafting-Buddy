# -----------------------------------------------------------------------------
#  Project: Ayumu's Crafting Buddy (or your project name)
#  Author: RetroReVamped
#  Copyright (c) 2025 RetroReVamped - All Rights Reserved
#
#  Permission is granted to use and modify this file for PERSONAL AND PRIVATE USE ONLY.
#  Redistribution, commercial use, or any form of distribution of this file or its
#  derivatives without explicit written permission from the author is strictly prohibited.
#
#  For full license terms, see the LICENSE file included with this project.
# -----------------------------------------------------------------------------
import os
import sys
import shutil
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

# =============================================================================
# Configuration & AppData bootstrap
# =============================================================================

APPDATA_DIR = os.path.join(os.getenv("APPDATA"), "AyumuCraftingBuddy")
CONFIG_FILE = os.path.join(APPDATA_DIR, "recipes.cfg")
IMAGE_FOLDER = os.path.join(APPDATA_DIR, "images")


def ensure_appdata_files():
    """
    Ensure AppData contains recipes.cfg and images.
    If running bundled, copy defaults from bundle; otherwise from source dir.
    """
    os.makedirs(APPDATA_DIR, exist_ok=True)
    os.makedirs(IMAGE_FOLDER, exist_ok=True)

    # Determine base path for defaults (PyInstaller/Nuitka bundle vs script dir)
    base_path = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    default_cfg = os.path.join(base_path, "recipes.cfg")
    default_images_dir = os.path.join(base_path, "images")

    # recipes.cfg
    if not os.path.exists(CONFIG_FILE) and os.path.exists(default_cfg):
        try:
            shutil.copy(default_cfg, CONFIG_FILE)
        except Exception as e:
            print(f"Warning: Could not copy recipes.cfg: {e}")

    # images (copy any missing images)
    if os.path.exists(default_images_dir):
        for fname in os.listdir(default_images_dir):
            src = os.path.join(default_images_dir, fname)
            dst = os.path.join(IMAGE_FOLDER, fname)
            if not os.path.exists(dst):
                try:
                    shutil.copy(src, dst)
                except Exception as e:
                    print(f"Warning: Could not copy image {fname}: {e}")


def open_appdata_folder():
    """Open the AppData folder in Explorer (Windows)."""
    try:
        if os.path.exists(APPDATA_DIR):
            subprocess.Popen(f'explorer "{APPDATA_DIR}"')
        else:
            messagebox.showwarning("Not Found", "The AppData folder does not exist yet.")
    except Exception as e:
        messagebox.showerror("Error", f"Could not open folder:\n{e}")


# Run once at import
ensure_appdata_files()

# =============================================================================
# Recipe file parsing
# =============================================================================

def load_recipes():
    """
    Parse recipes.cfg into two dicts:
    - raw_materials[name] = {cost, image, description}
    - craftable_items[name] = {ingredients, variations, cost, image, description}
    Variations are stored as: variations[var_key] = {label, ingredients, cost}
    """
    raw_materials, craftable_items = {}, {}
    section = "craftable"

    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"Config file '{CONFIG_FILE}' not found.")

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    i = 0
    while i < len(lines):
        raw_line = lines[i]
        stripped = raw_line.strip()

        # Section markers & comments
        if not stripped or stripped.startswith("#"):
            if "Raw Materials" in raw_line:
                section = "raw"
            elif "Craftable Items" in raw_line:
                section = "craftable"
            i += 1
            continue

        low = stripped.lower()
        if low.startswith("item:"):
            name = stripped.split(":", 1)[1].strip().lower()
            data = {"ingredients": {}, "variations": {}, "cost": 0, "image": "", "description": ""}
            target = raw_materials if section == "raw" else craftable_items
            target[name] = data
            i += 1
            current_variation = None

            # Consume fields for this item
            while i < len(lines):
                raw2 = lines[i]
                st = raw2.strip()
                l2 = st.lower()

                # End of item block?
                if not st:
                    i += 1
                    continue
                if l2.startswith("item:") or raw2.startswith("#") or "Raw Materials" in raw2 or "Craftable Items" in raw2:
                    break

                # Variation header like "Variation 1: 2 wood, 1 glue"
                if l2.startswith("variation"):
                    parts = st.split(":", 1)
                    var_label = parts[0].strip()               # e.g., "Variation 1"
                    var_key = var_label.lower()
                    var_ing = parts[1].strip() if len(parts) > 1 else ""
                    data["variations"][var_key] = {"label": var_label, "ingredients": {}, "cost": 0}
                    current_variation = var_key

                    # Inline ingredients on same line
                    if var_ing:
                        for chunk in var_ing.split(","):
                            chunk = chunk.strip()
                            if not chunk:
                                continue
                            qn = chunk.split(" ", 1)
                            if len(qn) == 2:
                                qty = int("".join([c for c in qn[0] if c.isdigit()]) or "0")
                                ing = qn[1].strip().lower()
                                data["variations"][var_key]["ingredients"][ing] = qty
                    i += 1
                    continue

                # Ingredients: on item or current variation
                if l2.startswith("ingredients:"):
                    ing_str = st.split(":", 1)[1].strip()
                    dest = data["ingredients"] if current_variation is None else data["variations"][current_variation]["ingredients"]
                    if ing_str:
                        for chunk in ing_str.split(","):
                            chunk = chunk.strip()
                            if not chunk:
                                continue
                            qn = chunk.split(" ", 1)
                            if len(qn) == 2:
                                qty = int("".join([c for c in qn[0] if c.isdigit()]) or "0")
                                ing = qn[1].strip().lower()
                                dest[ing] = dest.get(ing, 0) + qty
                    i += 1
                    continue

                # Cost: on item or current variation
                if l2.startswith("cost:"):
                    cstr = st.split(":", 1)[1].strip().replace(" eon", "")
                    digits = "".join(ch for ch in cstr if ch.isdigit())
                    val = int(digits) if digits else 0
                    if current_variation is not None:
                        data["variations"][current_variation]["cost"] = val
                    else:
                        data["cost"] = val
                    i += 1
                    continue

                # Image
                if l2.startswith("image:"):
                    data["image"] = st.split(":", 1)[1].strip()
                    i += 1
                    continue

                # Description (supports subsequent indented lines)
                if l2.startswith("description:"):
                    first = st.split(":", 1)[1].rstrip()
                    i += 1
                    extra = []
                    while i < len(lines):
                        look_raw = lines[i]
                        look_strip = look_raw.strip()
                        look_low = look_strip.lower()
                        if (
                            look_low.startswith(("item:", "variation", "ingredients:", "cost:", "image:", "description:"))
                            or look_raw.startswith("#")
                            or "Raw Materials" in look_raw
                            or "Craftable Items" in look_raw
                        ):
                            break
                        if look_raw.startswith((" ", "\t")):
                            extra.append(look_strip)
                            i += 1
                        else:
                            break
                    desc = (first + ("\n" + "\n".join(extra) if extra else "")).strip()
                    data["description"] = desc
                    continue

                i += 1
            continue

        i += 1

    return raw_materials, craftable_items


# =============================================================================
# Image helpers & UI utility
# =============================================================================

_loaded_images = {}


def get_placeholder(size=(120, 120)):
    """Simple gray placeholder for missing images."""
    key = f"placeholder_{size}"
    if key not in _loaded_images:
        img = Image.new("RGBA", size, (200, 200, 200, 255))
        _loaded_images[key] = ImageTk.PhotoImage(img)
    return _loaded_images[key]


def load_image_for_item(item, size=(120, 120)):
    """Resolve image by item name via craftable/raw dicts; returns PhotoImage."""
    img_file = ""
    if item in craftable_items:
        img_file = craftable_items[item].get("image", "")
    elif item in raw_materials:
        img_file = raw_materials[item].get("image", "")

    if not img_file:
        return get_placeholder(size)

    path = os.path.join(IMAGE_FOLDER, img_file)
    if os.path.exists(path):
        key = f"{path}_{size}"
        if key not in _loaded_images:
            pil = Image.open(path)
            pil.thumbnail(size, Image.LANCZOS)
            _loaded_images[key] = ImageTk.PhotoImage(pil)
        return _loaded_images[key]
    return get_placeholder(size)


def center_window(win, width=None, height=None):
    """Center a Tk/Toplevel on the screen."""
    win.update_idletasks()
    screen_w, screen_h = win.winfo_screenwidth(), win.winfo_screenheight()
    if width is None or height is None:
        win_w, win_h = win.winfo_reqwidth(), win.winfo_reqheight()
    else:
        win_w, win_h = width, height
    x = (screen_w // 2) - (win_w // 2)
    y = (screen_h // 2) - (win_h // 2)
    win.geometry(f"{win_w}x{win_h}+{x}+{y}")


def enable_hover_scroll(widget):
    """Allow wheel scrolling when hovering (Treeview/Text/Canvas)."""
    def _on_mousewheel(event):
        if isinstance(widget, (tk.Listbox, tk.Text, tk.Canvas, ttk.Treeview)):
            if event.delta:
                widget.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif event.num == 4:
                widget.yview_scroll(-1, "units")
            elif event.num == 5:
                widget.yview_scroll(1, "units")

    def _bind_hover(_):
        widget.bind_all("<MouseWheel>", _on_mousewheel)
        widget.bind_all("<Button-4>", _on_mousewheel)
        widget.bind_all("<Button-5>", _on_mousewheel)

    def _unbind_hover(_):
        widget.unbind_all("<MouseWheel>")
        widget.unbind_all("<Button-4>")
        widget.unbind_all("<Button-5>")

    widget.bind("<Enter>", _bind_hover)
    widget.bind("<Leave>", _unbind_hover)


# =============================================================================
# Tooltip system
# =============================================================================

_tooltip_win = None
_tooltip_after_id = None
_tooltip_owner_widget = None
_tooltip_owner_row = None


def _hide_tooltip():
    """Destroy current tooltip window if present."""
    global _tooltip_win
    if _tooltip_win:
        try:
            _tooltip_win.destroy()
        except Exception:
            pass
    _tooltip_win = None


def _show_tooltip_now(widget, text, x_root, y_root):
    """Render a small themed tooltip near pointer."""
    global _tooltip_win
    _hide_tooltip()
    tw = tk.Toplevel(widget)
    tw.wm_overrideredirect(True)
    tw.wm_attributes("-topmost", True)
    tw.wm_attributes("-alpha", 0.93)
    label = tk.Label(
        tw,
        text=text,
        bg="#1a1a1a",
        fg="#e0e0e0",
        justify="left",
        font=("Segoe UI", 10),
        relief="solid",
        bd=1,
        padx=8,
        pady=5,
        wraplength=400,
    )
    label.pack()
    tw.geometry(f"+{x_root + 20}+{y_root + 18}")
    _tooltip_win = tw


def schedule_tooltip(widget, row_id, text, x_root, y_root, delay=420):
    """Schedule tooltip for a specific widget/row to avoid flicker between rows."""
    global _tooltip_after_id, _tooltip_owner_widget, _tooltip_owner_row
    if _tooltip_after_id and (_tooltip_owner_widget != widget or _tooltip_owner_row != row_id):
        try:
            _tooltip_owner_widget.after_cancel(_tooltip_after_id)
        except Exception:
            pass
        _tooltip_after_id = None
    _tooltip_owner_widget = widget
    _tooltip_owner_row = row_id
    _tooltip_after_id = widget.after(delay, lambda: _show_tooltip_now(widget, text, x_root, y_root))


def cancel_scheduled_tooltip():
    """Cancel pending tooltip and hide active one."""
    global _tooltip_after_id, _tooltip_owner_widget, _tooltip_owner_row
    if _tooltip_after_id and _tooltip_owner_widget:
        try:
            _tooltip_owner_widget.after_cancel(_tooltip_after_id)
        except Exception:
            pass
    _tooltip_after_id = None
    _tooltip_owner_widget = None
    _tooltip_owner_row = None
    _hide_tooltip()


# =============================================================================
# Global state
# =============================================================================

raw_materials, craftable_items = load_recipes()
selected_variations = {}       # item -> [var_keys]
unresolved_queue = []          # deferred choices for deeper varied children
deferred_items = set()         # parents awaiting varied child selection
current_raw_totals = {}        # aggregated raw materials
current_total_cost = 0
current_root_item = None
current_root_node_id = None
node_ids_by_item = {}          # item -> [tree node ids]


# =============================================================================
# Variation helpers & deferral queue
# =============================================================================

def aggregate_from_variations(item, var_keys):
    """Sum ingredients and costs across selected variations for an item."""
    ingredients, total_cost = {}, 0
    for vk in var_keys:
        var = craftable_items[item]["variations"].get(vk, {})
        for ing, qty in var.get("ingredients", {}).items():
            ingredients[ing] = ingredients.get(ing, 0) + qty
        total_cost += var.get("cost", 0)
    return ingredients, total_cost


def is_aggregated(item):
    """True if an item currently has explicit variation selections."""
    return item in selected_variations and isinstance(selected_variations[item], list) and len(selected_variations[item]) > 0


def enqueue_unresolved_from_selection(parent_item, selections_for_parent):
    """
    Queue varied children required by selected variations of parent_item.
    Each selection represents one unit of the parent; we don't multiply here.
    """
    for var_key in selections_for_parent:
        var = craftable_items.get(parent_item, {}).get("variations", {}).get(var_key, {})
        for sub_ing, sub_qty in var.get("ingredients", {}).items():
            if sub_ing in craftable_items and craftable_items[sub_ing].get("variations"):
                deferred_items.add(parent_item)
                unresolved_queue.append({
                    "item": sub_ing,
                    "qty": sub_qty,
                    "parent": parent_item,
                    "parent_mult": 1,
                })


def process_unresolved_queue():
    """Show next queued popup (if any) for deeper varied children."""
    if unresolved_queue:
        task = unresolved_queue.pop(0)
        show_multi_variation_popup(
            root_item_context=current_root_item,
            ingredients_needed={task["item"]: task["qty"]},
            append=True,
            append_parent=task["parent"],
            append_multiplier=task.get("parent_mult", 1),
        )


def enqueue_variant_children_for_normal_items(parent_item, parent_multiplier=1):
    """
    For normal craftables (no variations), find sub-items that DO have variations,
    defer the parent, and queue popups so quantities reflect parent_multiplier.
    """
    if parent_item not in craftable_items:
        return
    if craftable_items[parent_item].get("variations"):
        return  # handled elsewhere

    ingredients = craftable_items[parent_item].get("ingredients", {})
    for ing, qty in ingredients.items():
        if ing in craftable_items and craftable_items[ing].get("variations"):
            if parent_item != current_root_item:
                deferred_items.add(parent_item)
                unresolved_queue.append({
                    "item": ing,
                    "qty": qty * parent_multiplier,
                    "parent": parent_item,
                    "parent_mult": parent_multiplier,
                })
        elif ing in craftable_items:
            enqueue_variant_children_for_normal_items(ing, parent_multiplier * qty)


# =============================================================================
# Expansion & cost computation
# =============================================================================

def get_ingredients_for_item(item):
    """Return (ingredients, cost) for item, honoring current aggregation if any."""
    if item in craftable_items:
        r = craftable_items[item]
        if is_aggregated(item):
            return aggregate_from_variations(item, selected_variations[item])
        return r.get("ingredients", {}), r.get("cost", 0)
    elif item in raw_materials:
        return {}, raw_materials[item].get("cost", 0)
    return {}, 0


def get_base_ingredients(item, collected=None, multiplier=1):
    """Expand item into base raw materials (recursively)."""
    if collected is None:
        collected = {}
    if item in raw_materials:
        collected[item] = collected.get(item, 0) + multiplier
        return collected
    if item not in craftable_items or item in deferred_items:
        return collected

    ingredients, _ = get_ingredients_for_item(item)
    if is_aggregated(item):
        for ing, qty in ingredients.items():
            get_base_ingredients(ing, collected, qty)
        return collected

    for ing, qty in ingredients.items():
        get_base_ingredients(ing, collected, multiplier * qty)
    return collected


def calculate_total_cost(item, multiplier=1):
    """Compute total cost including children; skip deferred parents."""
    if item in deferred_items:
        return 0
    if item in raw_materials:
        return raw_materials[item].get("cost", 0) * multiplier
    if item not in craftable_items:
        return 0

    ingredients, cost = get_ingredients_for_item(item)
    if is_aggregated(item):
        num = len(selected_variations[item])
        per_item_cost = round(cost / num, 2) if num else cost
        total = per_item_cost * num
        for ing, qty in ingredients.items():
            total += calculate_total_cost(ing, qty)
        return total

    total = cost * multiplier
    for ing, qty in ingredients.items():
        if is_aggregated(ing):
            total += calculate_total_cost(ing, qty)
        else:
            total += calculate_total_cost(ing, qty * multiplier)
    return total


def build_tree(item, parent, tree, multiplier=1):
    """Insert item subtree into a ttk.Treeview; returns node id."""
    if item in raw_materials:
        cost = raw_materials[item].get("cost", 0)
        txt = f"{multiplier} × {item.title()}" + (f" (Cost: {cost} eon)" if cost else "")
        nid = tree.insert(parent, "end", text=txt)
        node_ids_by_item.setdefault(item, []).append(nid)
        return nid

    if item not in craftable_items:
        return None

    ingredients, cost = get_ingredients_for_item(item)
    aggregated = is_aggregated(item)
    per_cost = (round(cost / len(selected_variations[item]), 2) if aggregated and selected_variations[item] else cost)
    txt = f"{multiplier} × {item.title()}" + (f" (Cost: {per_cost} eon)" if per_cost else "")
    nid = tree.insert(parent, "end", text=txt)
    node_ids_by_item.setdefault(item, []).append(nid)

    if item in deferred_items:
        return nid

    for ing, qty in ingredients.items():
        next_mult = qty if aggregated else qty * multiplier
        build_tree(ing, nid, tree, next_mult)
    return nid


# =============================================================================
# Overrides-based expansion (used for deferred appends)
# =============================================================================

def get_ingredients_with_overrides(item, overrides):
    """Like get_ingredients_for_item, but allow temporary override selections."""
    if item in craftable_items:
        if item in overrides:
            return aggregate_from_variations(item, overrides[item])
        if is_aggregated(item):
            return aggregate_from_variations(item, selected_variations[item])
        r = craftable_items[item]
        return r.get("ingredients", {}), r.get("cost", 0)
    elif item in raw_materials:
        return {}, raw_materials[item].get("cost", 0)
    return {}, 0


def expand_to_raw_with_overrides(item, overrides, collected=None, multiplier=1):
    """Expand to raw materials while honoring overrides for this append operation."""
    if collected is None:
        collected = {}
    if item in raw_materials:
        collected[item] = collected.get(item, 0) + multiplier
        return collected
    if item not in craftable_items:
        return collected

    ingredients, _ = get_ingredients_with_overrides(item, overrides)
    aggregated_current = (item in overrides) or is_aggregated(item)

    if aggregated_current:
        for ing, qty in ingredients.items():
            expand_to_raw_with_overrides(ing, overrides, collected, qty)
        return collected

    for ing, qty in ingredients.items():
        expand_to_raw_with_overrides(ing, overrides, collected, multiplier * qty)
    return collected


def cost_with_overrides(item, overrides, multiplier=1):
    """Cost calculation that respects override selections for this append."""
    if item in raw_materials:
        return raw_materials[item].get("cost", 0) * multiplier
    if item not in craftable_items:
        return 0

    ingredients, cost = get_ingredients_with_overrides(item, overrides)
    aggregated_current = (item in overrides) or is_aggregated(item)

    if aggregated_current:
        total = cost
        for ing, qty in ingredients.items():
            total += cost_with_overrides(ing, overrides, qty)
        return total

    total = cost * multiplier
    for ing, qty in ingredients.items():
        total += cost_with_overrides(ing, overrides, qty * multiplier)
    return total


def build_tree_with_overrides(item, parent, tree, overrides, multiplier=1):
    """Insert subtree into Treeview, factoring override aggregation state."""
    if item in raw_materials:
        cost = raw_materials[item].get("cost", 0)
        txt = f"{multiplier} × {item.title()}" + (f" (Cost: {cost} eon)" if cost else "")
        nid = tree.insert(parent, "end", text=txt)
        node_ids_by_item.setdefault(item, []).append(nid)
        return nid

    if item not in craftable_items:
        return None

    ingredients, cost = get_ingredients_with_overrides(item, overrides)
    aggregated_current = (item in overrides) or is_aggregated(item)
    selected_count = len(overrides.get(item, selected_variations.get(item, [])))
    per_cost = (round(cost / selected_count, 2) if aggregated_current and selected_count else cost)

    txt = f"{multiplier} × {item.title()}" + (f" (Cost: {per_cost} eon)" if per_cost else "")
    nid = tree.insert(parent, "end", text=txt)
    node_ids_by_item.setdefault(item, []).append(nid)

    for ing, qty in ingredients.items():
        next_mult = qty if aggregated_current else qty * multiplier
        build_tree_with_overrides(ing, nid, tree, overrides, next_mult)
    return nid


def add_children_with_overrides(item, parent_node, overrides, multiplier=1):
    """Append children nodes for 'item' using overrides and multiplier."""
    ingredients, _ = get_ingredients_with_overrides(item, overrides)
    aggregated_current = (item in overrides) or is_aggregated(item)
    for ing, qty in ingredients.items():
        next_mult = qty if aggregated_current else qty * multiplier
        build_tree_with_overrides(ing, parent_node, recipe_tree, overrides, next_mult)


# =============================================================================
# Output helpers (summary panel)
# =============================================================================

def set_summary_from_totals():
    """Refresh summary text from current_raw_totals/current_total_cost."""
    summary_text_widget.config(state="normal")
    summary_text_widget.delete("1.0", tk.END)
    summary_text_widget.insert(tk.END, "📜 Raw ingredients:\n")
    for k in sorted(current_raw_totals.keys()):
        v = current_raw_totals[k]
        line = f" - {v} × {k.title()}"
        cost_k = raw_materials.get(k, {}).get("cost", 0)
        if cost_k:
            line += f" (Cost: {cost_k} eon)"
        summary_text_widget.insert(tk.END, line + "\n")
    summary_text_widget.insert(tk.END, f"\n💰 Total cost: {current_total_cost} eon")
    summary_text_widget.config(state="disabled")


def merge_raw_totals(additional_dict):
    for k, v in additional_dict.items():
        current_raw_totals[k] = current_raw_totals.get(k, 0) + v


# =============================================================================
# GUI: navigate home/recipes & popups
# =============================================================================

def show_home():
    """Return to home list; reset per-session transient state."""
    global selected_variations, unresolved_queue, deferred_items
    global current_raw_totals, current_total_cost, current_root_item, current_root_node_id, node_ids_by_item
    selected_variations = {}
    unresolved_queue = []
    deferred_items = set()
    current_raw_totals = {}
    current_total_cost = 0
    current_root_item = None
    current_root_node_id = None
    node_ids_by_item = {}

    recipe_frame.pack_forget()
    home_frame.pack(fill="both", expand=True)

    search_entry.delete(0, tk.END)
    search_entry.insert(0, "Search...")
    search_entry.config(fg="gray")
    update_tree()


def show_recipe(item):
    """Open a recipe view for item (build tree, totals, and process queued popups)."""
    global current_raw_totals, current_total_cost, current_root_item, current_root_node_id, node_ids_by_item
    current_root_item = item
    node_ids_by_item = {}

    # Detect normal craftables with varied children and queue selection popups
    enqueue_variant_children_for_normal_items(current_root_item)

    home_frame.pack_forget()
    recipe_frame.pack(fill="both", expand=True)
    selected_item.set(item)

    # Image + tooltip
    img = load_image_for_item(item, size=(120, 120))
    if img:
        image_label.config(image=img, text="")
        image_label.image = img
    else:
        image_label.config(image="", text="No Image")
    desc = craftable_items.get(item, {}).get("description", "") or raw_materials.get(item, {}).get("description", "")
    cancel_scheduled_tooltip()
    image_label.tooltip_desc = desc if desc else ""

    # Build tree + compute summary
    for c in recipe_tree.get_children():
        recipe_tree.delete(c)
    current_root_node_id = build_tree(item, "", recipe_tree, multiplier=1)
    base = get_base_ingredients(item, collected=None, multiplier=1)
    total = calculate_total_cost(item, multiplier=1)
    current_raw_totals = base
    current_total_cost = total
    set_summary_from_totals()

    # Handle any deferred varied children
    process_unresolved_queue()


def append_item_subtree_with_overrides(append_parent, overrides, multiplier=1):
    """
    After a varied child selection, append the parent's subtree and update totals.
    """
    global current_total_cost
    if append_parent in deferred_items:
        deferred_items.discard(append_parent)

    parent_nodes = node_ids_by_item.get(append_parent, [])
    parent_node = parent_nodes[-1] if parent_nodes else current_root_node_id

    add_children_with_overrides(append_parent, parent_node, overrides, multiplier=multiplier)

    add_base = expand_to_raw_with_overrides(append_parent, overrides, collected=None, multiplier=multiplier)
    add_cost = cost_with_overrides(append_parent, overrides, multiplier=multiplier)
    merge_raw_totals(add_base)
    current_total_cost += add_cost
    set_summary_from_totals()


# ---- Popup: choose variations ------------------------------------------------

def _bind_mousewheel_to(canvas, top):
    """Bind wheel scrolling for a scrollable popup."""
    def on_wheel(event):
        if event.delta:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def bind_all(_=None):
        top.bind_all("<MouseWheel>", on_wheel)
        top.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        top.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

    def unbind_all(_=None):
        try:
            top.unbind_all("<MouseWheel>")
            top.unbind_all("<Button-4>")
            top.unbind_all("<Button-5>")
        except Exception:
            pass

    canvas.bind("<Enter>", bind_all)
    canvas.bind("<Leave>", unbind_all)
    top.bind("<FocusIn>", bind_all)
    top.bind("<FocusOut>", unbind_all)
    top.bind("<Destroy>", unbind_all)


def show_multi_variation_popup(root_item_context, ingredients_needed, append=False, append_parent=None, append_multiplier=1):
    """
    Multi-select popup to choose specific variations for one or more varied sub-items.
    If append=True, apply choices to append_parent and merge into current view.
    """
    top = tk.Toplevel(root)
    try:
        top.iconbitmap(default=ICON_PATH)
    except Exception:
        pass
    top.title(f"Choose variations for {root_item_context.title()}")
    top.grab_set()

    # Initial size; adjust later based on content
    screen_h = root.winfo_screenheight()
    h = min(600, max(400, int(screen_h * 0.45)))
    default_w = 300
    center_window(top, default_w, h)

    # Scrollable content
    canvas = tk.Canvas(top, borderwidth=0, highlightthickness=0)
    frame = tk.Frame(canvas)
    vscroll = tk.Scrollbar(top, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vscroll.set)
    vscroll.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    canvas.create_window((0, 0), window=frame, anchor="nw")
    frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    _bind_mousewheel_to(canvas, top)

    # Build groups (one group per needed varied ingredient)
    group_vars = {}
    for ingr_name, qty in ingredients_needed.items():
        if ingr_name in craftable_items and craftable_items[ingr_name].get("variations"):
            variations = craftable_items[ingr_name]["variations"]
            tk.Label(frame, text=f"How would you like to make your {qty} {ingr_name.title()}?",
                     font=("Arial", 11, "bold")).pack(pady=(10, 4), anchor="w")
            group_vars[ingr_name] = []
            for i in range(qty):
                tk.Label(frame, text=f"{i+1}", font=("Arial", 10, "italic")).pack(anchor="w", padx=10)
                var_list = []
                for var_key, var_data in variations.items():
                    text = ", ".join([f"{v_qty} {v_name.title()}" for v_name, v_qty in var_data.get("ingredients", {}).items()])
                    text += f" + {var_data.get('cost', 0)} eons"
                    state = tk.BooleanVar(value=False)
                    cb = tk.Checkbutton(frame, text=text, variable=state)

                    def enforce_one(v=state, group=var_list):
                        if v.get():
                            for other in group:
                                if other is not v:
                                    other.set(False)

                    state.trace_add("write", lambda *args, v=state, group=var_list: enforce_one(v, group))
                    cb.pack(anchor="w", padx=20)
                    var_list.append(state)
                group_vars[ingr_name].append(var_list)

    # Resize to fit content (within limits)
    frame.update_idletasks()
    needed_w = frame.winfo_reqwidth() + 20
    needed_h = frame.winfo_reqheight() + 50
    max_h = min(600, int(screen_h * 0.7))
    final_h = max(80, min(needed_h, max_h))
    final_w = max(default_w, needed_w)
    top.geometry(f"{final_w}x{final_h}")
    center_window(top, final_w, final_h)

    def on_submit():
        if not group_vars:
            top.destroy()
            if append and append_parent:
                append_item_subtree_with_overrides(append_parent, overrides={}, multiplier=append_multiplier)
            else:
                show_recipe(root_item_context)
            process_unresolved_queue()
            return

        # Collect chosen variation keys per varied ingredient
        local_sel = {}
        for ingr_name, groups in group_vars.items():
            chosen_keys = []
            for var_list in groups:
                chosen_key = None
                for idx, st in enumerate(var_list):
                    if st.get():
                        chosen_key = list(craftable_items[ingr_name]["variations"].keys())[idx]
                        break
                if not chosen_key:
                    messagebox.showwarning("Incomplete", f"Please choose a variation for {ingr_name.title()}.")
                    return
                chosen_keys.append(chosen_key)
            local_sel[ingr_name] = chosen_keys

        # Persist selections & enqueue any deeper varied children
        for name, vlist in local_sel.items():
            selected_variations.setdefault(name, [])
            selected_variations[name].extend(vlist)
            enqueue_unresolved_from_selection(name, vlist)

        top.destroy()
        if append and append_parent:
            overrides = {k: v for k, v in local_sel.items() if k != append_parent}
            append_item_subtree_with_overrides(append_parent, overrides, multiplier=append_multiplier)
        else:
            show_recipe(root_item_context)
        process_unresolved_queue()

    tk.Button(frame, text="Submit", command=on_submit).pack(pady=10)
    top.wait_window(top)


# =============================================================================
# Editing: add/remove items & write-back
# =============================================================================

def write_config_from_memory():
    """Write current in-memory structures back to recipes.cfg."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        f.write("# ---------------- Raw Materials ----------------\n")
        for name in sorted(raw_materials.keys()):
            data = raw_materials[name]
            f.write(f"Item: {name.title()}\n")
            if data.get("image"):
                f.write(f"Image: {data['image']}\n")
            if data.get("cost"):
                f.write(f"Cost: {data['cost']} eon\n")
            f.write("\n")

        f.write("# ---------------- Craftable Items ----------------\n")
        for name in sorted(craftable_items.keys()):
            data = craftable_items[name]
            f.write(f"Item: {name.title()}\n")
            if data.get("ingredients"):
                ings = ", ".join([f"{v} {k.title()}" for k, v in data["ingredients"].items()])
                f.write(f"Ingredients: {ings}\n")
            if data.get("variations"):
                for vkey in sorted(data["variations"].keys()):
                    vdata = data["variations"][vkey]
                    label = vdata.get("label", vkey.title())
                    ing_str = ", ".join([f"{v2} {k2.title()}" for k2, v2 in vdata.get("ingredients", {}).items()])
                    f.write(f"{label}: {ing_str}\n")
                    if vdata.get("cost"):
                        f.write(f"Cost: {vdata['cost']} eon\n")
            if data.get("cost"):
                f.write(f"Cost: {data['cost']} eon\n")
            if data.get("image"):
                f.write(f"Image: {data['image']}\n")
            desc = data.get("description", "")
            if desc:
                lines = desc.split("\n")
                f.write(f"Description: {lines[0].strip()}\n")
                for more in lines[1:]:
                    f.write(f"\t{more.strip()}\n")
            f.write("\n")


def delete_item_from_config(item_name):
    """Remove item from memory + file and refresh UI."""
    global raw_materials, craftable_items
    if item_name in craftable_items:
        del craftable_items[item_name]
    elif item_name in raw_materials:
        del raw_materials[item_name]
    write_config_from_memory()
    raw_materials, craftable_items = load_recipes()
    update_tree()


def open_remove_item_window():
    """Window listing all items with quick delete buttons."""
    top = tk.Toplevel(root)
    top.title("Remove Items")
    try:
        top.iconbitmap(default=ICON_PATH)
    except Exception:
        pass

    fixed_h, default_w = 500, 300
    center_window(top, default_w, fixed_h)
    top.grab_set()

    canvas = tk.Canvas(top, borderwidth=0, highlightthickness=0)
    frame = tk.Frame(canvas)
    vscroll = tk.Scrollbar(top, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vscroll.set)
    vscroll.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    canvas.create_window((0, 0), window=frame, anchor="nw")
    frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    _bind_mousewheel_to(canvas, top)

    all_items = sorted(list(raw_materials.keys()) + list(craftable_items.keys()))
    for item in all_items:
        img = load_image_for_item(item, size=(40, 40))
        row = tk.Frame(frame)
        row.pack(fill="x", pady=2, padx=6)
        tk.Label(row, image=img).pack(side="left")
        tk.Label(row, text=item.title(), font=("Arial", 10, "bold")).pack(side="left", padx=10)

        def on_click(it=item):
            if messagebox.askyesno("Confirm Deletion", f"Delete '{it.title()}'?"):
                delete_item_from_config(it)
                messagebox.showinfo("Deleted", f"'{it.title()}' has been removed.")
                top.destroy()

        tk.Button(row, text="🗑", command=on_click, bg="#c0392b", fg="white", width=2).pack(side="right", padx=5)

    # Expand width if needed
    frame.update_idletasks()
    needed_w = frame.winfo_reqwidth() + 20
    if needed_w > default_w:
        top.geometry(f"{needed_w}x{fixed_h}")
        center_window(top, needed_w, fixed_h)


# ---- Add item (entry points) -----------------------------------------------

def open_add_item_choice():
    """Prompt: add Raw Material or Craftable Item."""
    top = tk.Toplevel(root)
    try:
        top.iconbitmap(default=ICON_PATH)
    except Exception:
        pass
    top.title("Add Item")
    center_window(top, 350, 110)
    top.grab_set()

    tk.Label(top, text="Is this a Raw Material or a Craftable Item?", font=("Segoe UI", 11, "bold")).pack(padx=10, pady=10)

    btns = tk.Frame(top)
    btns.pack(pady=8)
    tk.Button(btns, text="Raw Material", width=16, command=lambda: (top.destroy(), open_add_raw_popup())).pack(side="left", padx=6)
    tk.Button(btns, text="Craftable Item", width=16, command=lambda: (top.destroy(), open_add_craftable_entry())).pack(side="left", padx=6)


def open_add_raw_popup():
    """Form for adding a raw material."""
    top = tk.Toplevel(root)
    try:
        top.iconbitmap(default=ICON_PATH)
    except Exception:
        pass
    top.title("Add Raw Material")
    center_window(top, 350, 200)
    top.grab_set()

    frm = tk.Frame(top)
    frm.pack(padx=10, pady=10)
    tk.Label(frm, text="Item name:").grid(row=0, column=0, sticky="e", padx=6, pady=4)
    tk.Label(frm, text="Cost:").grid(row=1, column=0, sticky="e", padx=6, pady=4)
    tk.Label(frm, text="Image name:").grid(row=2, column=0, sticky="e", padx=6, pady=4)

    name_var, cost_var, img_var = tk.StringVar(), tk.StringVar(), tk.StringVar()
    tk.Entry(frm, textvariable=name_var, width=28).grid(row=0, column=1, pady=4)
    tk.Entry(frm, textvariable=cost_var, width=28).grid(row=1, column=1, pady=4)
    tk.Entry(frm, textvariable=img_var, width=28).grid(row=2, column=1, pady=4)

    info = (
        'Place images in the "images" folder (include extension, e.g. "item.png").\n'
        "Most raw materials have no cost; leave empty if none."
    )
    tk.Label(top, text=info, justify="left", wraplength=360).pack(padx=10, pady=(0, 8))

    def submit():
        global raw_materials, craftable_items
        name = name_var.get().strip().lower()
        if not name:
            messagebox.showwarning("Missing", "Item name is required.")
            return
        ctext = cost_var.get().strip()
        cost = int("".join([c for c in ctext if c.isdigit()])) if ctext else 0
        img = img_var.get().strip()

        raw_materials[name] = {"ingredients": {}, "variations": {}, "cost": cost, "image": img, "description": ""}
        write_config_from_memory()
        raw_materials, craftable_items = load_recipes()
        update_tree()
        top.destroy()

    tk.Button(top, text="Add", command=submit).pack(pady=8)


def open_add_craftable_entry():
    """Ask whether the craftable has multiple variations."""
    top = tk.Toplevel(root)
    try:
        top.iconbitmap(default=ICON_PATH)
    except Exception:
        pass
    top.title("Craftable: Variations?")
    center_window(top, 350, 100)
    top.grab_set()

    tk.Label(top, text="Does this item have multiple crafting recipes?", font=("Segoe UI", 11, "bold")).pack(padx=10, pady=10)

    btns = tk.Frame(top)
    btns.pack(pady=8)
    tk.Button(btns, text="Yes", width=12, command=lambda: (top.destroy(), open_add_craftable_variations_popup())).pack(side="left", padx=6)
    tk.Button(btns, text="No", width=12, command=lambda: (top.destroy(), open_add_craftable_single_popup())).pack(side="left", padx=6)


def open_add_craftable_single_popup():
    """Form for adding a single-recipe craftable."""
    top = tk.Toplevel(root)
    try:
        top.iconbitmap(default=ICON_PATH)
    except Exception:
        pass
    top.title("Add Craftable (Single Recipe)")
    center_window(top, 350, 520)
    top.grab_set()

    # Scrollable form
    canvas = tk.Canvas(top, borderwidth=0, highlightthickness=0)
    frame = tk.Frame(canvas)
    vscroll = tk.Scrollbar(top, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vscroll.set)
    vscroll.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    canvas.create_window((0, 0), window=frame, anchor="nw")
    frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    _bind_mousewheel_to(canvas, top)

    # Fields
    tk.Label(frame, text="Item Name:").pack(anchor="w", padx=10, pady=(10, 4))
    name_var = tk.StringVar()
    tk.Entry(frame, textvariable=name_var, width=34).pack(padx=10, pady=(0, 6))

    tk.Label(frame, text="Ingredients (# Item, # Item, ...):").pack(anchor="w", padx=10, pady=(6, 4))
    ing_var = tk.StringVar()
    tk.Entry(frame, textvariable=ing_var, width=34).pack(padx=10, pady=(0, 6))

    tk.Label(frame, text="Cost (eon):").pack(anchor="w", padx=10, pady=(6, 4))
    cost_var = tk.StringVar()
    tk.Entry(frame, textvariable=cost_var, width=20).pack(padx=10, pady=(0, 6))

    tk.Label(frame, text="Image:").pack(anchor="w", padx=10, pady=(6, 4))
    img_var = tk.StringVar()
    tk.Entry(frame, textvariable=img_var, width=34).pack(padx=10, pady=(0, 6))

    tk.Label(frame, text="Description:").pack(anchor="w", padx=10, pady=(6, 4))
    desc_txt = tk.Text(frame, width=36, height=6)
    desc_txt.pack(padx=10, pady=(0, 8))

    info = (
        'Images belong in "images" (include extension). '
        'Cost is the crafting cost if any. '
        'Ingredients use "# Item, # Item, ..." (case matters). '
        "Description supports multiple lines."
    )
    tk.Label(frame, text=info, justify="left", wraplength=360).pack(padx=10, pady=(0, 8))

    def submit():
        global raw_materials, craftable_items
        name = name_var.get().strip().lower()
        if not name:
            messagebox.showwarning("Missing", "Item name is required.")
            return

        # Parse ingredients text -> dict
        ingredients = {}
        ings_text = ing_var.get().strip()
        if ings_text:
            parts = [p.strip() for p in ings_text.split(",") if p.strip()]
            for p in parts:
                qn = p.split(" ", 1)
                if len(qn) == 2:
                    qty = int("".join([c for c in qn[0] if c.isdigit()]) or "0")
                    ing = qn[1].strip().lower()
                    ingredients[ing] = ingredients.get(ing, 0) + qty

        c = cost_var.get().strip()
        cost = int("".join([d for d in c if d.isdigit()])) if c else 0
        img = img_var.get().strip()
        desc = desc_txt.get("1.0", "end").strip()

        craftable_items[name] = {
            "ingredients": ingredients,
            "variations": {},
            "cost": cost,
            "image": img,
            "description": desc,
        }
        write_config_from_memory()
        raw_materials, craftable_items = load_recipes()
        update_tree()
        top.destroy()

    tk.Button(frame, text="Add", command=submit).pack(pady=10)


def open_add_craftable_variations_popup():
    """Prompt for number of variations before opening the full form."""
    t0 = tk.Toplevel(root)
    try:
        t0.iconbitmap(ICON_PATH)
    except Exception:
        pass
    t0.title("How many variations?")
    center_window(t0, 300, 100)
    t0.grab_set()

    tk.Label(t0, text="How many variations does it have?").pack(padx=10, pady=(10, 4))
    vcount = tk.StringVar()
    tk.Entry(t0, textvariable=vcount, width=10).pack(padx=10, pady=(0, 8))

    def go_next():
        try:
            n = int(vcount.get().strip())
        except Exception:
            messagebox.showwarning("Invalid", "Enter a valid number.")
            return
        if n <= 0:
            messagebox.showwarning("Invalid", "Enter a positive number.")
            return
        t0.destroy()
        open_add_craftable_variations_form(n)

    tk.Button(t0, text="Submit", command=go_next).pack(pady=6)


def open_add_craftable_variations_form(n_variations):
    """Form for adding a craftable item that has multiple variations."""
    top = tk.Toplevel(root)
    try:
        top.iconbitmap(default=ICON_PATH)
    except Exception:
        pass
    top.title("Add Craftable (Variations)")
    center_window(top, 350, 650)
    top.grab_set()

    canvas = tk.Canvas(top, borderwidth=0, highlightthickness=0)
    frame = tk.Frame(canvas)
    vscroll = tk.Scrollbar(top, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vscroll.set)
    vscroll.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    canvas.create_window((0, 0), window=frame, anchor="nw")
    frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    _bind_mousewheel_to(canvas, top)

    tk.Label(frame, text="Item name:").pack(anchor="w", padx=10, pady=(10, 4))
    name_var = tk.StringVar()
    tk.Entry(frame, textvariable=name_var, width=34).pack(padx=10, pady=(0, 6))

    var_ing_vars, var_cost_vars = [], []
    for i in range(n_variations):
        tk.Label(frame, text=f"Variation {i+1}:").pack(anchor="w", padx=10, pady=(10, 2))
        vi = tk.StringVar()
        tk.Entry(frame, textvariable=vi, width=34).pack(padx=10, pady=(0, 2))
        tk.Label(frame, text="Cost (eon):").pack(anchor="w", padx=10, pady=(2, 2))
        vc = tk.StringVar()
        tk.Entry(frame, textvariable=vc, width=14).pack(padx=10, pady=(0, 4))
        var_ing_vars.append(vi)
        var_cost_vars.append(vc)

    tk.Label(frame, text="Image:").pack(anchor="w", padx=10, pady=(10, 4))
    img_var = tk.StringVar()
    tk.Entry(frame, textvariable=img_var, width=34).pack(padx=10, pady=(0, 6))

    tk.Label(frame, text="Description:").pack(anchor="w", padx=10, pady=(6, 4))
    desc_txt = tk.Text(frame, width=36, height=6)
    desc_txt.pack(padx=10, pady=(0, 8))

    info = (
        'Images go in "images" (include extension). '
        'Provide cost per variation if any. '
        'List variation ingredients as "# Item, # Item, ...".'
    )
    tk.Label(frame, text=info, justify="left", wraplength=360).pack(padx=10, pady=(0, 8))

    def submit():
        global raw_materials, craftable_items
        name = name_var.get().strip().lower()
        if not name:
            messagebox.showwarning("Missing", "Item name is required.")
            return

        variations = {}
        for i, (vings, vcost) in enumerate(zip(var_ing_vars, var_cost_vars), start=1):
            label = f"Variation {i}"
            ing_text = vings.get().strip()
            vcost_text = vcost.get().strip()

            # Parse ingredients for variation
            ing_dict = {}
            if ing_text:
                parts = [p.strip() for p in ing_text.split(",") if p.strip()]
                for p in parts:
                    qn = p.split(" ", 1)
                    if len(qn) == 2:
                        qty = int("".join([c for c in qn[0] if c.isdigit()]) or "0")
                        ing = qn[1].strip().lower()
                        ing_dict[ing] = ing_dict.get(ing, 0) + qty

            c = int("".join([d for d in vcost_text if d.isdigit()])) if vcost_text else 0
            variations[label.lower()] = {"label": label, "ingredients": ing_dict, "cost": c}

        img = img_var.get().strip()
        desc = desc_txt.get("1.0", "end").strip()

        craftable_items[name] = {"ingredients": {}, "variations": variations, "cost": 0, "image": img, "description": desc}
        write_config_from_memory()
        raw_materials, craftable_items = load_recipes()
        update_tree()
        top.destroy()

    tk.Button(frame, text="Add", command=submit).pack(pady=10)


# =============================================================================
# Theme & custom scrollbar
# =============================================================================

def setup_theme(root):
    """Apply themed style across ttk + custom scrollbar."""
    style = ttk.Style()
    style.theme_use("clam")

    # Palette
    base_bg = "#C39B6E"
    panel_bg = "#A87B4E"
    border_color = "#5C3B1E"
    button_bg = "#8C6239"
    button_hover = "#B9834B"
    highlight = "#D8B27C"
    text_color = "#2B1A0F"
    scrollbar_bg = "#8C6239"
    scrollbar_trough = "#5C3B1E"

    # Root bg
    root.configure(bg=base_bg)

    # ttk base styles
    style.configure(".", background=panel_bg, foreground=text_color, relief="flat", borderwidth=0)
    style.configure("TFrame", background=panel_bg)
    style.configure("TLabel", background=panel_bg, foreground=text_color)
    style.configure("TButton", background=button_bg, foreground=text_color, borderwidth=1, relief="raised",
                    padding=(8, 4), font=("Segoe UI", 10, "bold"))
    style.map("TButton",
              background=[("active", button_hover), ("pressed", button_hover)],
              relief=[("pressed", "sunken"), ("!pressed", "raised")])

    # Treeview
    style.configure("Treeview", background=base_bg, fieldbackground=base_bg, foreground=text_color,
                    bordercolor=border_color, borderwidth=1, rowheight=22)
    style.map("Treeview", background=[("selected", highlight)], foreground=[("selected", text_color)])
    style.configure("Treeview.Heading", background=button_bg, foreground=text_color, borderwidth=1, relief="raised")
    style.map("Treeview.Heading", background=[("active", button_hover)],
              relief=[("pressed", "sunken"), ("!pressed", "raised")])

    # Entry/Text (ttk theme hints for colors)
    style.configure("TEntry", fieldbackground=base_bg, background=base_bg, foreground=text_color, bordercolor=border_color)
    style.configure("TText", fieldbackground=base_bg, background=base_bg, foreground=text_color, bordercolor=border_color)

    # tk defaults for standard widgets
    root.option_add("*Background", base_bg)
    root.option_add("*Foreground", text_color)
    root.option_add("*Button.Background", button_bg)
    root.option_add("*Button.Foreground", text_color)
    root.option_add("*Button.ActiveBackground", button_hover)
    root.option_add("*Button.ActiveForeground", text_color)
    root.option_add("*Entry.Background", base_bg)
    root.option_add("*Entry.Foreground", text_color)
    root.option_add("*Entry.InsertBackground", border_color)
    root.option_add("*Entry.SelectBackground", highlight)
    root.option_add("*Entry.SelectForeground", text_color)
    root.option_add("*Text.Background", base_bg)
    root.option_add("*Text.Foreground", text_color)
    root.option_add("*Text.InsertBackground", border_color)
    root.option_add("*Text.SelectBackground", highlight)
    root.option_add("*Text.SelectForeground", text_color)
    root.option_add("*Label.Background", panel_bg)
    root.option_add("*Label.Foreground", text_color)
    root.option_add("*Frame.Background", panel_bg)

    # --- Custom scrollbar replacing tk.Scrollbar globally ---
    class ThemedScrollbar(tk.Canvas):
        """A slim custom scrollbar that mirrors the Scrollbar API (vertical/horizontal)."""

        def __init__(self, master=None, **kwargs):
            self.command = kwargs.pop("command", None)
            self.orient = kwargs.pop("orient", "vertical")
            if self.orient == "vertical":
                kwargs.setdefault("width", 12)
            else:
                kwargs.setdefault("height", 12)
            super().__init__(master, highlightthickness=0, bd=0, relief="flat", **kwargs)

            self.thumb_color = scrollbar_bg
            self.trough_color = scrollbar_trough
            self.hover_color = button_hover

            self._thumb_id = None
            self._pressed = False
            self._press_offset = 0.0
            self.lo, self.hi = 0.0, 1.0

            self.bind("<Configure>", self._draw_scrollbar)
            self.bind("<ButtonPress-1>", self._click)
            self.bind("<B1-Motion>", self._drag)
            self.bind("<ButtonRelease-1>", self._release)

        # Allow configure(command=..., orient=...)
        def configure(self, cnf=None, **kw):
            if "command" in kw:
                self.command = kw.pop("command")
            if "orient" in kw:
                self.orient = kw.pop("orient")
            return super().configure(cnf, **kw)
        config = configure

        def set(self, lo, hi):
            try:
                self.lo, self.hi = float(lo), float(hi)
            except Exception:
                self.lo, self.hi = 0.0, 1.0
            self._draw_scrollbar()

        def _draw_scrollbar(self, event=None):
            self.delete("all")
            w, h = self.winfo_width(), self.winfo_height()
            self.create_rectangle(0, 0, w, h, fill=self.trough_color, outline=self.trough_color)

            if self.hi - self.lo >= 1.0:
                return  # no thumb if all content visible

            min_size = 20
            if self.orient == "vertical":
                y1 = max(2, int(self.lo * h))
                y2 = min(h - 2, int(self.hi * h))
                if y2 - y1 < min_size:
                    y2 = min(h - 2, y1 + min_size)
                self._thumb_id = self.create_rectangle(2, y1, w - 2, y2,
                                                       fill=self.thumb_color, outline=self.trough_color, width=1)
            else:
                x1 = max(2, int(self.lo * w))
                x2 = min(w - 2, int(self.hi * w))
                if x2 - x1 < min_size:
                    x2 = min(w - 2, x1 + min_size)
                self._thumb_id = self.create_rectangle(x1, 2, x2, h - 2,
                                                       fill=self.thumb_color, outline=self.trough_color, width=1)

            # Hover effect on thumb
            self.tag_bind(self._thumb_id, "<Enter>",
                          lambda e: self.itemconfig(self._thumb_id, fill=self.hover_color))
            self.tag_bind(self._thumb_id, "<Leave>",
                          lambda e: self.itemconfig(self._thumb_id, fill=self.thumb_color))

        def _click(self, event):
            if not self.command or not self._thumb_id:
                return
            self._pressed = True
            coords = self.coords(self._thumb_id)
            if self.orient == "vertical":
                y1, y2 = coords[1], coords[3]
                if not (y1 <= event.y <= y2):
                    frac = max(0.0, min(1.0, event.y / max(1, self.winfo_height())))
                    self.command("moveto", str(frac))
                else:
                    self._press_offset = event.y - y1
            else:
                x1, x2 = coords[0], coords[2]
                if not (x1 <= event.x <= x2):
                    frac = max(0.0, min(1.0, event.x / max(1, self.winfo_width())))
                    self.command("moveto", str(frac))
                else:
                    self._press_offset = event.x - x1

        def _drag(self, event):
            if not (self._pressed and self.command and self._thumb_id):
                return
            if self.orient == "vertical":
                h = max(1, self.winfo_height())
                new_top_pix = event.y - self._press_offset
                frac = max(0.0, min(1.0, new_top_pix / h))
                self.command("moveto", str(frac))
            else:
                w = max(1, self.winfo_width())
                new_left_pix = event.x - self._press_offset
                frac = max(0.0, min(1.0, new_left_pix / w))
                self.command("moveto", str(frac))

        def _release(self, event):
            self._pressed = False
            self._press_offset = 0.0

    # Patch tk.Scrollbar globally so ttk.Treeview/Text use it
    tk.Scrollbar = ThemedScrollbar


# =============================================================================
# Main window & UI construction
# =============================================================================

ICON_PATH = os.path.join(IMAGE_FOLDER, "Logo.ico")

root = tk.Tk()
root.withdraw()  # hide during theme setup to avoid flicker
setup_theme(root)
root.title("Ayumu's Crafting Buddy <3")
center_window(root, 380, 600)

# Ensure the native handle exists before iconbitmap
root.update_idletasks()
try:
    if os.path.exists(ICON_PATH):
        root.iconbitmap(default=ICON_PATH)
    else:
        print(f"Warning: Icon not found at {ICON_PATH}")
except Exception as e:
    print(f"Warning: Could not load window icon: {e}")

# Optional PNG icon (Linux/macOS)
try:
    icon_png = os.path.join(IMAGE_FOLDER, "Logo.png")
    if os.path.exists(icon_png):
        root.iconphoto(False, tk.PhotoImage(file=icon_png))
except Exception:
    pass

root.deiconify()

selected_item = tk.StringVar()

# ---- Home frame -------------------------------------------------------------

home_frame = tk.Frame(root)
home_frame.pack(fill="both", expand=True)

search_var = tk.StringVar()

search_bar_frame = tk.Frame(home_frame)
search_bar_frame.pack(fill="x", pady=8, padx=8)

search_entry = tk.Entry(search_bar_frame, textvariable=search_var, width=40, fg="gray")
search_entry.pack(side="left", padx=(0, 10))
search_entry.insert(0, "Search...")

add_btn = tk.Button(search_bar_frame, text="➕", fg="white", bg="#1E8449", width=3, relief="raised", command=open_add_item_choice)
remove_btn = tk.Button(search_bar_frame, text="❌", fg="white", bg="#922B21", width=3, relief="raised", command=open_remove_item_window)
open_dir_btn = tk.Button(search_bar_frame, text="📂", fg="white", bg="#5D6D7E", width=3, relief="raised", command=open_appdata_folder)
for b in (open_dir_btn, remove_btn, add_btn):
    b.pack(side="right", padx=2)

def on_add_hover(e):    schedule_tooltip(add_btn, "add_btn", "Add items", e.x_root, e.y_root, delay=200)
def on_remove_hover(e): schedule_tooltip(remove_btn, "remove_btn", "Remove items", e.x_root, e.y_root, delay=200)
def on_open_hover(e):   schedule_tooltip(open_dir_btn, "open_dir_btn", "Open AppData Folder", e.x_root, e.y_root, delay=200)
def on_leave_button(e): cancel_scheduled_tooltip()
add_btn.bind("<Enter>", on_add_hover);      add_btn.bind("<Leave>", on_leave_button)
remove_btn.bind("<Enter>", on_remove_hover); remove_btn.bind("<Leave>", on_leave_button)
open_dir_btn.bind("<Enter>", on_open_hover); open_dir_btn.bind("<Leave>", on_leave_button)

def clear_search_placeholder(event):
    if search_entry.get() == "Search...":
        search_entry.delete(0, tk.END)
        search_entry.config(fg="black")

def restore_search_placeholder(event):
    if not search_entry.get():
        search_entry.insert(0, "Search...")
        search_entry.config(fg="gray")
        update_tree()

search_entry.bind("<FocusIn>", clear_search_placeholder)
search_entry.bind("<FocusOut>", restore_search_placeholder)

home_tree_frame = tk.Frame(home_frame)
home_tree_frame.pack(fill="both", expand=True, padx=8, pady=4)
home_scroll = tk.Scrollbar(home_tree_frame)
home_scroll.pack(side="right", fill="y")
home_tree = ttk.Treeview(home_tree_frame, yscrollcommand=home_scroll.set, show="tree")
home_tree.pack(fill="both", expand=True)
home_tree.bind("<<TreeviewSelect>>", lambda e: on_home_select())
home_tree.bind("<Motion>", lambda e: on_home_motion(e))
home_tree.bind("<Leave>", lambda e: on_home_leave(e))
home_scroll.config(command=home_tree.yview)
search_var.trace_add("write", lambda *args: update_tree(search_var.get()))

# ---- Recipe frame -----------------------------------------------------------

recipe_frame = tk.Frame(root)

top_frame = tk.Frame(recipe_frame)
top_frame.pack(fill="x", pady=8, anchor="w")
home_btn = tk.Button(top_frame, text="🏠 Home", command=show_home)
home_btn.pack(side="left", padx=6)
image_label = tk.Label(top_frame, text="Item Image", compound="top")
image_label.pack(side="left", padx=12)

def on_image_hover(event):
    desc = getattr(image_label, "tooltip_desc", "")
    if desc:
        schedule_tooltip(image_label, "image_label", desc, event.x_root, event.y_root, delay=300)

def on_image_leave(_):
    cancel_scheduled_tooltip()

image_label.bind("<Enter>", on_image_hover)
image_label.bind("<Leave>", on_image_leave)

recipe_tree_frame = tk.Frame(recipe_frame)
recipe_tree_frame.pack(fill="both", expand=True, padx=8, pady=4)
recipe_scroll = tk.Scrollbar(recipe_tree_frame)
recipe_scroll.pack(side="right", fill="y")
recipe_tree = ttk.Treeview(recipe_tree_frame, yscrollcommand=recipe_scroll.set, show="tree")
recipe_tree.pack(fill="both", expand=True)
recipe_tree.bind("<<TreeviewSelect>>", lambda e: on_recipe_select())
recipe_tree.bind("<Motion>", lambda e: on_recipe_motion(e))
recipe_tree.bind("<Leave>", lambda e: on_recipe_leave(e))
recipe_scroll.config(command=recipe_tree.yview)

summary_frame = tk.Frame(recipe_frame)
summary_frame.pack(fill="both", expand=True, pady=6, padx=8)
summary_scroll = tk.Scrollbar(summary_frame)
summary_scroll.pack(side="right", fill="y")
summary_text_widget = tk.Text(summary_frame, height=10, wrap="word", yscrollcommand=summary_scroll.set)
summary_text_widget.pack(fill="both", expand=True)
summary_text_widget.config(state="disabled")
summary_scroll.config(command=summary_text_widget.yview)

# ---- Summary right-click menu ----------------------------------------------

def show_summary_context_menu(event):
    summary_menu.tk_popup(event.x_root, event.y_root)

def copy_selected_text():
    try:
        selected = summary_text_widget.selection_get()
        root.clipboard_clear()
        root.clipboard_append(selected)
    except tk.TclError:
        pass

def copy_all_text():
    root.clipboard_clear()
    text = summary_text_widget.get("1.0", "end").strip()
    root.clipboard_append(text)

summary_menu = tk.Menu(root, tearoff=0)
summary_menu.add_command(label="📋 Copy Selected", command=copy_selected_text)
summary_menu.add_command(label="📜 Copy All", command=copy_all_text)
summary_text_widget.bind("<Button-3>", show_summary_context_menu)

# =============================================================================
# Home tree population & event handlers
# =============================================================================

_home_icons = {}

def update_tree(filter_text=""):
    """Populate the home tree with craftable items, filtered by text."""
    for c in home_tree.get_children():
        home_tree.delete(c)
    _home_icons.clear()
    f = (filter_text or "").lower().strip()
    for item, _recipe in sorted(craftable_items.items(), key=lambda kv: kv[0]):
        if not f or f in item.lower():
            icon = load_image_for_item(item, size=(24, 24))
            display_text = ("   " + item.title()) if icon else item.title()
            if icon:
                _home_icons[item] = icon
                home_tree.insert("", "end", text=display_text, image=icon)
            else:
                home_tree.insert("", "end", text=display_text)


def on_home_select():
    """Handle click on a home-tree item (trigger variation popup if needed)."""
    sel = home_tree.focus()
    if not sel:
        return
    item_text = home_tree.item(sel, "text").lstrip()
    item_name = item_text.lower()

    global current_root_item
    current_root_item = item_name
    ings = craftable_items.get(item_name, {}).get("ingredients", {})
    has_variant_children = any(craftable_items.get(ing, {}).get("variations") for ing in ings)

    if has_variant_children:
        show_multi_variation_popup(item_name, ings, append=False)
        return
    if craftable_items.get(item_name, {}).get("variations"):
        show_multi_variation_popup(item_name, {item_name: 1}, append=False)
    else:
        show_recipe(item_name)


def on_recipe_select():
    """Update image + tooltip when a node in the recipe tree is selected."""
    sel = recipe_tree.focus()
    if not sel:
        return
    text = recipe_tree.item(sel, "text")
    name_part = text.split("(")[0]
    name = (name_part.split("×")[-1] if "×" in name_part else name_part).strip().lower()

    img = load_image_for_item(name, size=(120, 120))
    if img:
        image_label.config(image=img, text="")
        image_label.image = img
    else:
        image_label.config(image="", text="No Image")

    selected_item.set(name)
    desc = craftable_items.get(name, {}).get("description", "") or raw_materials.get(name, {}).get("description", "")
    cancel_scheduled_tooltip()
    image_label.tooltip_desc = desc if desc else ""


_last_home_row = None
_last_recipe_row = None

def on_home_motion(event):
    """Hover tooltip in home tree."""
    global _last_home_row
    row = home_tree.identify_row(event.y)
    if not row:
        _last_home_row = None
        cancel_scheduled_tooltip()
        return
    if row == _last_home_row:
        return
    _last_home_row = row
    item_text = home_tree.item(row, "text").lstrip()
    item_name = item_text.lower()
    desc = craftable_items.get(item_name, {}).get("description", "")
    cancel_scheduled_tooltip()
    if desc:
        schedule_tooltip(home_tree, row, desc, event.x_root, event.y_root, delay=420)


def on_recipe_motion(event):
    """Hover tooltip in recipe tree."""
    global _last_recipe_row
    row = recipe_tree.identify_row(event.y)
    if not row:
        _last_recipe_row = None
        cancel_scheduled_tooltip()
        return
    if row == _last_recipe_row:
        return
    _last_recipe_row = row
    text = recipe_tree.item(row, "text")
    name_part = text.split("(")[0]
    name = (name_part.split("×")[-1] if "×" in name_part else name_part).strip().lower()
    desc = craftable_items.get(name, {}).get("description", "") or raw_materials.get(name, {}).get("description", "")
    cancel_scheduled_tooltip()
    if desc:
        schedule_tooltip(recipe_tree, row, desc, event.x_root, event.y_root, delay=420)


def on_home_leave(_): cancel_scheduled_tooltip()
def on_recipe_leave(_): cancel_scheduled_tooltip()


# =============================================================================
# Run app
# =============================================================================

update_tree()
root.mainloop()
