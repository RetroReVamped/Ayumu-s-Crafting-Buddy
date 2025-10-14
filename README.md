# Ayumu’s Crafting Buddy

*A EO-inspired crafting companion and recipe manager for crafters, collectors, and EO-style tinkerers.*

![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![GUI](https://img.shields.io/badge/GUI-Tkinter-green.svg)
![License](https://img.shields.io/badge/License-Non--Commercial-red.svg)
![Build](https://img.shields.io/badge/Build-Nuitka%20%2B%20MSVC-blueviolet.svg)

---

## 🌟 Overview

**Ayumu’s Crafting Buddy** is a standalone desktop that helps you manage, view, and explore **crafting recipes** with support for:

- Raw materials and craftable items  
- Multi-step crafting chains  
- Multiple recipe variations per item
- Full cost breakdown and raw material summary  
- Integrated image previews and descriptions  
- Simple and cozy EO-style UI  

---

## ⚙️ Key Features

### 🧵 Crafting System
- Create and edit **craftable items** with ingredients, cost, image, and description.
- Add **multiple recipe variations** (e.g., “Variation 1”, “Variation 2”) for the same item.
- Automatically calculate **total crafting costs** and **raw material totals** across all dependencies.
- View nested crafting trees with expandable branches for each item.

### 🖼️ Image & Description Support
- Each item can include an image (PNG, JPG, ICO, etc.) stored in the `/images` folder.
- Tooltip descriptions appear when hovering over items or recipes.
- Auto-scaling image previews in both list and detail views.

### ⚒️ Recipe Management
- Add or remove raw materials or craftable items directly within the app.
- Automatically updates the `recipes.cfg` file on every change.
- Supports multi-line descriptions.

### 🔍 Search & Navigation
- Real-time search bar with fuzzy match.
- Tree-style layout with collapsible entries.
- Tooltips on hover for quick reference.

### 🧩 Intelligent Variation Handling
- Automatically prompts you to select which **variation** to craft when multiple recipes exist.
- Handles nested variations (e.g., an item that uses another item with multiple crafting methods).
- Properly multiplies and merges ingredient totals based on your choices.

### 💾 AppData Integration
- On first launch, the app automatically creates:
- %AppData%\AyumuCraftingBuddy
- ├── recipes.cfg
- └── images\
- Copies default configuration and images if missing.

### 📂 Utility Shortcuts
- 🏠 **Home** — Return to main crafting list.  
- ➕ **Add Item** — Create new raw or craftable items.  
- ❌ **Remove Item** — Delete unwanted entries.  
- 📂 **Open AppData Folder** — Opens your data directory instantly.  

### 💡 Quality of Life
- Auto-centering popups and scrollable forms.   
- Right-click **Copy** menu on the crafting summary (copy selected or all).   
- Fully resizable windows and adaptive popup sizing.  

---

## 📦 Installation

### Option 1: (recommended)
- Download the latest release from the **Releases** page and run:
Ayumu's Crafting Buddy.exe
  
### Option 2: (optional)
- Download the code and run with Python:
Ayumu's Crafting Buddy.py

#### Requirements:
- Python 3.9+
- Pillow (`pip install pillow`)

### Option 3: (optional)
- Download the code and compile it yourself

## ⚙️ Coming Soon
🌗 Optional Dark / EO-style Theme

## 🧑‍💻 Credits
Developed by: Ayumu @ RetroReVamped

Language: Python 3

UI Framework: Tkinter + PIL

License: Non-commercial use only (RetroReVamped License)


### 🧾 License:

This project is released under the RetroReVamped Non-Commercial License.

#### You may:

Use and modify for personal projects.

#### You may not:

Redistribute or sell derivative works.

See LICENSE for full details.

© 2025 RetroReVamped — All Rights Reserved.

License: Custom Non-Commercial, No-Redistribution (see LICENSE file).

#### Disclaimer:
All Images in the images folder are public domain and are not owned or claimed by RetroReVamped or Ayumu.
