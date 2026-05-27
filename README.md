# MangaTranslate 🎨🤖

MangaTranslate is a premium, interactive Manga Translation and Typesetting application built with Python and PyQt5. Designed to elevate the scanlation and translation workflow, it offers a visual, layer-based typesetting environment with integrated multi-engine AI support.

---

## ✨ Outstanding Features

### 1. 🖥️ Focus-Oriented Workspace & Collapsible Panels
Maximize your editing canvas using highly responsive, collapsible sidebars and dedicated focus tools:
* **F3 (Folder list Sidebar)**: Instantly show or hide the left navigation panel containing your active image lists.
* **F4 (Tools Panel Sidebar)**: Toggle the right tools panel containing AI options, typesetting controls, and cleanup actions.
* **F2 (Focus Mode)**: Hides both sidebars simultaneously, providing an immersive, clean slate to focus solely on typesetting your manga.
* **Synchronized Controls**: Access toggles seamlessly via **Hotkeys**, the **View Menu Bar**, or custom **Bottom Navigation Toggles** (featuring an emerald-green Focus Mode button).

### 2. 🎨 Photoshop & Canva-Style Layers Panel
Organize your typesetting workspace efficiently using a dedicated **Layers** manager:
* **Visual Rendering Order (z-index)**: Drag-and-drop or use the **Bring to Front / Send to Back** buttons to control overlapping text bubbles.
* **Show/Hide Eye Toggles**: Hide specific text blocks with checkboxes. Hidden layers are instantly invisible and completely unselectable/unclickable on the canvas.
* **Real-Time Opacity Slider (0% - 100%)**: Smooth, high-performance transparency adjustments with zero visual lag.
* **Double-Click Rename**: Quickly organize and label text blocks by double-clicking on the layer name.
* **Bi-Directional Sync**: Clicking a text box on the canvas highlights it in the Layers panel, and selecting a layer in the panel highlights it on the canvas.

### 3. 🤖 Multi-Engine AI Translation & OCR
Harness the power of advanced language models and OCR detectors:
* **Broad Integration**: Out-of-the-box support for **OpenAI**, **Google Gemini**, **DeepL**, and **OpenRouter** backends.
* **Default Presets**: Configure your preferred **Default Translation Style** (e.g., *Santai*, *Formal*, *Akrab*, *Sesuai Konteks*, etc.) directly in the global Settings dialog, which automatically saves and loads on boot.
* **Persistent Local Cache**: Uses a thread-safe, disk-serialized cache (`.cache/ocr_translation_cache.json`) to remember translated blocks. Avoid redundant API calls and prevent double-billing.

### 4. 🚀 Zero-Configuration Launcher
No manual environment setup needed!
* **Automated Bootloader (`launcher.bat`)**: Double-clicking the launcher automatically checks for a local virtual environment. If missing, it builds a `venv`, upgrades `pip`, installs `requirements.txt` dependencies, and boots the application safely in isolation.

### 5. 🤫 Clean, Silent Startup
* No annoying warning alerts or startup popups (like missing optional libraries) to interrupt your flow.
* Global deprecation filters mute noisy console warnings from dependencies on launch.

---

## 🎹 Shortkeys & Controls Reference

| Shortcut / Trigger | Action | Description |
|:---|:---|:---|
| **`F2`** | Toggle Focus Mode | Collapses or expands both sidebars at the same time |
| **`F3`** | Toggle Folder Sidebar | Shows or hides the left image navigation folder list |
| **`F4`** | Toggle Tools Panel | Shows or hides the right translation/formatting sidebar |
| **`Esc`** | Save Project | Instantly saves your current translation progress |
| **`Space`** | Next Image | Move forward to the next image in the directory |
| **`Middle Mouse Click`** | Save Image | Renders and exports the final translation image |
| **`Right Mouse Click`** | Confirm Pen | Confirms active typesetting/pen/cleaning modifications |
| **`Double-Click Layer`** | Rename Layer | Quickly edit the name of the selected text block layer |

---

## 🚀 Quick Start / Installation

Getting started is extremely simple and requires no manual environment configuration:

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/irazawa/MangaTranslate.git
   cd MangaTranslate
   ```
2. **Launch the Tool**:
   * On Windows, simply double-click **`launcher.bat`**.
   * The launcher will set up the local virtual environment (`venv`), install dependencies, and launch the editor.

---

## 🛡️ Excluded Configurations
The repository is pre-configured with a `.gitignore` to prevent sensitive credentials and heavy local directories from being uploaded:
* Local API keys and preferences (`settings.json`) are excluded.
* Heavy image and manga assets (`Manga/` folder) are ignored.
* Virtual environment (`venv/`) and local translation caches (`.cache/`) are kept strictly offline.