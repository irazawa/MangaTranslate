"""Application identity and version metadata."""

APP_NAME = "Manga OCR & Typeset Tool"
APP_VERSION = "14.8.8"
APP_COPYRIGHT = "Copyright © 2024"


def app_title(project_name=None) -> str:
    title = f"{APP_NAME} v{APP_VERSION}"
    if project_name:
        return f"{title} - {project_name}"
    return title
