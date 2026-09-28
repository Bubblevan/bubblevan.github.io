from __future__ import annotations

from pathlib import Path
from typing import Any

from ..aliases import ArtifactAliases
from ..entity_aliases import EntityAliases
from ..store import JsonlStore
from ..topics import topic_aliases
from .builders.observation_artifact import build_observation_artifact_edges
from .builders.topic import build_topic_edges
from .models import predicate_definitions
from .store import GraphStore


def graph_backfill(
    store: JsonlStore,
    runtime_dir: Path | str,
    *,
    now: str,
) -> dict[str, Any]:
    graph = GraphStore(store.directory)
    artifact_aliases = ArtifactAliases(store.directory)
    entity_aliases = EntityAliases(store.directory)
    link_result = build_observation_artifact_edges(
        store, graph, artifact_aliases, entity_aliases, now=now,
    )
    topic_result = build_topic_edges(store, graph, now=now)
    _validate_edge_nodes(store, graph, artifact_aliases, entity_aliases)
    index_result = graph.rebuild_indexes(runtime_dir, entity_id_resolver=entity_aliases)
    return {
        "sources": len(list(store.iter_records("source"))),
        "observations": link_result["observations"],
        "artifacts": len(list(store.iter_records("artifact"))),
        "entities": len(list(store.iter_records("entity"))),
        "edges_total": len(graph.iter_edges()),
        "observation_artifact": link_result,
        "topics": topic_result,
        "indexes": index_result,
        "network_requests": 0,
    }


def validate_graph_nodes(store: JsonlStore, graph: GraphStore) -> None:
    _validate_edge_nodes(store, graph, ArtifactAliases(store.directory), EntityAliases(store.directory))


def _validate_edge_nodes(
    store: JsonlStore,
    graph: GraphStore,
    artifact_aliases: ArtifactAliases,
    entity_aliases: EntityAliases,
) -> None:
    sources = list(store.iter_records("source"))
    observations = list(store.iter_records("observation"))
    artifacts = list(store.iter_records("artifact"))
    entities = list(store.iter_records("entity"))
    known = {
        "source": {item["source_id"] for item in sources},
        "observation": {item["observation_id"] for item in observations},
        "artifact": {item["artifact_id"] for item in artifacts},
        "entity": {entity_aliases.resolve_entity_id(item["entity_id"]) for item in entities},
        "topic": set(topic_aliases().values()),
    }
    node_types: dict[str, set[str]] = {}
    for item in sources:
        node_types[str(item["source_id"])] = {"source"}
    for item in artifacts:
        types = {"artifact"}
        if item.get("artifact_type") == "repository":
            types.add("repository")
        node_types[str(item["artifact_id"])] = types
    for item in entities:
        node_types[entity_aliases.resolve_entity_id(str(item["entity_id"]))] = {
            "entity", str(item.get("entity_type") or "")
        }
    for topic in known["topic"]:
        node_types[topic] = {"topic"}
    prefixes = {"src": "source", "obs": "observation", "art": "artifact", "ent": "entity", "topic": "topic"}
    for edge in graph.iter_edges():
        resolved_endpoints = []
        for endpoint in (str(edge["subject_id"]), str(edge["object_id"])):
            prefix = endpoint.split("-", 1)[0]
            kind = prefixes[prefix]
            resolved = endpoint
            if kind == "entity":
                resolved = entity_aliases.resolve_entity_id(endpoint)
            elif kind == "artifact":
                resolved = artifact_aliases.resolve_artifact_id(endpoint)
            if resolved not in known[kind]:
                raise ValueError(f"graph edge references missing {kind} node")
            resolved_endpoints.append(resolved)
        definition = predicate_definitions()[str(edge["predicate"])]
        subject_types = node_types.get(resolved_endpoints[0], set())
        object_types = node_types.get(resolved_endpoints[1], set())
        if not subject_types.intersection(definition["subjects"]):
            raise ValueError("graph edge subject type violates predicate vocabulary")
        if not object_types.intersection(definition["objects"]):
            raise ValueError("graph edge object type violates predicate vocabulary")
