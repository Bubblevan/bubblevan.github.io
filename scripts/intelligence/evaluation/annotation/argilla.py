from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from .base import AnnotationAdapter, annotation_records, import_judgments


class ArgillaAdapter:
    """Optional Argilla server adapter; credentials are read only from environment."""

    def export(self, pack: Mapping[str, Any], target: Any = None) -> Mapping[str, Any]:
        rg, client = self._argilla()
        records = annotation_records(pack, display_fallbacks=target if isinstance(target, Mapping) else None)
        dataset_name = _dataset_name(pack)
        dataset, created = _get_or_create_dataset(rg, client, dataset_name)
        existing = _records_with_responses(dataset)
        expected = {record["external_id"]: record["metadata"] for record in records}
        existing_by_external = {
            str(_value(record, "id") or ""): record
            for record in existing if _value(record, "id")
        }
        if len(existing_by_external) != len(existing):
            raise ValueError("Argilla dataset contains duplicate record IDs")
        for external_id, record in existing_by_external.items():
            if external_id not in expected:
                raise ValueError("Argilla dataset contains an unknown record ID")
            metadata = _value(record, "metadata") or {}
            if any(str(metadata.get(key) or "") != str(expected[external_id].get(key) or "")
                   for key in ("benchmark_hash", "corpus_hash", "query_id", "artifact_id")):
                raise ValueError("Argilla record identity metadata does not match the blind pack")
        to_add = [record for record in records if record["external_id"] not in existing_by_external]
        argilla_records = [rg.Record(id=record["external_id"], fields=record["fields"],
                                     metadata=record["metadata"])
                           for record in to_add]
        if argilla_records:
            dataset.records.log(argilla_records)
        after = _records_with_responses(dataset)
        after_ids = [str(_value(record, "id") or "") for record in after]
        return {"dataset": dataset_name, "created": created, "records_total": len(records),
                "records_added": len(to_add), "duplicates": len(after_ids) - len(set(after_ids)),
                "records_present": len(set(after_ids)), "preserved_existing": len(existing_by_external)}

    def import_labels(self, pack: Mapping[str, Any], source: Any, target: str | Path, *,
                      reviewed_by: str | None = None, reviewed_at: str | None = None,
                      judge_type: str = "human", judge_name: str | None = None,
                      judge_model: str | None = None) -> Mapping[str, Any]:
        rg, client = self._argilla()
        dataset_name = str(source or _dataset_name(pack))
        dataset = _load_dataset(rg, client, dataset_name)
        expected_external = {row["external_id"]: row["metadata"] for row in annotation_records(pack)}
        rows = []
        for record in _records_with_responses(dataset):
            external_id = str(_value(record, "id") or "")
            identity = expected_external.get(external_id)
            metadata = _value(record, "metadata") or {}
            if identity is None:
                # Unknown records are forwarded as invalid identities so import fails closed.
                identity = {"benchmark_hash": metadata.get("benchmark_hash", ""),
                            "corpus_hash": metadata.get("corpus_hash", ""),
                            "query_id": metadata.get("query_id", ""),
                            "artifact_id": metadata.get("artifact_id", "")}
            elif any(str(metadata.get(key) or "") != str(identity.get(key) or "")
                     for key in ("benchmark_hash", "corpus_hash", "query_id", "artifact_id")):
                identity = dict(metadata)
            responses = _response_map(_value(record, "responses"))
            rows.append({"benchmark_hash": identity.get("benchmark_hash"),
                         "corpus_hash": identity.get("corpus_hash"),
                         "query_id": identity.get("query_id"),
                         "artifact_id": identity.get("artifact_id"),
                         "external_id": external_id,
                         "grade": responses.get("relevance"),
                         "quality_issue": responses.get("quality_issue")})
        qrels_path = Path(target)
        import json
        existing = json.loads(qrels_path.read_text(encoding="utf-8")) if qrels_path.exists() else None
        qrels, report = import_judgments(pack, rows, reviewed_by=reviewed_by, reviewed_at=reviewed_at,
                                         existing_qrels=existing, judge_type=judge_type,
                                         judge_name=judge_name, judge_model=judge_model)
        _write_json(qrels_path, qrels)
        return report

    @staticmethod
    def _argilla():
        api_url = os.environ.get("ARGILLA_API_URL", "").strip()
        api_key = os.environ.get("ARGILLA_API_KEY", "").strip()
        if not api_url or not api_key:
            raise RuntimeError("ARGILLA_API_URL and ARGILLA_API_KEY must be configured in the environment")
        try:
            import argilla as rg
            client = rg.Argilla(api_url=api_url, api_key=api_key)
        except Exception as exc:
            raise RuntimeError(f"Argilla initialization failed ({type(exc).__name__})") from None
        return rg, client


