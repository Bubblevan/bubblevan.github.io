from __future__ import annotations

from typing import Any

from ..bridge_xhs import bridge_xhs
from .base import ConnectorCheckpoint, ConnectorContext, ConnectorSpec, FetchResult


class XhsImportConnector:
    spec = ConnectorSpec(
        connector_id="xhs-import", version="1", modes=("manual",),
        capabilities=frozenset({"manual_import", "browser"}),
    )

    def fetch(self, source: dict[str, Any], checkpoint: ConnectorCheckpoint | None, context: ConnectorContext) -> FetchResult:
        if context.import_payload is None:
            raise ValueError("xhs-import requires an explicit sanitized import payload")
        imported_source, observation = bridge_xhs(context.import_payload)
        return FetchResult([observation], checkpoint or ConnectorCheckpoint(), True,
                           {"mode": "manual_import"}, [imported_source])
