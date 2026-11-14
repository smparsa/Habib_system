"""Temporary audit helper: list model fields that have no code references
outside their own models.py file and the migrations history.

Usage: venv/Scripts/python.exe _audit_dormant.py [app_label ...]
"""
import os
import re
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "habib_system.settings")
django.setup()

from django.apps import apps  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
EXCLUDE_DIRS = {"venv", ".git", ".freebuff", ".idea", "__pycache__", "media"}
EXCLUDE_FILES = {"_audit_dormant.py", "manage.py"}

APP_LABELS = sys.argv[1:] or None


def source_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in filenames:
            if not fn.endswith((".py", ".html", ".js")):
                continue
            if fn in EXCLUDE_FILES:
                continue
            yield os.path.join(dirpath, fn)


def occurrences(field_name, exclude_paths):
    pat = re.compile(r"\b" + re.escape(field_name) + r"\b")
    hits = []
    for fp in source_files():
        if fp in exclude_paths:
            continue
        try:
            text = open(fp, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        n = len(pat.findall(text))
        if n:
            rel = os.path.relpath(fp, ROOT)
            if "migrations" in rel:
                continue  # migration history is not live usage
            hits.append((rel, n))
    return hits


def fields_of(model):
    out = []
    for f in model._meta.get_fields():
        name = f.name
        if name == "id":
            continue
        if getattr(f, "auto_created", False):
            continue  # reverse relations / through tables
        out.append(name)
    return out


def main():
    for model in apps.get_models():
        app_label = model._meta.app_label
        if APP_LABELS and app_label not in APP_LABELS:
            continue
        model_path = os.path.normpath(os.path.join(ROOT, *model.__module__.split("."))) + ".py"
        print(f"\n=== {app_label}.{model.__name__} ===")
        for name in fields_of(model):
            hits = occurrences(name, {model_path})
            if not hits:
                print(f"  DORMANT? {name}")
            elif len(hits) == 1 and hits[0][0] == os.path.relpath(model_path, ROOT):
                print(f"  dormant? {name} (only self-ref)")
            else:
                pass  # referenced somewhere; skip


if __name__ == "__main__":
    main()