"""ScaffoldValidator — verifies a scaffold is complete using its manifest."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ValidationResult:
    ok: bool
    missing: list[str] = field(default_factory=list)
    empty: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ScaffoldValidator:
    """Checks that all files listed in manifest.json exist and are non-empty."""

    def validate(self, output_dir: Path) -> ValidationResult:
        """Return ValidationResult; never raises."""
        manifest_path = output_dir / "manifest.json"
        if not manifest_path.exists():
            return ValidationResult(
                ok=False,
                warnings=["manifest.json not found in scaffold directory"],
            )

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            return ValidationResult(
                ok=False,
                warnings=[f"manifest.json could not be parsed: {exc}"],
            )

        missing: list[str] = []
        empty: list[str] = []

        for entry in manifest.get("files", []):
            rel = entry["relative_path"]
            path = output_dir / rel
            if not path.exists():
                missing.append(rel)
            elif path.stat().st_size == 0 and entry.get("header", True):
                empty.append(rel)

        return ValidationResult(ok=not missing and not empty, missing=missing, empty=empty)
