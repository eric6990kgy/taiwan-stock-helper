"""Automated guard for the app/analytics independence rule (Phase 2's
founding constraint, reaffirmed for Phase 6's technical.py): nothing in this
package may import FastAPI, SQLAlchemy, httpx, or any app.* package outside
of app.analytics itself. Static source inspection, not just convention --
this is what the README's "verified by grep" claim should mean going
forward.
"""

import ast
from pathlib import Path

ANALYTICS_DIR = Path(__file__).resolve().parent.parent.parent / "app" / "analytics"
FORBIDDEN_TOP_LEVEL_MODULES = {"fastapi", "sqlalchemy", "httpx", "pydantic"}


def _imported_top_level_modules(file_path: Path) -> set[str]:
    tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.add(node.module.split(".")[0])
    return modules


def test_no_forbidden_framework_imports_in_analytics():
    py_files = list(ANALYTICS_DIR.glob("*.py"))
    assert py_files, "expected to find source files under app/analytics"

    for file_path in py_files:
        modules = _imported_top_level_modules(file_path)
        forbidden_hits = modules & FORBIDDEN_TOP_LEVEL_MODULES
        assert not forbidden_hits, f"{file_path.name} imports forbidden module(s): {forbidden_hits}"


def test_no_imports_from_outside_app_analytics():
    """app.analytics may only import from itself (or stdlib/third-party
    non-framework libs) -- never app.services/app.repositories/app.api/
    app.models/app.providers, which would pull FastAPI/SQLAlchemy in
    transitively even if this file never imports them directly."""
    py_files = list(ANALYTICS_DIR.glob("*.py"))
    disallowed_app_packages = {"app.services", "app.repositories", "app.api", "app.models", "app.providers", "app.database"}

    for file_path in py_files:
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        for node in ast.walk(tree):
            module = None
            if isinstance(node, ast.ImportFrom) and node.module:
                module = node.module
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name
            if module is None:
                continue
            for disallowed in disallowed_app_packages:
                assert not module.startswith(disallowed), (
                    f"{file_path.name} imports {module!r}, which pulls in framework/DB dependencies"
                )
