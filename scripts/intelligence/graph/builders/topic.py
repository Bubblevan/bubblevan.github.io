from __future__ import annotations

from ..models import make_edge
from ..store import GraphSnapshot, GraphStore
from ...store import JsonlStore


def build_topic_edges(store: JsonlStore, graph: GraphStore, *, now: str,
                      snapshot: GraphSnapshot | None = None) -> dict[str, int]:
    """Materialize curated topic assignments as explicit catalog metadata edges."""
    edges_added = 0
    prior = set(snapshot.by_id) if snapshot is not None else {item["edge_id"] for item in graph.iter_edges()}
    edges = []
    for kind in ("source", "artifact", "entity"):
        for record in store.iter_records(kind):
            record_id = str(record[f"{kind}_id"])
            for topic_id in sorted(set(str(value) for value in record.get("topics", []))):
                edge = make_edge(
                    record_id, "about_topic", topic_id,
                    {
                        "evidence_type": "exact_provider_metadata",
                        "provider": "curated-topic-catalog",
                        "provider_record_id": f"{kind}:{record_id}:{topic_id}",
                        "confidence": 1.0,
                        "observed_at": now,
                    },
                    observed_at=now,
                )
                edges.append(edge)
    snapshot.add_edges(edges) if snapshot is not None else graph.add_edges(edges)
    edges_added = len({edge["edge_id"] for edge in edges} - prior)
    return {"edges_added": edges_added}