def _get_or_create_dataset(rg, client, name: str):
    try:
        dataset = _load_dataset(rg, client, name)
        return dataset, False
    except Exception:
        pass
    try:
        settings = rg.Settings(
            allow_extra_metadata=True,
            fields=[rg.TextField(name="query", title="Query", client=client),
                    rg.TextField(name="category", title="Category", client=client),
                    rg.TextField(name="specificity", title="Specificity", client=client),
                    rg.TextField(name="artifact_id", title="Artifact ID", client=client),
                    rg.TextField(name="artifact_type", title="Artifact type", client=client),
                    rg.TextField(name="title", title="Title", client=client),
                    rg.TextField(name="canonical_url", title="Canonical URL", client=client),
                    rg.TextField(name="published_at", title="Published at", client=client),
                    rg.TextField(name="summary_excerpt", title="Summary / excerpt", client=client)],
            questions=[rg.LabelQuestion(name="relevance", title="Relevance",
                                        labels={"0": "Irrelevant", "1": "Useful", "2": "Directly important"},
                                        client=client),
                       rg.LabelQuestion(name="quality_issue", title="Optional quality issue",
                                        labels={"insufficient_metadata": "Insufficient metadata",
                                                "broken_url": "Broken URL",
                                                "suspected_duplicate": "Suspected duplicate",
                                                "identity_problem": "Identity problem", "none": "None"},
                                        required=False, client=client)],
        )
        dataset = rg.Dataset(name=name, workspace=os.environ.get("ARGILLA_WORKSPACE", "default"),
                             settings=settings, client=client)
        dataset.create()
        return dataset, True
    except Exception as exc:
        raise RuntimeError(f"Argilla dataset setup failed ({type(exc).__name__})") from None


def _load_dataset(rg, client, name: str):
    try:
        dataset = rg.Dataset(name=name, workspace=os.environ.get("ARGILLA_WORKSPACE", "default"), client=client)
        return dataset.get()
    except Exception as exc:
        raise RuntimeError(f"Argilla dataset lookup failed ({type(exc).__name__})") from None


def _records_with_responses(dataset):
    try:
        return list(dataset.records(with_responses=True))
    except TypeError:
        try:
            return list(dataset.records(with_responses=True, include_responses=True))
        except Exception as exc:
            raise RuntimeError(f"Argilla record retrieval failed ({type(exc).__name__})") from None
    except Exception as exc:
        raise RuntimeError(f"Argilla record retrieval failed ({type(exc).__name__})") from None


def _response_map(responses: Any) -> dict[str, Any]:
    if isinstance(responses, Mapping):
        result = {}
        for key, value in responses.items():
            result[str(key)] = _response_value(value)
        return result
    result = {}
    if isinstance(responses, (list, tuple)):
        for response in responses:
            name = _value(response, "question_name") or _value(response, "name")
            if name:
                result[str(name)] = _response_value(response)
    return result


def _response_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return value.get("value", value.get("values"))
    return getattr(value, "value", getattr(value, "values", value))


def _value(item: Any, key: str) -> Any:
    return item.get(key) if isinstance(item, Mapping) else getattr(item, key, None)


def _dataset_name(pack: Mapping[str, Any]) -> str:
    return f"ri-{pack.get('benchmark_id', 'dev-v1')}-{str(pack['benchmark_hash'])[:12]}"


def _write_json(path: str | Path, value: Mapping[str, Any]) -> None:
    import json
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
