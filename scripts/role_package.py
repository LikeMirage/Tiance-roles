from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROLE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
SEMVER_PATTERN = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?$"
)
CONFIG_FILES = {
    "profile.json",
    "model.json",
    "generation.json",
    "prompt.json",
    "response.json",
    "context.json",
    "memory.json",
    "tools.json",
}
PACKAGE_FILES = {"manifest.json", *CONFIG_FILES}
REASONING_MODES = {"default", "auto", "enabled", "off", "low", "medium", "high", "max"}


class MarketBuildError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise MarketBuildError(message)


def load_and_validate_role_package(role_root: Path) -> dict[str, Any]:
    role_id = role_root.name
    require(ROLE_ID_PATTERN.fullmatch(role_id) is not None, f"非法角色目录名：{role_id}")
    entries = list(role_root.iterdir())
    require(all(path.is_file() and not path.is_symlink() for path in entries), f"{role_id} 只允许九个普通文件。")
    require({path.name for path in entries} == PACKAGE_FILES, f"{role_id} 的文件不完整或存在多余文件。")
    manifest = _read_object(role_root / "manifest.json")
    _validate_manifest(role_id, manifest)
    _validate_configs(role_root)
    return manifest


def _validate_manifest(role_id: str, manifest: dict[str, Any]) -> None:
    expected = {
        "schemaVersion", "kind", "id", "name", "version", "author", "summary",
        "license", "compatibility",
    }
    require(set(manifest) == expected, f"{role_id} 的 manifest 字段不完整或存在多余字段。")
    require(manifest["schemaVersion"] == 1, f"{role_id} 的 manifest 版本非法。")
    require(manifest["kind"] == "tiance-role-package", f"{role_id} 的包类型非法。")
    require(manifest["id"] == role_id, f"{role_id} 的 manifest.id 与目录名不一致。")
    _require_text(manifest["name"], 80, f"{role_id} 缺少名称。")
    require(SEMVER_PATTERN.fullmatch(str(manifest["version"])) is not None, f"{role_id} 的版本号非法。")
    author = manifest["author"]
    require(isinstance(author, dict) and set(author) == {"name"}, f"{role_id} 的 author 非法。")
    _require_text(author["name"], 80, f"{role_id} 缺少作者。")
    _require_text(manifest["summary"], 300, f"{role_id} 缺少简介。")
    _require_text(manifest["license"], 80, f"{role_id} 缺少许可证。")
    compatibility = manifest["compatibility"]
    require(
        isinstance(compatibility, dict) and set(compatibility) == {"minTianceVersion"},
        f"{role_id} 的兼容信息非法。",
    )
    require(
        SEMVER_PATTERN.fullmatch(str(compatibility["minTianceVersion"])) is not None,
        f"{role_id} 的最低天策版本非法。",
    )


def _validate_configs(root: Path) -> None:
    role_id = root.name
    profile = _read_exact(root / "profile.json", {"description"})
    _require_type(profile["description"], str, f"{role_id} 的 description 非法。")

    model = _read_exact(root / "model.json", {"provider_id", "model_id", "reasoning_mode"})
    _require_type(model["provider_id"], str, f"{role_id} 的 provider_id 非法。")
    _require_type(model["model_id"], str, f"{role_id} 的 model_id 非法。")
    require(
        model["reasoning_mode"] is None or model["reasoning_mode"] in REASONING_MODES,
        f"{role_id} 的 reasoning_mode 非法。",
    )

    generation = _read_exact(root / "generation.json", {"temperature", "top_p", "max_output_tokens"})
    _require_number_or_none(generation["temperature"], 0, 2, f"{role_id} 的 temperature 非法。")
    _require_number_or_none(generation["top_p"], 0, 1, f"{role_id} 的 top_p 非法。")
    _require_int(generation["max_output_tokens"], 1, f"{role_id} 的 max_output_tokens 非法。")

    prompt = _read_exact(root / "prompt.json", {"system_prompt"})
    _require_type(prompt["system_prompt"], str, f"{role_id} 的 system_prompt 非法。")

    response = _read_exact(root / "response.json", {
        "return_cancelled_messages", "return_user_before_cancelled",
        "streaming_enabled", "auto_collapse_assistant_process",
        "malformed_tool_call_recovery_enabled", "upstream_retry_count",
    })
    _require_booleans(response, role_id, exclude={"upstream_retry_count"})
    _require_int(response["upstream_retry_count"], 0, f"{role_id} 的上游重试次数非法。")

    context = _read_exact(root / "context.json", {"inject_message_timestamps"})
    _require_booleans(context, role_id)

    memory = _read_exact(root / "memory.json", {
        "global_memory_enabled", "global_memory_extraction_enabled", "project_memory_enabled",
        "project_memory_extraction_enabled", "memory_compression_enabled",
        "memory_context_token_trigger_threshold", "memory_raw_context_token_reserve",
    })
    _require_booleans(memory, role_id, exclude={
        "memory_context_token_trigger_threshold", "memory_raw_context_token_reserve",
    })
    _require_int(memory["memory_context_token_trigger_threshold"], 1, f"{role_id} 的记忆阈值非法。")
    _require_int(memory["memory_raw_context_token_reserve"], 0, f"{role_id} 的记忆保留量非法。")

    tools = _read_exact(root / "tools.json", {"tools_enabled", "enabled_tool_names", "max_tool_calls"})
    require(type(tools["tools_enabled"]) is bool, f"{role_id} 的 tools_enabled 非法。")
    names = tools["enabled_tool_names"]
    require(names is None or (isinstance(names, list) and all(isinstance(item, str) for item in names)), f"{role_id} 的工具列表非法。")
    _require_int(tools["max_tool_calls"], 1, f"{role_id} 的 max_tool_calls 非法。")


def _read_exact(path: Path, keys: set[str]) -> dict[str, Any]:
    payload = _read_object(path)
    require(set(payload) == keys, f"{path.parent.name}/{path.name} 字段不完整或存在多余字段。")
    return payload


def _read_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MarketBuildError(f"无法读取 JSON：{path.parent.name}/{path.name}") from exc
    require(isinstance(payload, dict), f"JSON 顶层必须是对象：{path.parent.name}/{path.name}")
    return payload


def _require_text(value: Any, maximum: int, message: str) -> None:
    require(isinstance(value, str) and bool(value.strip()) and len(value) <= maximum, message)


def _require_type(value: Any, expected: type, message: str) -> None:
    require(type(value) is expected, message)


def _require_number_or_none(value: Any, minimum: float, maximum: float, message: str) -> None:
    require(value is None or (type(value) in {int, float} and minimum <= value <= maximum), message)


def _require_int(value: Any, minimum: int, message: str) -> None:
    require(type(value) is int and value >= minimum, message)


def _require_booleans(payload: dict[str, Any], role_id: str, exclude: set[str] | None = None) -> None:
    ignored = exclude or set()
    require(all(type(value) is bool for key, value in payload.items() if key not in ignored), f"{role_id} 包含非法布尔配置。")

