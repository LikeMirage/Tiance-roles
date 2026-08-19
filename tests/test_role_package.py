from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from role_package import MarketBuildError, load_and_validate_role_package  # noqa: E402


class RolePackageTests(unittest.TestCase):
    def test_valid_role_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "test-role"
            _write_role(root)
            manifest = load_and_validate_role_package(root)
            self.assertEqual(manifest["id"], "test-role")

    def test_private_workspace_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "test-role"
            _write_role(root)
            (root / ".Tiance").mkdir()
            with self.assertRaises(MarketBuildError):
                load_and_validate_role_package(root)

    def test_unknown_configuration_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "test-role"
            _write_role(root)
            profile = json.loads((root / "profile.json").read_text(encoding="utf-8"))
            profile["unexpected"] = True
            _write_json(root / "profile.json", profile)
            with self.assertRaises(MarketBuildError):
                load_and_validate_role_package(root)


def _write_role(root: Path) -> None:
    root.mkdir()
    payloads = {
        "manifest.json": {
            "schemaVersion": 1,
            "kind": "tiance-role-package",
            "id": root.name,
            "name": "Test Role",
            "version": "1.0.0",
            "author": {"name": "Tester"},
            "summary": "Temporary contract fixture.",
            "license": "CC0-1.0",
            "compatibility": {"minTianceVersion": "0.1.0"},
        },
        "profile.json": {"description": "Test"},
        "model.json": {"provider_id": "", "model_id": "", "reasoning_mode": None},
        "generation.json": {"temperature": None, "top_p": None, "max_output_tokens": 4096},
        "prompt.json": {"system_prompt": "Test"},
        "response.json": {
            "return_cancelled_messages": True,
            "return_user_before_cancelled": True,
            "streaming_enabled": True,
            "auto_collapse_assistant_process": False,
            "malformed_tool_call_recovery_enabled": True,
            "upstream_retry_count": 1,
        },
        "context.json": {"inject_message_timestamps": False},
        "memory.json": {
            "global_memory_enabled": False,
            "global_memory_extraction_enabled": False,
            "project_memory_enabled": False,
            "project_memory_extraction_enabled": False,
            "memory_compression_enabled": True,
            "memory_context_token_trigger_threshold": 24000,
            "memory_raw_context_token_reserve": 12000,
        },
        "tools.json": {"tools_enabled": False, "enabled_tool_names": None, "max_tool_calls": 8},
    }
    for name, payload in payloads.items():
        _write_json(root / name, payload)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
