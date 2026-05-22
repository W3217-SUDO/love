"""Jinja2 templating wiring.

Importing this module yields a singleton `templates` object that knows how to
render templates from `app/templates/`. Routers call `templates.TemplateResponse`.
"""
from pathlib import Path

from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
