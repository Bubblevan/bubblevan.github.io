from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from typing import Any

from ..ids import stable_id
from ..graph.store import GraphStore
from ..models import now_utc
from ..repositories.artifacts import ArtifactRepository
from ..schema_validator import validate_record
from ..store import JsonlStore
from .evidence.base import EvidenceBudget
from .evidence.local_corpus import LocalCorpusEvidenceBackend
from .ids import evidence_ref
from .rendering import render_brief_markdown, render_promotion_markdown
from .synthesis import LiteLLMAdapter, SynthesisAdapter, prompt_hashes


SESSION_SCHEMA = "bubblevan/research-session/v1"
BRIEF_SCHEMA = "bubblevan/research-brief/v1"
EVIDENCE_SET_SCHEMA = "bubblevan/research-evidence-set/v1"
_SESSION_ID = re.compile(r"^rs-[0-9a-f]{24}$")


class ResearchService:
    """Private research-session lifecycle; synthesis never writes Source/Observation records."""

    def __init__(self, store_dir: str | Path, runtime_dir: str | Path, private_root: str | Path,
                 *, repository_root: str | Path | None = None, model_adapter: SynthesisAdapter | None = None,
                 evidence_backend: Any | None = None):
        self.store_dir = Path(store_dir)
        self.runtime_dir = Path(runtime_dir)
        self.private_dir = Path(private_root) / "research"
        self.sessions_dir = self.private_dir / "sessions"
        self.evidence_dir = self.private_dir / "evidence"
        self.briefs_dir = self.private_dir / "briefs"
        self.previews_dir = self.private_dir / "promotion-previews"
        self.repository_root = Path(repository_root).resolve() if repository_root else self.store_dir.resolve().parents[2]
        self.model_adapter = model_adapter
        self.evidence_backend = evidence_backend
        self.store = JsonlStore(self.store_dir)
        self.artifacts = ArtifactRepository(self.store)
        for path in (self.sessions_dir, self.evidence_dir, self.briefs_dir, self.previews_dir):
            path.mkdir(parents=True, exist_ok=True)

    def start(self, question: str = "", *, artifact_ids: list[str] | None = None,
              source_feed_run_id: str | None = None, created_at: str | None = None) -> dict[str, Any]:
        seeds = sorted({self.artifacts.resolve_id(str(item)) for item in (artifact_ids or [])})
        snapshot_docs = {str(row["artifact_id"]): row for row in self.artifacts.iter_canonical()}
        unknown = sorted(set(seeds) - set(snapshot_docs))
        if unknown:
            raise ValueError(f"unknown research seed Artifact ID(s): {unknown}")
        question = str(question or "").strip()
        if not question and seeds:
            names = [str(snapshot_docs[item].get("title") or item) for item in seeds[:3]]
            question = "Research the selected Artifact(s): " + "; ".join(names)
        if not question:
            raise ValueError("research session needs a question or at least one seed Artifact")
        if len(question) > 2000:
            raise ValueError("research question must not exceed 2000 characters")
        stamp = _timestamp(created_at or now_utc())
        session_id = stable_id("rs", "research-session", f"{stamp}|{question}|{'|'.join(seeds)}")
        path = self.sessions_dir / f"{session_id}.json"
        if path.exists():
            existing = self.get_session(session_id)
            return existing
        session = {
            "schema": SESSION_SCHEMA,
            "research_session_id": session_id,
            "question": question,
            "seed_artifact_ids": seeds,
            "source_feed_run_id": source_feed_run_id,
            "status": "draft",
            "created_at": stamp,
            "updated_at": stamp,
            "corpus_hash": None,
            "retrieval_config": {},
            "model_config": {},
            "prompt_hashes": {},
            "evidence_set_hash": None,
            "evidence_path": None,
            "brief_revision": 0,
            "reviewed_by": None,
            "reviewed_at": None,
            "approved_by": None,
            "approved_at": None,
            "promoted_path": None,
        }
        validate_record("research_session", session)
        _atomic_json(path, session)
        return session

    def get_session(self, session_id: str) -> dict[str, Any]:
        path = self._session_path(session_id)
        row = _read_json(path)
        validate_record("research_session", row)
        return row

    def list_sessions(self) -> list[dict[str, Any]]:
        rows = [self.get_session(path.stem) for path in sorted(self.sessions_dir.glob("rs-*.json"))]
        return sorted(rows, key=lambda row: (row["created_at"], row["research_session_id"]), reverse=True)

    def collect_evidence(self, session_id: str, *, budget: EvidenceBudget | None = None,
                         paper_files: dict[str, str | Path] | None = None) -> dict[str, Any]:
        session = self.get_session(session_id)
        backend = self.evidence_backend or LocalCorpusEvidenceBackend(self.store_dir, self.runtime_dir)
        budget = budget or EvidenceBudget()
        refs = backend.gather(session["question"], list(session["seed_artifact_ids"]), budget)
        paperqa_status = "not_requested"
        if paper_files:
            try:
                from .evidence.paperqa import PaperQA2EvidenceBackend
                used_chars = sum(len(str(row["text"])) for row in refs)
                paper_budget = EvidenceBudget(
                    max_retrieved_artifacts=budget.max_retrieved_artifacts,
                    max_evidence_artifacts=budget.max_evidence_artifacts,
                    max_evidence_refs=max(0, budget.max_evidence_refs - len(refs)),
                    max_refs_per_artifact=budget.max_refs_per_artifact,
                    max_evidence_chars=max(0, budget.max_evidence_chars - used_chars),
                )
                if paper_budget.max_evidence_refs:
                    paper_backend = PaperQA2EvidenceBackend(self.store_dir, paper_files, self.runtime_dir)
                    paper_refs = paper_backend.gather(session["question"], list(session["seed_artifact_ids"]), paper_budget)
                    refs.extend(paper_refs)
                    paperqa_status = "succeeded" if paper_refs else "no_local_full_text_match"
                else:
                    paperqa_status = "skipped:evidence_budget_exhausted"
            except Exception as exc:
                # The optional backend never blocks local evidence collection, and error text is not persisted.
                paperqa_status = f"unavailable:{type(exc).__name__}"
        broken = self._validate_evidence(refs)
        if broken:
            raise ValueError(f"evidence packet contains {broken} broken reference(s)")
        evidence_hash = _evidence_set_hash(refs)
        revision = 1
        for path in self.evidence_dir.glob(f"{session_id}-evidence-*.json"):
            match = re.search(r"-evidence-(\d+)\.json$", path.name)
            if match:
                revision = max(revision, int(match.group(1)) + 1)
        evidence_path = self.evidence_dir / f"{session_id}-evidence-{revision:04d}.json"
        record = {"schema": EVIDENCE_SET_SCHEMA, "research_session_id": session_id,
                  "revision": revision, "corpus_hash": getattr(backend, "last_retrieval", {}).get("corpus_hash"),
                  "evidence_set_hash": evidence_hash, "evidence_refs": refs,
                  "retrieval": {**getattr(backend, "last_retrieval", {}),
                                "paperqa_status": paperqa_status}, "created_at": now_utc()}
        _atomic_json(evidence_path, record)
        session.update({
            "status": "evidence_ready", "updated_at": now_utc(),
            "corpus_hash": record["corpus_hash"], "evidence_set_hash": evidence_hash,
            "evidence_path": evidence_path.relative_to(self.private_dir).as_posix(),
            "retrieval_config": {"budget": budget.__dict__, "retrieval": record["retrieval"]},
            "reviewed_by": None, "reviewed_at": None, "approved_by": None, "approved_at": None,
        })
        self._save_session(session)
        return {"status": "evidence_ready", "research_session_id": session_id,
                "evidence_count": len(refs), "evidence_artifacts": len({row["artifact_id"] for row in refs}),
                "evidence_set_hash": evidence_hash, "corpus_hash": record["corpus_hash"],
                "retrieval": record["retrieval"], "path": str(evidence_path)}

    def load_evidence(self, session: dict[str, Any] | str) -> list[dict[str, Any]]:
        row = self.get_session(session) if isinstance(session, str) else session
        if not row.get("evidence_path"):
            raise ValueError("research session has no evidence packet; run research-evidence first")
        path = (self.private_dir / str(row["evidence_path"])).resolve()
        if not path.is_relative_to(self.private_dir.resolve()):
            raise ValueError("evidence path escapes private research storage")
        record = _read_json(path)
        refs = record.get("evidence_refs")
        if not isinstance(refs, list):
            raise ValueError("research evidence packet is malformed")
        self._validate_evidence(refs, raise_on_broken=True)
        if _evidence_set_hash(refs) != row.get("evidence_set_hash"):
            raise ValueError("research evidence set hash no longer matches the session")
        return refs

    def generate(self, session_id: str, *, model_adapter: SynthesisAdapter | None = None) -> dict[str, Any]:
        session = self.get_session(session_id)
        evidence = self.load_evidence(session)
        adapter = model_adapter or self.model_adapter or LiteLLMAdapter.from_environment()
        if adapter is None:
            return {"status": "synthesis_unavailable", "reason": "no RESEARCH_MODEL/RI_RESEARCH_MODEL configured in the process environment",
                    "evidence_count": len(evidence), "evidence_set_hash": session.get("evidence_set_hash")}
        prompts = prompt_hashes(session["question"], evidence)
        try:
            result = adapter.synthesize(session["question"], evidence)
        except Exception as exc:
            return {"status": "synthesis_unavailable", "reason": type(exc).__name__,
                    "evidence_count": len(evidence), "evidence_set_hash": session.get("evidence_set_hash")}
        if not isinstance(result, dict) or not isinstance(result.get("payload"), dict):
            raise ValueError("synthesis adapter returned a malformed result")
        revision = int(session.get("brief_revision") or 0) + 1
        brief = self._normalize_brief(session, evidence, result["payload"], revision,
                                      result.get("model_provenance") or {}, prompts)
        path = self.briefs_dir / f"{session_id}-r{revision:04d}.json"
        _atomic_json(path, brief)
        markdown = render_brief_markdown(brief, evidence)
        _atomic_text(path.with_suffix(".md"), markdown)
        session.update({"status": "synthesized", "updated_at": now_utc(), "brief_revision": revision,
                        "model_config": brief["model_provenance"], "prompt_hashes": prompts})
        self._save_session(session)
        return {"status": "synthesized", "research_session_id": session_id, "revision": revision,
                "brief_path": str(path), "markdown_path": str(path.with_suffix('.md')),
                "evidence_set_hash": brief["evidence_set_hash"], "metrics": brief["metrics"]}

    def get_brief(self, session_id: str, revision: int | None = None) -> dict[str, Any]:
        session = self.get_session(session_id)
        revision = revision or int(session.get("brief_revision") or 0)
        if revision < 1:
            raise ValueError("research session has no generated brief")
        path = self.briefs_dir / f"{session_id}-r{revision:04d}.json"
        brief = _read_json(path)
        validate_record("research_brief", brief)
        for claim in brief.get("claims", []):
            validate_record("research_claim", claim)
        return brief

    def review(self, session_id: str, *, reviewer: str) -> dict[str, Any]:
        reviewer = str(reviewer).strip()
        if not reviewer:
            raise ValueError("reviewer is required")
        session = self.get_session(session_id)
        brief = self.get_brief(session_id)
        if brief.get("evidence_set_hash") != session.get("evidence_set_hash"):
            raise ValueError("latest brief is stale for the current evidence set; generate a new revision first")
        self.load_evidence(session)
        brief["status"] = "reviewed"
        _atomic_json(self.briefs_dir / f"{session_id}-r{brief['revision']:04d}.json", brief)
        session.update({"status": "reviewed", "reviewed_by": reviewer,
                        "reviewed_at": now_utc(), "updated_at": now_utc()})
        self._save_session(session)
        return {"status": "reviewed", "research_session_id": session_id,
                "revision": brief["revision"], "reviewed_by": reviewer, "metrics": brief["metrics"]}

    def approve(self, session_id: str, *, approver: str) -> dict[str, Any]:
        approver = str(approver).strip()
        if not approver:
            raise ValueError("approver is required")
        session = self.get_session(session_id)
        if session["status"] != "reviewed":
            raise ValueError("only a human-reviewed research brief can be approved")
        brief = self.get_brief(session_id)
        if brief.get("evidence_set_hash") != session.get("evidence_set_hash"):
            raise ValueError("brief evidence set changed; generate and review a new revision")
        self.load_evidence(session)
        metrics = brief.get("metrics", {})
        if int(metrics.get("unsupported_fact_count", -1)) != 0:
            raise ValueError("unsupported factual claims block approval")
        if int(metrics.get("broken_citation_count", -1)) != 0:
            raise ValueError("broken citations block approval")
        if int(metrics.get("missing_evidence_count", -1)) != 0:
            raise ValueError("missing evidence blocks approval")
        previews = [path for path in self.previews_dir.glob("pv-*.json")
                    if (candidate := _read_json(path)).get("research_session_id") == session_id
                    and int(candidate.get("revision", 0)) == int(brief["revision"])
                    and bool((candidate.get("gate") or {}).get("eligible"))]
        if not previews:
            raise ValueError("create and inspect an eligible private promotion preview before approval")
        brief["status"] = "approved"
        _atomic_json(self.briefs_dir / f"{session_id}-r{brief['revision']:04d}.json", brief)
        session.update({"status": "approved", "approved_by": approver,
                        "approved_at": now_utc(), "updated_at": now_utc()})
        self._save_session(session)
        return {"status": "approved", "research_session_id": session_id,
                "revision": brief["revision"], "approved_by": approver}

    def promotion_preview(self, session_id: str, *, target: str, title: str | None = None,
                          topics: list[str] | None = None) -> dict[str, Any]:
        session = self.get_session(session_id)
        brief = self.get_brief(session_id)
        if brief.get("evidence_set_hash") != session.get("evidence_set_hash"):
            raise ValueError("brief evidence set changed; generate a new revision before preview")
        evidence = self.load_evidence(session)
        canonical_target = self._validate_target(target)
        gate = self._promotion_gate(brief, evidence)
        markdown = render_promotion_markdown(session, brief, evidence, target=canonical_target,
                                             title=title, topics=topics or [])
        preview_id = stable_id("pv", "research-promotion-preview", f"{session_id}|{brief['revision']}|{canonical_target}|{brief['output_hash']}")
        preview_path = self.previews_dir / f"{preview_id}.json"
        record = {"schema": "bubblevan/research-promotion-preview/v1", "preview_id": preview_id,
                  "research_session_id": session_id, "revision": brief["revision"], "target": canonical_target,
                  "title": title or session["question"], "markdown": markdown, "gate": gate,
                  "created_at": now_utc()}
        _atomic_json(preview_path, record)
        _atomic_text(preview_path.with_suffix(".md"), markdown)
        return {"status": "preview_ready" if gate["eligible"] else "preview_blocked",
                "preview_id": preview_id, "preview_path": str(preview_path),
                "markdown_path": str(preview_path.with_suffix('.md')), "target": canonical_target,
                "front_matter": markdown.split("---\n", 2)[1] if markdown.startswith("---\n") else "",
                "gate": gate}

    def promote(self, session_id: str, *, target: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        already_promoted = session["status"] == "promoted" and session.get("promoted_path") == target
        if session["status"] != "approved" and not already_promoted:
            raise ValueError("research-promote requires explicit research-approve first")
        target = self._validate_target(target)
        brief = self.get_brief(session_id)
        if brief.get("evidence_set_hash") != session.get("evidence_set_hash"):
            raise ValueError("brief evidence set changed; regenerate before promotion")
        evidence = self.load_evidence(session)
        gate = self._promotion_gate(brief, evidence)
        if not gate["eligible"]:
            raise ValueError("promotion blocked by structural quality gates")
        preview = self._find_preview(session_id, int(brief["revision"]), target)
        if not preview:
            raise ValueError("create a promotion preview for this exact target before promotion")
        path = (self.repository_root / target).resolve()
        if not path.is_relative_to(self.repository_root):
            raise ValueError("promotion target escapes the repository")
        payload = str(preview["markdown"])
        if path.exists():
            if path.read_text(encoding="utf-8") != payload:
                raise FileExistsError("promotion target already exists with different contents")
            outcome = "already_promoted"
        else:
            _atomic_text(path, payload)
            outcome = "promoted"
        event = {"schema": "bubblevan/research-event/v1", "event_id": stable_id(
                     "re", "research-promotion", f"{session_id}|{target}|{brief['output_hash']}"),
                 "action": "promote_to_hugo", "research_session_id": session_id,
                 "artifact_seed_ids": session["seed_artifact_ids"], "target_path": target,
                 "occurred_at": now_utc()}
        if not already_promoted:
            self._append_private_event(event)
            session.update({"status": "promoted", "promoted_path": target, "updated_at": now_utc()})
            self._save_session(session)
        return {"status": outcome, "research_session_id": session_id, "target": target,
                "path": str(path), "event_id": event["event_id"]}

    def _normalize_brief(self, session: dict[str, Any], evidence: list[dict[str, Any]], payload: dict[str, Any],
                         revision: int, provenance: dict[str, Any], prompts: dict[str, str]) -> dict[str, Any]:
        allowed = {str(row["evidence_id"]) for row in evidence}
        raw_claims = payload.get("claims") or []
        if not isinstance(raw_claims, list):
            raise ValueError("model claims must be an array")
        claims = []
        for index, raw in enumerate(raw_claims):
            if not isinstance(raw, dict) or not str(raw.get("text") or "").strip():
                continue
            evidence_ids = _string_list(raw.get("evidence_ids"))
            _reject_unknown_evidence(evidence_ids, allowed)
            claim_type = str(raw.get("claim_type") or "fact")
            if claim_type not in {"fact", "inference", "interpretation", "open_question"}:
                claim_type = "interpretation"
            confidence = str(raw.get("confidence") or "uncertain")
            if confidence not in {"supported", "uncertain", "unsupported"}:
                confidence = "uncertain"
            if claim_type == "fact" and not evidence_ids:
                confidence = "unsupported"
            claim = {"schema": "bubblevan/research-claim/v1",
                     "claim_id": stable_id("claim", "research-claim",
                                            f"{session['research_session_id']}|{revision}|{index}|{raw['text']}"),
                     "text": str(raw["text"]).strip(), "claim_type": claim_type,
                     "evidence_ids": evidence_ids, "confidence": confidence,
                     "notes": str(raw.get("notes") or "")[:2000]}
            validate_record("research_claim", claim)
            claims.append(claim)
        summary = str(payload.get("executive_summary") or "").strip()
        summary_ids = _string_list(payload.get("summary_evidence_ids"))
        _reject_unknown_evidence(summary_ids, allowed)
        disagreements = _normalize_linked_text(payload.get("disagreements"), allowed)
        implications = _normalize_linked_text(payload.get("practical_implications"), allowed)
        limitations = _string_list(payload.get("limitations"))
        open_questions = _string_list(payload.get("open_questions"))
        unsupported = sum(1 for claim in claims if claim["claim_type"] == "fact" and
                          (not claim["evidence_ids"] or claim["confidence"] != "supported"))
        missing_evidence = unsupported
        if summary and not summary_ids:
            missing_evidence += 1
        if any(not row["evidence_ids"] for row in disagreements):
            missing_evidence += sum(not row["evidence_ids"] for row in disagreements)
        broken = self._validate_evidence(evidence)
        all_ids = set(summary_ids)
        for claim in claims:
            all_ids.update(claim["evidence_ids"])
        for row in disagreements + implications:
            all_ids.update(row["evidence_ids"])
        evidence_by_id = {str(row["evidence_id"]): row for row in evidence}
        distinct_artifacts = {evidence_by_id[item]["artifact_id"] for item in all_ids if item in evidence_by_id}
        distinct_sources = {evidence_by_id[item]["source_id"] for item in all_ids
                            if item in evidence_by_id and evidence_by_id[item].get("source_id")}
        citation_count = len(summary_ids) + sum(len(row["evidence_ids"]) for row in claims)
        citation_count += sum(len(row["evidence_ids"]) for row in disagreements + implications)
        brief = {
            "schema": BRIEF_SCHEMA, "research_session_id": session["research_session_id"],
            "revision": revision, "status": "draft", "question": session["question"],
            "executive_summary": summary, "summary_evidence_ids": summary_ids,
            "key_findings": [row["claim_id"] for row in claims if row["confidence"] == "supported"][:10],
            "claims": claims, "disagreements": disagreements,
            "limitations": limitations, "open_questions": open_questions,
            "practical_implications": implications, "evidence_ids": sorted(all_ids),
            "evidence_set_hash": str(session.get("evidence_set_hash") or ""),
            "output_hash": "0" * 64,
            "model_provenance": {"provider": provenance.get("provider"), "model": provenance.get("model"),
                                 "model_revision": provenance.get("model_revision"),
                                 "temperature": provenance.get("temperature", 0),
                                 "request_id": provenance.get("request_id"),
                                 "started_at": provenance.get("started_at"),
                                 "completed_at": provenance.get("completed_at"),
                                 "input_tokens": provenance.get("input_tokens"),
                                 "output_tokens": provenance.get("output_tokens"),
                                 "cost": provenance.get("cost")},
            "prompt_hashes": prompts,
            "metrics": {"claim_count": len(claims),
                        "fact_claim_count": sum(row["claim_type"] == "fact" for row in claims),
                        "supported_fact_count": sum(row["claim_type"] == "fact" and row["confidence"] == "supported" for row in claims),
                        "unsupported_fact_count": unsupported,
                        "citation_count": citation_count,
                        "broken_citation_count": broken,
                        "missing_evidence_count": missing_evidence,
                        "distinct_artifact_count": len(distinct_artifacts),
                        "distinct_source_count": len(distinct_sources),
                        "evidence_set_hash": str(session.get("evidence_set_hash") or "")},
        }
        semantic = {key: value for key, value in brief.items() if key not in {"output_hash", "status"}}
        brief["output_hash"] = _hash(semantic)
        validate_record("research_brief", brief)
        return brief

    def _validate_evidence(self, refs: list[dict[str, Any]], *, raise_on_broken: bool = False) -> int:
        artifact_rows = {str(row["artifact_id"]): row for row in self.artifacts.iter_canonical()}
        observations = {str(row["observation_id"]): row for row in self.store.iter_records("observation")}
        graph_edge_ids = {str(row.get("locator", {}).get("value", "")).removeprefix("graph-edge:")
                          for row in refs if str(row.get("locator", {}).get("value", "")).startswith("graph-edge:")}
        graph_edges = ({str(row["edge_id"]): row for row in GraphStore(self.store_dir).iter_edges()
                        if str(row.get("edge_id")) in graph_edge_ids} if graph_edge_ids else {})
        broken = 0
        for row in refs:
            try:
                validate_record("evidence_ref", row)
                canonical_id = self.artifacts.resolve_id(str(row["artifact_id"]))
                if canonical_id != row["artifact_id"] or canonical_id not in artifact_rows:
                    raise ValueError("evidence Artifact does not resolve to a canonical record")
                if hashlib.sha256(str(row["text"]).encode("utf-8")).hexdigest() != row["text_sha256"]:
                    raise ValueError("evidence text hash mismatch")
                locator = row.get("locator") or {}
                locator_type = str(locator.get("type") or "")
                locator_value = str(locator.get("value") or "")
                if locator_type == "metadata" and locator_value in {"title", "summary"}:
                    original = str(artifact_rows[canonical_id].get(locator_value) or "")
                    if locator_value == "summary":
                        original = original[:4000]
                    if original != str(row["text"]):
                        raise ValueError("artifact metadata evidence has changed")
                observation_id = row.get("observation_id")
                if observation_id and observation_id not in observations:
                    raise ValueError("evidence Observation does not exist")
                if observation_id and locator_type == "observation":
                    observation = observations[observation_id]
                    current_text = "\n\n".join(part.strip() for part in
                                                  (str(observation.get("title") or ""), str(observation.get("text") or ""))
                                                  if part.strip())[:20_000]
                    if current_text != str(row["text"]):
                        raise ValueError("observation evidence text has changed")
                if locator_type == "section" and locator_value.startswith("graph-edge:"):
                    edge_id = locator_value.removeprefix("graph-edge:")
                    edge = graph_edges.get(edge_id)
                    if edge is None:
                        raise ValueError("graph evidence edge no longer exists")
                    relation_prefix = (f"Exact graph relation: {edge['subject_id']} --{edge['predicate']}--> "
                                       f"{edge['object_id']}; edge={edge['edge_id']}; evidence_type=")
                    if not any(str(row["text"]).startswith(relation_prefix)
                               and str(item.get("evidence_type") or "") in {"exact_provider_metadata", "explicit_source_link"}
                               for item in edge.get("evidence", [])):
                        raise ValueError("graph evidence is no longer backed by an exact edge")
            except (ValueError, KeyError, TypeError):
                broken += 1
        if broken and raise_on_broken:
            raise ValueError(f"research evidence contains {broken} invalid reference(s)")
        return broken

    def _promotion_gate(self, brief: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any]:
        broken = self._validate_evidence(evidence)
        metrics = brief.get("metrics", {})
        unsupported = int(metrics.get("unsupported_fact_count", -1))
        missing = int(metrics.get("missing_evidence_count", -1))
        recorded_broken = int(metrics.get("broken_citation_count", -1))
        broken = max(broken, recorded_broken)
        eligible = unsupported == 0 and missing == 0 and broken == 0
        return {"eligible": eligible, "unsupported_fact_count": unsupported,
                "missing_evidence_count": missing, "broken_citation_count": broken,
                "evidence_set_hash": brief.get("evidence_set_hash")}

    def _find_preview(self, session_id: str, revision: int, target: str) -> dict[str, Any] | None:
        for path in self.previews_dir.glob("pv-*.json"):
            row = _read_json(path)
            if (row.get("research_session_id") == session_id and int(row.get("revision", 0)) == revision
                    and row.get("target") == target):
                return row
        return None

    def _validate_target(self, target: str) -> str:
        relative = PurePosixPath(str(target).replace("\\", "/"))
        if relative.is_absolute() or ".." in relative.parts or relative.suffix.casefold() != ".md":
            raise ValueError("promotion target must be a relative Markdown path inside an allowed content section")
        allowed = ("content/docs/research/", "content/papers/", "content/blog/")
        normalized = relative.as_posix()
        if not normalized.startswith(allowed):
            raise ValueError("promotion target must be under content/docs/research, content/papers, or content/blog")
        resolved = (self.repository_root / normalized).resolve()
        allowed_root = next(self.repository_root / prefix.rstrip("/") for prefix in allowed
                            if normalized.startswith(prefix)).resolve()
        if not resolved.is_relative_to(allowed_root):
            raise ValueError("promotion target escapes its allowed content section")
        return normalized

    def _append_private_event(self, event: dict[str, Any]) -> None:
        path = self.private_dir / "research-events.jsonl"
        existing = set()
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    row = json.loads(line)
                    if row.get("event_id"):
                        existing.add(str(row["event_id"]))
                except (json.JSONDecodeError, AttributeError):
                    raise ValueError("private research event log is malformed")
        if event["event_id"] not in existing:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")

    def _session_path(self, session_id: str) -> Path:
        if not _SESSION_ID.fullmatch(str(session_id)):
            raise ValueError("invalid research_session_id")
        return self.sessions_dir / f"{session_id}.json"

    def _save_session(self, session: dict[str, Any]) -> None:
        validate_record("research_session", session)
        _atomic_json(self._session_path(session["research_session_id"]), session)


def _normalize_linked_text(value: Any, allowed: set[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    result = []
    for row in value:
        if not isinstance(row, dict) or not str(row.get("text") or "").strip():
            continue
        ids = _string_list(row.get("evidence_ids"))
        _reject_unknown_evidence(ids, allowed)
        result.append({"text": str(row["text"]).strip(), "evidence_ids": ids})
    return result


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return list(dict.fromkeys(str(item) for item in value if isinstance(item, str) and item.strip()))


def _reject_unknown_evidence(ids: list[str], allowed: set[str]) -> None:
    unknown = sorted(set(ids) - allowed)
    if unknown:
        raise ValueError(f"model output referenced unknown EvidenceRef ID(s): {unknown}")


def _evidence_set_hash(refs: list[dict[str, Any]]) -> str:
    values = [{"evidence_id": row["evidence_id"], "text_sha256": row["text_sha256"]}
              for row in sorted(refs, key=lambda item: (item["evidence_id"], item["text_sha256"]))]
    return _hash(values)


def _timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps require a timezone")
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid private research JSON at {path.name}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"private research JSON must be an object: {path.name}")
    return value


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    _atomic_text(path, json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def _atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent,
                                     prefix=f".{path.name}.", suffix=".tmp", delete=False) as stream:
        temp = Path(stream.name)
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)
