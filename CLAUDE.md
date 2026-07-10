# CLAUDE.md - MangaTranslate Project Standard

You are working on **MangaTranslate**, a Windows-first PyQt5 desktop application for manga OCR, translation, and typesetting.

> **IMPORTANT**: This file (`CLAUDE.md`) and `AGENTS.md` work together as the standard project instructions so the user never has to explain repository rules repeatedly. Read `AGENTS.md` for complete architectural, subagent team, MCP, and skill guidelines.

## 🚀 Startup & Operating Loop

At the very beginning of every session (before any other step):
1. **[PALING AWAL HARUS DILAKUKAN] Read & Strictly Follow `claude-fable-5.md` First!**
   - At the very beginning, agents **MUST** read and follow the behavioral principles in `claude-fable-5.md` (user safety, empathy, concise communication, avoiding assumptions without verification, and clean formatting). All other instructions are subject to these ethics.
2. Confirm current working directory is `E:\Project\MangaTranslate`.
3. **Read root `AGENTS.md`** for comprehensive project rules, subagent workflows, and UI standards.
4. Read `.agents/index.md` and `.agents/code.md` for architecture and threading conventions.
5. Read `.agents/feature_ideas.md` when planning features or cleaning backlog.
6. Review repo status: `git status --short` and `git log --oneline -5`.
7. Always use the repository virtual environment: `venv\Scripts\python.exe`.
8. Create or update a task documentation folder under `.agents/task/<task-slug>-<YYYYMMDD-HHMMSS>/`.

## 🕸️ Graphify (Mandatory Architecture Check)

- **Mandatory Pre-Execution Check**: Before executing code modifications or randomly searching for file structures, **always use `/graphify`** (e.g. `graphify query "<question>"`) to understand codebase architecture and component relationships.
- **Fast Path**: If `graphify-out/graph.json` exists, query it directly (`graphify query "how does OCR connect to translation?"`).
- **Build / Update Graph**: Run `/graphify .` for a full build, `/graphify . --update` after code changes, or `graphify hook install` to automate updates post-commit.

## 🧠 Core Principles (Adapted from claude-fable-5.md)

- **Safety & Wellbeing First**: Prioritize user wellbeing, data safety, and careful refusal handling without preachy language.
- **Tone & Formatting**: Maintain a collaborative, friendly, and professional tone. Avoid over-formatting or unnecessary bullet lists when simple prose is clearer.
- **Precise Execution**: Do not assume files exist or code works without checking. Always verify syntax, imports, and UI layout before completing a task.

## 👥 Subagents & Team Workflow ("The Chef Team")

Do not attempt complex feature development alone. Leverage subagents and specialized roles like a professional kitchen team preparing a gourmet menu:
- **Manager / Orchestrator**: Understands user goals, divides tasks, and merges final results.
- **Planner / Researcher**: Investigates existing code and docs using **`/graphify query`** without editing files.
- **Coder**: Implements focused changes in specific files (keep `main_window.py` edits minimal).
- **QA / QC / Tester**: Validates syntax (`py_compile`), runs offscreen UI checks, and verifies zero regressions.

## 📚 Skills & MCP Integration

- Check `.agents/skills/` (e.g., `pyqt-manga-ui-designer`, `graphify`) and global skills before coding. Treat skills as ready-to-use recipe books.
- Utilize available Model Context Protocol (MCP) servers (Filesystem, Git, Playwright/Browser, SQLite, Memory) to safely inspect and automate workflows.

## 🛑 Completion Gate & Handoff

1. Verify code changes using `venv\Scripts\python.exe -m py_compile <changed_files>` and relevant smoke tests.
2. Record changes, verification evidence, and remaining risks in your `.agents/task/<task-slug>/task-log.md`.
3. Leave the repository clean and ready for seamless session handoff.
