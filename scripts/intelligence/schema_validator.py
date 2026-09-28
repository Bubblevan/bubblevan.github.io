from __future__ import annotations

from datetime import datetime
from functools import lru_cache
import json
from pathlib import Path
import re
from typing import Any


SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas" / "intelligence"
_SUPPORTED_KEYWORDS = {
    "$schema", "$id", "title", "type", "const", "enum", "pattern", "minLength",
    "minimum", "maximum", "format", "required", "properties", "additionalProperties", "items",
    "oneOf", "minItems",
}


class SchemaValidationError(ValueError):
    pass


@lru_cache(maxsize=None)
def _load_schema(kind: str) -> dict[str, Any]:
    if kind not in {
        "source", "observation", "artifact", "artifact_alias", "entity", "feedback", "topic",
        "graph_edge", "entity_alias", "source_candidate", "feed_profile", "feed_run", "feedback_v2",
    }:
        raise ValueError(f"unsupported schema kind: {kind}")
    path = SCHEMA_DIR / f"{kind}.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def validate_record(kind: str, record: object) -> None:
    if kind == "feedback" and isinstance(record, dict):
        schema_id = str(record.get("schema") or "")
        kind = "feedback_v2" if schema_id == "bubblevan/intelligence-feedback/v2" else "feedback"
    validate_instance(record, _load_schema(kind))


def validate_instance(instance: object, schema: dict[str, Any], path: str = "$") -> None:
    """Validate the JSON Schema keywords used by M0 without network/packages."""
    unknown = set(schema) - _SUPPORTED_KEYWORDS
    if unknown:
        raise SchemaValidationError(f"{path}: unsupported schema keyword(s): {sorted(unknown)}")

    expected_type = schema.get("type")
    valid_types = [expected_type] if isinstance(expected_type, str) else expected_type or []
    if valid_types and not any(_has_json_type(instance, str(item)) for item in valid_types):
        raise SchemaValidationError(f"{path}: expected {valid_types}, got {type(instance).__name__}")
    if "const" in schema and instance != schema["const"]:
        raise SchemaValidationError(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        raise SchemaValidationError(f"{path}: value {instance!r} is not in enum")
    if "oneOf" in schema:
        matches = 0
        for branch in schema["oneOf"]:
            try:
                validate_instance(instance, branch, path)
            except SchemaValidationError:
                continue
            matches += 1
        if matches != 1:
            raise SchemaValidationError(f"{path}: expected exactly one oneOf branch, matched {matches}")

    if isinstance(instance, str):
        if len(instance) < int(schema.get("minLength", 0)):
            raise SchemaValidationError(f"{path}: string is shorter than minLength")
        if "pattern" in schema and re.search(str(schema["pattern"]), instance) is None:
            raise SchemaValidationError(f"{path}: string does not match {schema['pattern']!r}")
        if schema.get("format") == "date-time":
            try:
                parsed = datetime.fromisoformat(instance.replace("Z", "+00:00"))
            except ValueError as exc:
                raise SchemaValidationError(f"{path}: invalid date-time") from exc
            if parsed.tzinfo is None:
                raise SchemaValidationError(f"{path}: date-time must include a timezone")
        elif "format" in schema:
            raise SchemaValidationError(f"{path}: unsupported format {schema['format']!r}")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool) and "minimum" in schema:
        if instance < schema["minimum"]:
            raise SchemaValidationError(f"{path}: value is below minimum")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool) and "maximum" in schema:
        if instance > schema["maximum"]:
            raise SchemaValidationError(f"{path}: value is above maximum")

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                raise SchemaValidationError(f"{path}: missing required property {key!r}")
        properties = schema.get("properties", {})
        for key, value in instance.items():
            if key in properties:
                validate_instance(value, properties[key], f"{path}.{key}")
            elif schema.get("additionalProperties") is False:
                raise SchemaValidationError(f"{path}: unexpected property {key!r}")
            elif isinstance(schema.get("additionalProperties"), dict):
                validate_instance(value, schema["additionalProperties"], f"{path}.{key}")

    if isinstance(instance, list) and isinstance(schema.get("items"), dict):
        if len(instance) < int(schema.get("minItems", 0)):
            raise SchemaValidationError(f"{path}: array is shorter than minItems")
        for index, value in enumerate(instance):
            validate_instance(value, schema["items"], f"{path}[{index}]")


def _has_json_type(value: object, expected: str) -> bool:
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(expected, False)
