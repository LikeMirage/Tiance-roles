from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from role_package import PACKAGE_FILES, load_and_validate_role_package, require


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ROLES_ROOT = REPOSITORY_ROOT / "roles"
SCHEMAS_ROOT = REPOSITORY_ROOT / "schemas"
DIST_ROOT = REPOSITORY_ROOT / "dist"


def main() -> None:
    role_roots = sorted(
        (path for path in ROLES_ROOT.iterdir() if path.is_dir()),
        key=lambda path: path.name,
    ) if ROLES_ROOT.is_dir() else []
    _reset_dist()
    entries = [_build_role(role_root) for role_root in role_roots]
    shutil.copytree(SCHEMAS_ROOT, DIST_ROOT / "schemas", dirs_exist_ok=True)
    _write_json(DIST_ROOT / "index.json", {
        "schemaVersion": 1,
        "kind": "tiance-role-market",
        "name": "Tiance Roles",
        "updatedAt": _market_updated_at(),
        "roles": entries,
    })
    print(f"市场构建完成：{len(entries)} 个角色。")


def _build_role(role_root: Path) -> dict[str, object]:
    manifest = load_and_validate_role_package(role_root)
    role_id = role_root.name
    version = str(manifest["version"])
    package_name = f"{role_id}-{version}.zip"
    package_target = DIST_ROOT / "packages" / package_name
    package_target.parent.mkdir(parents=True, exist_ok=True)
    _write_package(role_root, package_target)
    return {
        "id": role_id,
        "name": manifest["name"],
        "version": version,
        "author": manifest["author"]["name"],
        "summary": manifest["summary"],
        "license": manifest["license"],
        "packageUrl": f"packages/{package_name}",
        "sha256": _sha256(package_target),
        "size": package_target.stat().st_size,
        "compatibility": manifest["compatibility"],
    }


def _write_package(role_root: Path, target: Path) -> None:
    with ZipFile(target, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for file_name in sorted(PACKAGE_FILES):
            data = (role_root / file_name).read_bytes()
            entry = ZipInfo(
                (PurePosixPath(role_root.name) / file_name).as_posix(),
                date_time=(1980, 1, 1, 0, 0, 0),
            )
            entry.compress_type = ZIP_DEFLATED
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data, compresslevel=9)


def _reset_dist() -> None:
    resolved = DIST_ROOT.resolve()
    require(resolved.parent == REPOSITORY_ROOT.resolve(), "dist 目录越界。")
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True)


def _market_updated_at() -> str:
    explicit = os.environ.get("MARKET_UPDATED_AT", "").strip()
    if explicit:
        return datetime.fromisoformat(explicit.replace("Z", "+00:00")).astimezone(UTC).isoformat()
    try:
        value = subprocess.check_output(
            ["git", "show", "-s", "--format=%cI", "HEAD"],
            cwd=REPOSITORY_ROOT,
            text=True,
        ).strip()
        return datetime.fromisoformat(value).astimezone(UTC).isoformat()
    except (OSError, subprocess.CalledProcessError, ValueError):
        return "1970-01-01T00:00:00+00:00"


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


if __name__ == "__main__":
    main()
