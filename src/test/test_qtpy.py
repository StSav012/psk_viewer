import ast
import mimetypes
from pathlib import Path

import qtpy


def test_only_qtpy_imported() -> None:
    mimetypes.init()

    imported_packages: set[str] = set()

    for src in (Path(__file__).parent.parent / "psk_viewer").iterdir():
        if mimetypes.guess_type(src) != ("text/x-python", None):
            continue
        text: str = src.read_text()
        if text.startswith(("\ufeff", "\ufffe")):
            text = text[1:]
        module: ast.Module = ast.parse(text, src, type_comments=True)
        for s in module.body:
            if isinstance(s, ast.Import):
                s: ast.Import
                imported_packages.update(a.name for a in s.names)
            elif isinstance(s, ast.ImportFrom):
                s: ast.ImportFrom
                import_source: str | None = s.module
                if import_source is None:
                    continue
                import_source = import_source.split(".", maxsplit=1)[0]
                if import_source:
                    imported_packages.add(import_source.casefold())

    assert (qtpy.__package__ in imported_packages) != any(
        api.casefold() in imported_packages for api in qtpy.API_NAMES
    )


if __name__ == "__main__":
    test_only_qtpy_imported()
