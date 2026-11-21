"""Fa rispettare i confini del modular monolith (ARCHITECTURE.md, ADR-017).

Regole:
1. Ogni modulo in app/modules deve essere dichiarato in ALLOWED_DEPENDENCIES.
2. Un modulo può importare solo i moduli che ha dichiarato.
3. Da un altro modulo si importa solo il package (`app.modules.x`), mai i file interni.
"""

import ast
from pathlib import Path

MODULES_DIR = Path(__file__).resolve().parent.parent / "app" / "modules"

ALLOWED_DEPENDENCIES: dict[str, set[str]] = {
    "audit": set(),
    "identity": set(),
}


def imported_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
            # `from app.modules import audit` importa il package audit
            if node.module == "app.modules":
                names.extend(f"app.modules.{alias.name}" for alias in node.names)
    return names


def module_names() -> set[str]:
    return {p.name for p in MODULES_DIR.iterdir() if (p / "__init__.py").exists()}


def test_every_module_is_declared() -> None:
    assert module_names() == set(ALLOWED_DEPENDENCIES)


def test_modules_respect_boundaries() -> None:
    violations: list[str] = []
    for module in module_names():
        for path in (MODULES_DIR / module).rglob("*.py"):
            for name in imported_names(path):
                parts = name.split(".")
                if parts[:2] != ["app", "modules"] or len(parts) < 3 or parts[2] == module:
                    continue
                other = parts[2]
                where = f"{path.relative_to(MODULES_DIR)} -> {name}"
                if other not in ALLOWED_DEPENDENCIES[module]:
                    violations.append(f"dipendenza non dichiarata: {where}")
                elif len(parts) > 3:
                    violations.append(f"import di un file interno: {where}")
    assert not violations, "\n".join(violations)


def test_boundary_checker_detects_violations(tmp_path: Path) -> None:
    sample = tmp_path / "sample.py"
    sample.write_text(
        "from app.modules.identity.keycloak_adapter import X\nfrom app.modules import jobs\n"
    )
    assert imported_names(sample) == [
        "app.modules.identity.keycloak_adapter",
        "app.modules",
        "app.modules.jobs",
    ]
