from __future__ import annotations

from typing import Any

from ..bridge_capture import bridge_capture
from .base import ConnectorCheckpoint, ConnectorContext, ConnectorSpec, FetchResult


class CaptureImportConnector:
    spec = ConnectorSpec(
        connector_id="pkb-import", version="1", modes=("manual",),
        capabilities=frozenset({"manual_import"}),
    )

    def fetch(self, source: dict[str, Any], checkpoint: ConnectorCheckpoint | None, context: ConnectorContext) -> FetchResult:
        if context.import_payload is None:
            raise ValueError("pkb-import requires an explicit PKB capture payload")
        imported_source, observation = bridge_capture(context.import_payload)
        return FetchResult([observation], checkpoint or ConnectorCheckpoint(), True,
                           {"mode": "manual_import"}, [imported_source])
