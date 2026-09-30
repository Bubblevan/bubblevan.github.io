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
from .evidence.base import EvidenceBudget, ResearchPerspectivePlan
from .evidence.local_corpus import LocalCorpusEvidenceBackend
from .ids import evidence_ref
from .quality import (classify_evidence, disagreement_evidence_issues, is_synthetic_artifact,
                      preview_privacy_issues, quality_metrics, safe_public_url, scrub_audit_text)
from .rendering import render_brief_markdown, render_promotion_markdown
from .synthesis import (CodexAuthUnavailable, SynthesisAdapter, prompt_hashes,
                        synthesis_adapter_from_environment)


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
        self.reports_dir = self.private_dir / "reports"
        self.repository_root = Path(repository_root).resolve() if repository_root else self.store_dir.resolve().parents[2]
        self.model_adapter = model_adapter
        self.evidence_backend = evidence_backend
        self.store = JsonlStore(self.store_dir)
        self.artifacts = ArtifactRepository(self.store)
        for path in (self.sessions_dir, self.evidence_dir, self.briefs_dir, self.previews_dir, self.reports_dir):
            path.mkdir(parents=True, exist_ok=True)

    def start(self, question: str = "", *, artifact_ids: list[str] | None = None,
              source_feed_run_id: str | None = None, created_at: str | None = None,
              real_case: bool = False,
              perspective_plan: ResearchPerspectivePlan | dict[str, Any] | None = None) -> dict[str, Any]:
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
            "retrieval_config": {"quality_profile": "real_case" if real_case else "default",
                                 "perspective_plan": ResearchPerspectivePlan.from_value(perspective_plan).to_dict()},
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
                         paper_files: dict[str, str | Path] | None = None,
                         perspective_plan: ResearchPerspectivePlan | dict[str, Any] | None = None) -> dict[str, Any]:
        session = self.get_session(session_id)
        real_case = self._is_real_case(session)
        saved_plan = (session.get("retrieval_config") or {}).get("perspective_plan")
        plan = ResearchPerspectivePlan.from_value(perspective_plan if perspective_plan is not None else saved_plan)
        backend = self.evidence_backend or LocalCorpusEvidenceBackend(self.store_dir, self.runtime_dir,
                                                                      real_case=real_case,
                                                                      perspective_plan=plan)
        if real_case and not isinstance(backend, LocalCorpusEvidenceBackend):
            raise ValueError("real ResearchCase requires LocalCorpusEvidenceBackend")
        if real_case and paper_files:
            raise ValueError("real ResearchCase uses local corpus evidence; PaperQA2 remains unconfigured")
        budget = budget or EvidenceBudget()
        refs = backend.gather(session["question"], list(session["seed_artifact_ids"]), budget)
        paperqa_status = "unconfigured" if real_case else "not_requested"
        if paper_files:
            try:
                from .evidence.paperqa import PaperQA2EvidenceBackend
                paper_backend = PaperQA2EvidenceBackend(self.store_dir, paper_files, self.runtime_dir)
                if not paper_backend.is_configured:
                    paperqa_status = "unconfigured"
                else:
                    used_chars = sum(len(str(row["text"])) for row in refs)
                    paper_budget = EvidenceBudget(
                        max_retrieved_artifacts=budget.max_retrieved_artifacts,
                        max_evidence_artifacts=budget.max_evidence_artifacts,
                        max_evidence_refs=max(0, budget.max_evidence_refs - len(refs)),
                        max_refs_per_artifact=budget.max_refs_per_artifact,
                        max_metadata_refs_per_artifact=budget.max_metadata_refs_per_artifact,
                        max_evidence_chars=max(0, budget.max_evidence_chars - used_chars),
                    )
                    if paper_budget.max_evidence_refs:
                        paper_refs = paper_backend.gather(session["question"], list(session["seed_artifact_ids"]), paper_budget)
                        refs.extend(paper_refs)
                        paperqa_status = "succeeded" if paper_refs else "no_local_full_text_match"
                    else:
                        paperqa_status = "skipped:evidence_budget_exhausted"
            except Exception as exc:
                # The optional backend never blocks local evidence collection, and error text is not persisted.
                from .evidence.paperqa import PaperQAUnconfigured
                if isinstance(exc, PaperQAUnconfigured):
                    paperqa_status = "unconfigured"
                else:
                    paperqa_status = f"unavailable:{type(exc).__name__}"
        artifact_rows = {str(row["artifact_id"]): row for row in self.artifacts.iter_canonical()}
        source_rows = {str(row["source_id"]): row for row in self.store.iter_records("source")}
        integrity_issues = self._evidence_integrity_issues(refs, real_case=real_case,
                                                           artifact_rows=artifact_rows, source_rows=source_rows)
        composition = classify_evidence(refs, artifact_rows, source_rows)
        retrieval = getattr(backend, "last_retrieval", {})
        retrieval["perspective_plan"] = plan.to_dict()
        retrieval["metadata_fallback"] = bool(getattr(backend, "metadata_fallback", False))
        retrieval["curator_evidence_unavailable"] = bool(
            plan.curator and int(composition["curator_artifacts"]) < 1)
        retrieval["discussion_evidence_unavailable"] = bool(
            plan.discussion and int(composition["discussion_artifacts"]) < 1)
        retrieval["metadata_share"] = composition["metadata_share"]
        retrieval["metadata_ref_count"] = composition["metadata_ref_count"]
        retrieval["substantive_ref_count"] = composition["substantive_ref_count"]
        prior_paths = sorted(self.evidence_dir.glob(f"{session_id}-evidence-*.json"))
        if prior_paths:
            def revision_composition(path: Path) -> dict[str, Any] | None:
                prior_record = _read_json(path)
                prior_refs = prior_record.get("evidence_refs") if isinstance(prior_record, dict) else None
                if not isinstance(prior_refs, list):
                    return None
                prior_composition = classify_evidence(prior_refs, artifact_rows, source_rows)
                return {"revision": prior_record.get("revision"),
                        "first_party_refs": prior_composition["evidence_kind_refs"]["first_party"],
                        "metadata_refs": prior_composition["evidence_kind_refs"]["metadata"],
                        "curator_artifacts": prior_composition["curator_artifacts"]}

            retrieval["previous_evidence_composition"] = revision_composition(prior_paths[-1])
            baseline = revision_composition(prior_paths[0])
            if baseline and int(baseline.get("revision") or 0) == 1:
                retrieval["m83_baseline_evidence_composition"] = baseline
        blockers = []
        if integrity_issues:
            blockers.extend(sorted({issue["code"] for issue in integrity_issues}))
        if real_case and int(composition["first_party_artifacts"]) < 2:
            blockers.append("REAL_CASE_BLOCKED_INSUFFICIENT_PRIMARY_EVIDENCE")
        if real_case and float(composition["metadata_share"]) > 0.25:
            blockers.append("REAL_CASE_BLOCKED_METADATA_SHARE")
        if real_case and retrieval.get("dense_status") != "fresh":
            blockers.append("REAL_CASE_BLOCKED_DENSE_NOT_FRESH")
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
                  "retrieval": {**retrieval, "paperqa_status": paperqa_status,
                                "evidence_composition": {key: composition[key] for key in (
                                    "evidence_kind_refs", "first_party_artifacts", "curator_artifacts",
                                    "discussion_artifacts", "metadata_artifacts", "metadata_ref_count",
                                    "substantive_ref_count", "metadata_share")},
                                "integrity_issues": integrity_issues,
                                "real_case_blockers": sorted(set(blockers))}, "created_at": now_utc()}
        _atomic_json(evidence_path, record)
        audit_path = self._write_evidence_audit(session, refs, artifact_rows, source_rows,
                                                composition, integrity_issues, real_case=real_case,
                                                retrieval=retrieval)
        session.update({
            "status": "failed" if blockers else "evidence_ready", "updated_at": now_utc(),
            "corpus_hash": record["corpus_hash"], "evidence_set_hash": evidence_hash,
            "evidence_path": evidence_path.relative_to(self.private_dir).as_posix(),
            "retrieval_config": {"quality_profile": "real_case" if real_case else "default",
                                 "perspective_plan": plan.to_dict(),
                                 "budget": budget.__dict__, "retrieval": record["retrieval"]},
            "reviewed_by": None, "reviewed_at": None, "approved_by": None, "approved_at": None,
        })
        self._save_session(session)
        return {"status": "evidence_blocked" if blockers else "evidence_ready",
                "research_session_id": session_id,
                "evidence_count": len(refs), "evidence_artifacts": len({row["artifact_id"] for row in refs}),
                "evidence_set_hash": evidence_hash, "corpus_hash": record["corpus_hash"],
                "retrieval": record["retrieval"], "integrity_issue_count": len(integrity_issues),
                "blockers": sorted(set(blockers)), "evidence_audit_path": str(audit_path),
                "path": str(evidence_path)}

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
        self._validate_evidence(refs, raise_on_broken=True, real_case=self._is_real_case(row))
        if _evidence_set_hash(refs) != row.get("evidence_set_hash"):
            raise ValueError("research evidence set hash no longer matches the session")
        return refs

    def generate(self, session_id: str, *, model_adapter: SynthesisAdapter | None = None) -> dict[str, Any]:
        session = self.get_session(session_id)
        try:
            evidence = self.load_evidence(session)
        except (OSError, ValueError):
            return {"status": "synthesis_unavailable", "synthesis_status": "evidence_integrity_blocked",
                    "reason": "evidence_integrity_check_failed", "evidence_count": 0,
                    "evidence_set_hash": session.get("evidence_set_hash")}
        if self._is_real_case(session):
            retrieval = (session.get("retrieval_config") or {}).get("retrieval") or {}
            blockers = list(retrieval.get("real_case_blockers") or [])
            composition = classify_evidence(
                evidence,
                {str(row["artifact_id"]): row for row in self.artifacts.iter_canonical()},
                {str(row["source_id"]): row for row in self.store.iter_records("source")},
            )
            plan = ResearchPerspectivePlan.from_value(
                retrieval.get("perspective_plan") or (session.get("retrieval_config") or {}).get("perspective_plan"))
            if int(composition["first_party_artifacts"]) < 2:
                blockers.append("REAL_CASE_BLOCKED_INSUFFICIENT_PRIMARY_EVIDENCE")
            if float(composition["metadata_share"]) > 0.25:
                blockers.append("REAL_CASE_BLOCKED_METADATA_SHARE")
            if (plan.curator and int(composition["curator_artifacts"]) < 1
                    and not retrieval.get("curator_evidence_unavailable")):
                blockers.append("REAL_CASE_BLOCKED_UNRECORDED_CURATOR_GAP")
            if blockers:
                return {"status": "synthesis_unavailable", "synthesis_status": "evidence_blocked",
                        "reason": "real_case_evidence_gate_failed", "blockers": blockers,
                        "evidence_count": len(evidence), "evidence_set_hash": session.get("evidence_set_hash")}
        adapter = model_adapter if model_adapter is not None else self.model_adapter
        try:
            if adapter is None:
                adapter = synthesis_adapter_from_environment()
        except (TypeError, ValueError):
            return {"status": "synthesis_unavailable", "synthesis_status": "failed",
                    "reason": "invalid_synthesis_backend_configuration",
                    "evidence_count": len(evidence), "evidence_set_hash": session.get("evidence_set_hash")}
        if adapter is None:
            return {"status": "synthesis_unavailable", "synthesis_status": "unconfigured",
                    "reason": "RI_RESEARCH_BACKEND/model configuration is incomplete in the process environment",
                    "evidence_count": len(evidence), "evidence_set_hash": session.get("evidence_set_hash"),
                    "model_usage": {"provider": None, "backend": None, "auth_mode": None,
                                    "billing_mode": None, "model": None, "input_tokens": 0,
                                    "output_tokens": 0, "cost": 0.0}}
        model_evidence = self._model_evidence(evidence)
        synthesis_question = self._synthesis_question(session, evidence)
        prompts = prompt_hashes(synthesis_question, model_evidence)
        try:
            result = adapter.synthesize(synthesis_question, model_evidence)
        except CodexAuthUnavailable as exc:
            model_usage = {"provider": "codex", "backend": "codex_exec",
                           "auth_mode": "auth_unavailable", "billing_mode": None,
                           "model": getattr(adapter, "model", None), "codex_cli_version": None,
                           "timeout_seconds": getattr(adapter, "timeout_seconds", None),
                           "input_tokens": None, "output_tokens": None, "cost": None}
            model_usage.update(exc.model_provenance)
            quality_path = (self._write_blocked_quality_report(
                session, evidence, synthesis_status="auth_unavailable", model_usage=model_usage)
                if self._is_real_case(session) else None)
            return {"status": "synthesis_unavailable", "synthesis_status": "auth_unavailable",
                    "reason": "codex_login_status_reports_not_logged_in", "evidence_count": len(evidence),
                    "evidence_set_hash": session.get("evidence_set_hash"),
                    "quality_report_path": str(quality_path) if quality_path else None,
                    "model_usage": model_usage}
        except Exception as exc:
            return {"status": "synthesis_unavailable", "synthesis_status": "failed", "reason": type(exc).__name__,
                    "evidence_count": len(evidence), "evidence_set_hash": session.get("evidence_set_hash")}
        if not isinstance(result, dict) or not isinstance(result.get("payload"), dict):
            raise ValueError("synthesis adapter returned a malformed result")
        revision = int(session.get("brief_revision") or 0) + 1
        brief = self._normalize_brief(session, evidence, result["payload"], revision,
                                      result.get("model_provenance") or {}, prompts)
        path = self.briefs_dir / f"{session_id}-r{revision:04d}.json"
        _atomic_json(path, brief)
        markdown = render_brief_markdown(brief, self._render_evidence(evidence))
        _atomic_text(path.with_suffix(".md"), markdown)
        session.update({"status": "synthesized", "updated_at": now_utc(), "brief_revision": revision,
                        "model_config": brief["model_provenance"], "prompt_hashes": prompts})
        self._save_session(session)
        quality_path = self._write_quality_report(session, evidence, brief) if self._is_real_case(session) else None
        return {"status": "synthesized", "synthesis_status": "succeeded",
                "research_session_id": session_id, "revision": revision,
                "brief_path": str(path), "markdown_path": str(path.with_suffix('.md')),
                "quality_report_path": str(quality_path) if quality_path else None,
                "evidence_set_hash": brief["evidence_set_hash"], "metrics": brief["metrics"],
                "model_usage": {key: brief["model_provenance"].get(key)
                                for key in ("provider", "backend", "auth_mode", "billing_mode", "model",
                                            "input_tokens", "output_tokens", "cost")}}

    def _model_evidence(self, refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        artifact_rows = {str(row["artifact_id"]): row for row in self.artifacts.iter_canonical()}
        source_rows = {str(row["source_id"]): row for row in self.store.iter_records("source")}
        kinds = classify_evidence(refs, artifact_rows, source_rows)["evidence_kinds"]
        fields = ("schema", "evidence_id", "artifact_id", "observation_id", "source_id", "canonical_url",
                  "title", "published_at", "locator", "text", "text_sha256", "evidence_type", "retrieved_at")
        result = []
        for ref in refs:
            artifact = artifact_rows.get(str(ref.get("artifact_id") or ""), {})
            source = source_rows.get(str(ref.get("source_id") or ""), {})
            result.append({**{key: ref.get(key) for key in fields},
                           "evidence_kind": kinds.get(str(ref.get("evidence_id") or "")),
                           "artifact_type": artifact.get("artifact_type"),
                           "source_name": source.get("name")})
        return result

    def _synthesis_question(self, session: dict[str, Any], refs: list[dict[str, Any]]) -> str:
        retrieval = (session.get("retrieval_config") or {}).get("retrieval") or {}
        plan_value = retrieval.get("perspective_plan") or (session.get("retrieval_config") or {}).get("perspective_plan")
        plan = ResearchPerspectivePlan.from_value(plan_value)
        composition = classify_evidence(
            refs,
            {str(row["artifact_id"]): row for row in self.artifacts.iter_canonical()},
            {str(row["source_id"]): row for row in self.store.iter_records("source")},
        )
        question = str(session["question"])
        if plan.curator and int(composition["curator_artifacts"]) < 1:
            question += ("\n\nEvidence constraint: the requested curator/community perspective has no "
                        "sufficient relevant curator evidence in the current corpus. State this explicitly; "
                        "do not infer curator consensus or substitute unrelated social posts.")
        if plan.discussion and int(composition["discussion_artifacts"]) < 1:
            question += ("\n\nEvidence constraint: no relevant discussion-source text was found in the current corpus. "
                        "State this limitation if discussing community reaction.")
        return question

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
        if self._is_real_case(session) and int(metrics.get("secondary_only_fact_count", -1)) != 0:
            raise ValueError("secondary-only factual claims block approval")
        if self._is_real_case(session) and int(metrics.get("metadata_only_fact_count", -1)) != 0:
            raise ValueError("metadata-only factual claims block approval")
        if self._is_real_case(session) and float(metrics.get("metadata_share", 1.0)) > 0.25:
            raise ValueError("metadata evidence share above 25% blocks approval")
        if self._is_real_case(session) and int(metrics.get("first_party_artifacts", -1)) < 2:
            raise ValueError("real-case approval requires at least two first-party evidence Artifacts")
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
        markdown = render_promotion_markdown(session, brief, self._render_evidence(evidence), target=canonical_target,
                                             title=title, topics=topics or [])
        gate = self._promotion_gate(session, brief, evidence, markdown=markdown)
        stored_markdown = markdown if not gate["preview_privacy_issues"] else None
        preview_id = stable_id("pv", "research-promotion-preview", f"{session_id}|{brief['revision']}|{canonical_target}|{brief['output_hash']}")
        preview_path = self.previews_dir / f"{preview_id}.json"
        markdown_path = preview_path.with_suffix(".md")
        record = {"schema": "bubblevan/research-promotion-preview/v1", "preview_id": preview_id,
                  "research_session_id": session_id, "revision": brief["revision"], "target": canonical_target,
                  "title": scrub_audit_text(title or session["question"], limit=300),
                  "markdown": stored_markdown, "gate": gate,
                  "created_at": now_utc()}
        _atomic_json(preview_path, record)
        if stored_markdown is not None:
            _atomic_text(markdown_path, stored_markdown)
        else:
            # A stable preview id can be regenerated after its earlier content was
            # saved. Remove any old body when the current privacy scan blocks it.
            markdown_path.unlink(missing_ok=True)
        return {"status": "preview_ready" if gate["eligible"] else "preview_blocked",
                "preview_id": preview_id, "preview_path": str(preview_path),
                "markdown_path": str(markdown_path) if stored_markdown is not None else None,
                "target": canonical_target,
                "markdown": stored_markdown,
                "front_matter": markdown.split("---\n", 2)[1] if markdown.startswith("---\n") and stored_markdown is not None else "",
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
        preview = self._find_preview(session_id, int(brief["revision"]), target)
        gate = self._promotion_gate(session, brief, evidence,
                                    markdown=str(preview.get("markdown") or "") if preview else "")
        if not gate["eligible"]:
            raise ValueError("promotion blocked by structural quality gates")
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
        missing_evidence = sum(1 for claim in claims
                               if claim["claim_type"] == "fact" and not claim["evidence_ids"])
        if summary and not summary_ids:
            missing_evidence += 1
        evidence_by_id = {str(row["evidence_id"]): row for row in evidence}
        missing_evidence += disagreement_evidence_issues(disagreements, evidence_by_id)
        broken = self._validate_evidence(evidence)
        all_ids = set(summary_ids)
        for claim in claims:
            all_ids.update(claim["evidence_ids"])
        for row in disagreements + implications:
            all_ids.update(row["evidence_ids"])
        distinct_artifacts = {evidence_by_id[item]["artifact_id"] for item in all_ids if item in evidence_by_id}
        distinct_sources = {evidence_by_id[item]["source_id"] for item in all_ids
                            if item in evidence_by_id and evidence_by_id[item].get("source_id")}
        citation_count = len(summary_ids) + sum(len(row["evidence_ids"]) for row in claims)
        citation_count += sum(len(row["evidence_ids"]) for row in disagreements + implications)
        metrics = {"claim_count": len(claims),
                   "fact_claim_count": sum(row["claim_type"] == "fact" for row in claims),
                   "supported_fact_count": sum(row["claim_type"] == "fact" and row["confidence"] == "supported" for row in claims),
                   "unsupported_fact_count": unsupported,
                   "citation_count": citation_count,
                   "broken_citation_count": broken,
                   "missing_evidence_count": missing_evidence,
                   "metadata_only_fact_count": 0,
                   "distinct_artifact_count": len(distinct_artifacts),
                   "distinct_source_count": len(distinct_sources),
                   "evidence_set_hash": str(session.get("evidence_set_hash") or "")}
        artifact_rows = {str(row["artifact_id"]): row for row in self.artifacts.iter_canonical()}
        source_rows = {str(row["source_id"]): row for row in self.store.iter_records("source")}
        metrics.update(quality_metrics(evidence, {"claims": claims, "disagreements": disagreements,
                                                  "metrics": metrics,
                                                  "model_provenance": provenance},
                                       artifact_rows, source_rows, broken_citation_count=broken,
                                        missing_evidence_count=missing_evidence))
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
                                 "backend": provenance.get("backend"),
                                 "auth_mode": provenance.get("auth_mode"),
                                 "billing_mode": provenance.get("billing_mode"),
                                 "codex_cli_version": provenance.get("codex_cli_version"),
                                 "timeout_seconds": provenance.get("timeout_seconds"),
                                 "model_revision": provenance.get("model_revision"),
                                 "temperature": provenance.get("temperature", 0),
                                 "request_id": provenance.get("request_id"),
                                 "started_at": provenance.get("started_at"),
                                 "completed_at": provenance.get("completed_at"),
                                 "input_tokens": provenance.get("input_tokens"),
                                 "output_tokens": provenance.get("output_tokens"),
                                 "cost": provenance.get("cost")},
            "prompt_hashes": prompts,
            "metrics": metrics,
        }
        semantic = {key: value for key, value in brief.items() if key not in {"output_hash", "status"}}
        brief["output_hash"] = _hash(semantic)
        validate_record("research_brief", brief)
        return brief

    def _validate_evidence(self, refs: list[dict[str, Any]], *, raise_on_broken: bool = False,
                           real_case: bool = False) -> int:
        issues = self._evidence_integrity_issues(refs, real_case=real_case)
        if issues and raise_on_broken:
            raise ValueError(f"research evidence contains {len(issues)} invalid reference(s)")
        return len(issues)

    def _evidence_integrity_issues(self, refs: list[dict[str, Any]], *, real_case: bool = False,
                                   artifact_rows: dict[str, dict[str, Any]] | None = None,
                                   source_rows: dict[str, dict[str, Any]] | None = None) -> list[dict[str, str]]:
        artifact_rows = artifact_rows or {str(row["artifact_id"]): row for row in self.artifacts.iter_canonical()}
        source_rows = source_rows or {str(row["source_id"]): row for row in self.store.iter_records("source")}
        observations = {str(row["observation_id"]): row for row in self.store.iter_records("observation")}
        graph_edge_ids = {str(row.get("locator", {}).get("value", "")).removeprefix("graph-edge:")
                          for row in refs if str(row.get("locator", {}).get("value", "")).startswith("graph-edge:")}
        graph_edges = ({str(row["edge_id"]): row for row in GraphStore(self.store_dir).iter_edges()
                        if str(row.get("edge_id")) in graph_edge_ids} if graph_edge_ids else {})
        issues: list[dict[str, str]] = []
        for row in refs:
            evidence_id = str(row.get("evidence_id") or "unknown") if isinstance(row, dict) else "unknown"
            try:
                if not isinstance(row, dict):
                    raise ValueError("malformed_ref")
                validate_record("evidence_ref", row)
                artifact_id = str(row["artifact_id"])
                canonical_id = self.artifacts.resolve_id(artifact_id)
                if canonical_id != artifact_id or canonical_id not in artifact_rows:
                    raise ValueError("noncanonical_artifact")
                artifact = artifact_rows[canonical_id]
                if hashlib.sha256(str(row["text"]).encode("utf-8")).hexdigest() != row["text_sha256"]:
                    raise ValueError("text_hash_mismatch")
                source_id = row.get("source_id")
                if source_id and str(source_id) not in source_rows:
                    raise ValueError("unknown_source")
                locator = row.get("locator") or {}
                locator_type = str(locator.get("type") or "")
                locator_value = str(locator.get("value") or "")
                observation_id = row.get("observation_id")
                if observation_id:
                    observation = observations.get(str(observation_id))
                    if observation is None:
                        raise ValueError("missing_observation")
                    observation_source_id = str(observation.get("source_id") or "")
                    if observation_source_id not in source_rows:
                        raise ValueError("unknown_source")
                    if str(source_id or "") != observation_source_id:
                        raise ValueError("observation_source_mismatch")
                if row.get("evidence_type") == "observation_text" and not observation_id:
                    raise ValueError("observation_required")
                if locator_type == "metadata":
                    if locator_value not in {"title", "summary"}:
                        raise ValueError("unresolved_metadata_locator")
                    original = str(artifact.get(locator_value) or "")
                    if locator_value == "summary":
                        original = original[:4000]
                    if original != str(row["text"]):
                        raise ValueError("metadata_text_mismatch")
                elif locator_type == "observation":
                    observation = observations.get(str(observation_id or ""))
                    if observation is None or str(observation_id) != locator_value:
                        raise ValueError("unresolved_observation_locator")
                    current_text = "\n\n".join(part.strip() for part in
                                                  (str(observation.get("title") or ""), str(observation.get("text") or ""))
                                                  if part.strip())[:20_000]
                    if current_text != str(row["text"]):
                        raise ValueError("observation_text_mismatch")
                elif locator_type == "section" and locator_value.startswith("graph-edge:"):
                    edge_id = locator_value.removeprefix("graph-edge:")
                    edge = graph_edges.get(edge_id)
                    if edge is None:
                        raise ValueError("unresolved_graph_locator")
                    relation_prefix = (f"Exact graph relation: {edge['subject_id']} --{edge['predicate']}--> "
                                       f"{edge['object_id']}; edge={edge['edge_id']}; evidence_type=")
                    if not any(str(row["text"]).startswith(relation_prefix)
                               and str(item.get("evidence_type") or "") in {"exact_provider_metadata", "explicit_source_link"}
                               for item in edge.get("evidence", [])):
                        raise ValueError("graph_evidence_mismatch")
                elif real_case:
                    raise ValueError("unresolved_locator")
                if real_case and is_synthetic_artifact(artifact, source_rows.get(str(source_id or ""))):
                    raise ValueError("synthetic_artifact")
            except (ValueError, KeyError, TypeError) as exc:
                known_codes = {"malformed_ref", "noncanonical_artifact", "text_hash_mismatch", "unknown_source",
                               "missing_observation", "observation_source_mismatch", "observation_required",
                               "unresolved_metadata_locator", "metadata_text_mismatch",
                               "unresolved_observation_locator", "observation_text_mismatch",
                               "unresolved_graph_locator", "graph_evidence_mismatch", "unresolved_locator",
                               "synthetic_artifact"}
                issue_code = str(exc) if str(exc) in known_codes else "invalid_evidence_reference"
                issues.append({"evidence_id": evidence_id, "code": issue_code})
        return issues

    def _is_real_case(self, session: dict[str, Any]) -> bool:
        return str((session.get("retrieval_config") or {}).get("quality_profile") or "") == "real_case"

    def _write_evidence_audit(self, session: dict[str, Any], refs: list[dict[str, Any]],
                              artifact_rows: dict[str, dict[str, Any]],
                              source_rows: dict[str, dict[str, Any]], composition: dict[str, Any],
                              issues: list[dict[str, str]], *, real_case: bool,
                              retrieval: dict[str, Any] | None = None) -> Path:
        report_path = self.reports_dir / f"{session['research_session_id']}-evidence-audit.md"
        refs_by_artifact: dict[str, list[dict[str, Any]]] = {}
        for ref in refs:
            refs_by_artifact.setdefault(str(ref.get("artifact_id") or ""), []).append(ref)
        lines = ["# Evidence audit", "", f"Case ID: `{session['research_session_id']}`", "",
                 f"Question: {scrub_audit_text(session['question'], limit=500)}", "",
                 f"Evidence references: {len(refs)}", "",
                 "This private audit lists only bounded excerpts. Query strings, signed links, credentials, and local paths are omitted.", ""]
        if issues:
            lines.extend(["## Integrity", "", f"Broken references: {len(issues)}"])
            lines.extend(f"- `{row['evidence_id']}` — `{row['code']}`" for row in issues)
            lines.append("")
        elif real_case:
            lines.extend(["## Integrity", "", "All EvidenceRefs resolved to canonical Artifacts, valid Sources, and matching text hashes.", ""])
        prior = (retrieval or {}).get("previous_evidence_composition") or {}
        if prior:
            lines.extend(["## Prior revision comparison", "",
                          f"- Prior revision: {prior.get('revision')}",
                          f"- Prior first-party EvidenceRefs: {prior.get('first_party_refs', 0)}",
                          f"- Prior metadata EvidenceRefs: {prior.get('metadata_refs', 0)}",
                          f"- Prior curator Artifacts: {prior.get('curator_artifacts', 0)}", ""])
        baseline = (retrieval or {}).get("m83_baseline_evidence_composition") or {}
        if baseline and baseline.get("revision") != prior.get("revision"):
            lines.extend(["## M8.3 original baseline", "",
                          f"- Revision: {baseline.get('revision')}",
                          f"- First-party EvidenceRefs: {baseline.get('first_party_refs', 0)}",
                          f"- Metadata EvidenceRefs: {baseline.get('metadata_refs', 0)}",
                          f"- Curator Artifacts: {baseline.get('curator_artifacts', 0)}", ""])
        lines.extend(["## Evidence by Artifact", ""])
        for artifact_id in sorted(refs_by_artifact):
            artifact = artifact_rows.get(artifact_id, {})
            artifact_refs = refs_by_artifact[artifact_id]
            source_names = sorted({str(source_rows.get(str(item.get("source_id") or ""), {}).get("name") or "Unknown source")
                                   for item in artifact_refs})
            kind = composition.get("artifact_kinds", {}).get(artifact_id, "metadata")
            title = scrub_audit_text(str(artifact.get("title") or "Untitled Artifact"), limit=300)
            artifact_type = scrub_audit_text(str(artifact.get("artifact_type") or "unknown"), limit=80)
            lines.extend([f"### {title}", "", f"- Artifact type: `{artifact_type}`",
                          f"- Artifact ID: `{artifact_id}`", f"- Source: {', '.join(scrub_audit_text(item, limit=160) for item in source_names)}",
                          f"- Evidence kind: `{kind}`"])
            for ref in sorted(artifact_refs, key=lambda row: str(row.get("evidence_id") or "")):
                locator = ref.get("locator") or {}
                locator_value = str(locator.get("value") or "")
                if str(locator.get("type") or "") in {"page", "paper_page"}:
                    locator_value = safe_public_url(locator_value) or "[non-public locator omitted]"
                locator_display = scrub_audit_text(f"{locator.get('type')}: {locator_value}", limit=240)
                excerpt = scrub_audit_text(str(ref.get("text") or ""), limit=700).replace("\n", " ")
                lines.extend(["", f"- Locator: `{locator_display}`", f"- Bounded excerpt: {excerpt}"])
            lines.append("")
        lines.extend(["## Evidence composition", "",
                      f"- First-party Artifacts: {composition.get('first_party_artifacts', 0)}",
                      f"- Curator Artifacts: {composition.get('curator_artifacts', 0)}",
                      f"- Discussion Artifacts: {composition.get('discussion_artifacts', 0)}",
                      f"- Metadata-only Artifacts: {composition.get('metadata_artifacts', 0)}",
                      f"- Substantive EvidenceRefs: {composition.get('substantive_ref_count', 0)}",
                      f"- Metadata EvidenceRefs: {composition.get('metadata_ref_count', 0)}",
                      f"- Metadata share: {composition.get('metadata_share', 0.0):.3f}",
                      f"- Metadata fallback used: {bool((retrieval or {}).get('metadata_fallback'))}",
                      f"- Curator evidence unavailable: {bool((retrieval or {}).get('curator_evidence_unavailable'))}", ""])
        _atomic_text(report_path, "\n".join(lines).rstrip() + "\n")
        return report_path

    def _write_quality_report(self, session: dict[str, Any], evidence: list[dict[str, Any]],
                              brief: dict[str, Any]) -> Path:
        artifact_rows = {str(row["artifact_id"]): row for row in self.artifacts.iter_canonical()}
        source_rows = {str(row["source_id"]): row for row in self.store.iter_records("source")}
        metrics = quality_metrics(evidence, brief, artifact_rows, source_rows,
                                  broken_citation_count=self._validate_evidence(evidence, real_case=True),
                                  missing_evidence_count=int(brief.get("metrics", {}).get("missing_evidence_count", 0)))
        report = {"schema": "bubblevan/research-case-quality/v1",
                  "research_case_id": session["research_session_id"],
                  "question": session["question"],
                  "corpus_hash": session.get("corpus_hash"),
                  "evidence_set_hash": session.get("evidence_set_hash"),
                  "paperqa2": "unconfigured", **metrics}
        gates = {
            "unsupported_fact_count": int(metrics.get("unsupported_fact_count", -1)) == 0,
            "secondary_only_fact_count": int(metrics.get("secondary_only_fact_count", -1)) == 0,
            "metadata_only_fact_count": int(metrics.get("metadata_only_fact_count", -1)) == 0,
            "broken_citation_count": int(metrics.get("broken_citation_count", -1)) == 0,
            "missing_evidence_count": int(metrics.get("missing_evidence_count", -1)) == 0,
            "metadata_share": float(metrics.get("metadata_share", 1.0)) <= 0.25,
            "first_party_artifacts": int(metrics.get("first_party_artifacts", 0)) >= 2,
        }
        report["quality_status"] = "pass" if all(gates.values()) else "blocked"
        report["quality_gates"] = gates
        path = self.reports_dir / f"{session['research_session_id']}-quality.json"
        _atomic_json(path, report)
        return path

    def _write_blocked_quality_report(self, session: dict[str, Any], evidence: list[dict[str, Any]],
                                      *, synthesis_status: str,
                                      model_usage: dict[str, Any]) -> Path:
        artifact_rows = {str(row["artifact_id"]): row for row in self.artifacts.iter_canonical()}
        source_rows = {str(row["source_id"]): row for row in self.store.iter_records("source")}
        composition = classify_evidence(evidence, artifact_rows, source_rows)
        report = {
            "schema": "bubblevan/research-case-quality/v1",
            "research_case_id": session["research_session_id"],
            "question": session["question"],
            "corpus_hash": session.get("corpus_hash"),
            "evidence_set_hash": session.get("evidence_set_hash"),
            "synthesis_status": synthesis_status,
            "quality_status": "claim_metrics_not_evaluated",
            "preview_status": "not_created",
            "evidence_count": len(evidence),
            "artifact_count": len({str(row.get("artifact_id") or "") for row in evidence}),
            "source_count": len({str(row.get("source_id") or "") for row in evidence
                                  if row.get("source_id")}),
            "first_party_artifacts": composition["first_party_artifacts"],
            "curator_artifacts": composition["curator_artifacts"],
            "discussion_artifacts": composition["discussion_artifacts"],
            "metadata_artifacts": composition["metadata_artifacts"],
            "metadata_ref_count": composition["metadata_ref_count"],
            "substantive_ref_count": composition["substantive_ref_count"],
            "metadata_share": composition["metadata_share"],
            "claim_count": None,
            "supported_fact_count": None,
            "unsupported_fact_count": None,
            "secondary_only_fact_count": None,
            "metadata_only_fact_count": None,
            "disagreement_count": None,
            "broken_citation_count": None,
            "missing_evidence_count": None,
            "evidence_integrity_issue_count": 0,
            "input_tokens": model_usage.get("input_tokens"),
            "output_tokens": model_usage.get("output_tokens"),
            "cost": model_usage.get("cost"),
            "model_provenance": model_usage,
            "curator_evidence_unavailable": bool(
                ((session.get("retrieval_config") or {}).get("retrieval") or {}).get("curator_evidence_unavailable")),
            "metadata_fallback": bool(
                ((session.get("retrieval_config") or {}).get("retrieval") or {}).get("metadata_fallback")),
            "paperqa2": "unconfigured",
        }
        path = self.reports_dir / f"{session['research_session_id']}-quality.json"
        _atomic_json(path, report)
        return path

    def review_surface(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        brief = self.get_brief(session_id)
        refs = self.load_evidence(session)
        source_rows = {str(row["source_id"]): row for row in self.store.iter_records("source")}
        artifact_rows = {str(row["artifact_id"]): row for row in self.artifacts.iter_canonical()}
        evidence_kinds = classify_evidence(refs, artifact_rows, source_rows)["evidence_kinds"]
        evidence_by_id = {str(row["evidence_id"]): row for row in refs}

        def linked(evidence_ids: list[str]) -> list[dict[str, Any]]:
            result = []
            for evidence_id in evidence_ids:
                ref = evidence_by_id.get(str(evidence_id))
                if not ref:
                    continue
                source = source_rows.get(str(ref.get("source_id") or ""), {})
                result.append({"evidence_id": evidence_id, "source_title": ref.get("title"),
                               "source_name": source.get("name"), "evidence_kind": evidence_kinds.get(evidence_id),
                               "public_url": safe_public_url(ref.get("canonical_url"))})
            return result

        return {"executive_summary": {"text": brief.get("executive_summary"),
                                      "evidence": linked(brief.get("summary_evidence_ids", []))},
                "claims": [{**row, "supporting_evidence": linked(row.get("evidence_ids", []))}
                           for row in brief.get("claims", [])],
                "evidence": [{**row, "evidence_kind": evidence_kinds.get(str(row.get("evidence_id"))),
                              "source_name": source_rows.get(str(row.get("source_id") or ""), {}).get("name")}
                             for row in refs],
                "disagreements": [{**row, "supporting_evidence": linked(row.get("evidence_ids", []))}
                                   for row in brief.get("disagreements", [])],
                "limitations": brief.get("limitations", []),
                "interpretations": [{**row, "supporting_evidence": linked(row.get("evidence_ids", []))}
                                    for row in brief.get("claims", [])
                                    if row.get("claim_type") in {"inference", "interpretation"}],
                "practical_implications": [{**row, "supporting_evidence": linked(row.get("evidence_ids", []))}
                                           for row in brief.get("practical_implications", [])],
                "open_questions": brief.get("open_questions", [])}

    def _render_evidence(self, refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        artifact_rows = {str(row["artifact_id"]): row for row in self.artifacts.iter_canonical()}
        source_rows = {str(row["source_id"]): row for row in self.store.iter_records("source")}
        evidence_kinds = classify_evidence(refs, artifact_rows, source_rows)["evidence_kinds"]
        return [{**row, "evidence_kind": evidence_kinds.get(str(row.get("evidence_id"))),
                 "source_name": source_rows.get(str(row.get("source_id") or ""), {}).get("name")}
                for row in refs]

    def _promotion_gate(self, session: dict[str, Any], brief: dict[str, Any], evidence: list[dict[str, Any]],
                        *, markdown: str) -> dict[str, Any]:
        real_case = self._is_real_case(session)
        broken = self._validate_evidence(evidence, real_case=real_case)
        metrics = brief.get("metrics", {})
        unsupported = int(metrics.get("unsupported_fact_count", -1))
        missing = int(metrics.get("missing_evidence_count", -1))
        recorded_broken = int(metrics.get("broken_citation_count", -1))
        broken = max(broken, recorded_broken)
        secondary_only = int(metrics.get("secondary_only_fact_count", 0)) if real_case else 0
        metadata_only = int(metrics.get("metadata_only_fact_count", 0)) if real_case else 0
        metadata_share = float(metrics.get("metadata_share", 1.0)) if real_case else 0.0
        first_party = int(metrics.get("first_party_artifacts", 0)) if real_case else 0
        privacy_issues = preview_privacy_issues(markdown)
        missing_public_citation = self._missing_public_citations(brief, evidence) if real_case else 0
        eligible = (unsupported == 0 and missing == 0 and broken == 0 and not privacy_issues
                    and (not real_case or (secondary_only == 0 and metadata_only == 0
                                           and metadata_share <= 0.25 and first_party >= 2
                                           and missing_public_citation == 0)))
        return {"eligible": eligible, "unsupported_fact_count": unsupported,
                "missing_evidence_count": missing, "broken_citation_count": broken,
                "secondary_only_fact_count": secondary_only,
                "metadata_only_fact_count": metadata_only,
                "metadata_share": metadata_share,
                "first_party_artifacts": first_party,
                "missing_public_citation_count": missing_public_citation,
                "preview_privacy_issues": privacy_issues,
                "evidence_set_hash": brief.get("evidence_set_hash")}

    def _missing_public_citations(self, brief: dict[str, Any], evidence: list[dict[str, Any]]) -> int:
        evidence_by_id = {str(row.get("evidence_id") or ""): row for row in evidence}
        missing = 0
        summary_ids = [str(item) for item in brief.get("summary_evidence_ids", [])]
        if str(brief.get("executive_summary") or "").strip() and not any(
                safe_public_url(evidence_by_id.get(item, {}).get("canonical_url")) for item in summary_ids):
            missing += 1
        for claim in brief.get("claims", []):
            if claim.get("claim_type") != "fact":
                continue
            if not any(safe_public_url(evidence_by_id.get(str(item), {}).get("canonical_url"))
                       for item in claim.get("evidence_ids", [])):
                missing += 1
        for item in brief.get("disagreements", []):
            if item.get("evidence_ids") and not any(
                    safe_public_url(evidence_by_id.get(str(ref_id), {}).get("canonical_url"))
                    for ref_id in item["evidence_ids"]):
                missing += 1
        return missing

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
