# MangaTranslate Project Instructions

This is a Python PyQt5 desktop application.

Before changing code:
- Read `code.md` first.
- Understand the current architecture before editing.
- Do not rewrite large files blindly.
- `src/ui/main_window.py` is very large, so only edit the smallest necessary section.
- Preserve existing features and behavior.

UI/Design rules:
- Keep the app visually consistent with the existing dark theme.
- Main background: `#090a0f`
- Panel background: `#0e111a`
- Accent color: `#38bdf8`
- Main text color: `#cbd5e1`
- Font stack: `Outfit`, `Inter`, `Segoe UI`, sans-serif.
- Prefer QSS/class-based styling over random inline styles.
- Reuse existing widgets from `src/ui/widgets.py` when possible.
- Reuse existing panels/dialog patterns from `src/ui/panels.py`, `src/ui/dialogs.py`, and `src/ui/unified_help_dialog.py`.

When creating new UI files:
- Put reusable custom widgets in `src/ui/widgets.py`, or create `src/ui/widgets/<name>.py` if the widget is large.
- Put new dialogs in `src/ui/dialogs.py`, or create a standalone `src/ui/<feature>_dialog.py` if complex.
- Put new panels/sidebar components in `src/ui/panels.py`, or create `src/ui/<feature>_panel.py` if complex.
- Put shared colors, spacing, and QSS helpers in `src/ui/theme.py` if needed.
- Do not create random files in the root folder.

Centralized text rules:
- Put app identity and version text in `src/core/app_info.py`.
- Put repeated or important UI copy in `src/ui/texts.py`.
- Do not hardcode app version, app title, common button labels, dialog titles, status messages, or repeated user-facing text in feature code.
- If a new category grows large, create a focused text module such as `src/ui/texts_<feature>.py` and import it from the feature.
- Keep text modules as data/constants and tiny formatting helpers only; do not put UI logic or business logic there.

Threading rules:
- Do not update UI from worker threads.
- Use `pyqtSignal` for worker-to-UI communication.
- Do not clear QThread references before the thread has fully finished.

Project safety:
- Do not delete `.secret.key`.
- Do not hardcode API keys.
- Use existing config/settings helpers.
- Do not add new dependencies unless `requirements.txt` is also updated.
