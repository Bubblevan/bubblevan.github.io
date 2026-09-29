from __future__ import annotations

from typing import Iterable

from .base import Connector, ConnectorSpec


class ConnectorRegistry:
    def __init__(self, connectors: Iterable[Connector] = ()):
        self._connectors: dict[str, Connector] = {}
        for connector in connectors:
            self.register(connector)

    def register(self, connector: Connector) -> None:
        key = connector.spec.connector_id
        if not key or key in self._connectors:
            raise ValueError(f"duplicate or empty connector id: {key!r}")
        self._connectors[key] = connector

    def get(self, connector_id: str) -> Connector:
        try:
            return self._connectors[connector_id]
        except KeyError as exc:
            raise ValueError(f"unknown connector: {connector_id}") from exc

    def list(self) -> list[ConnectorSpec]:
        return [self._connectors[key].spec for key in sorted(self._connectors)]


def connector_registry() -> ConnectorRegistry:
    from .github_releases import GitHubReleasesConnector
    from .huggingface_daily import HuggingFaceDailyPapersConnector
    from .import_capture import CaptureImportConnector
    from .import_xhs import XhsImportConnector
    from .openalex_works import OpenAlexWorksConnector
    from .openreview_submissions import OpenReviewSubmissionsConnector
    from .rss_atom import RssAtomConnector

    return ConnectorRegistry((RssAtomConnector(), GitHubReleasesConnector(), XhsImportConnector(),
                              CaptureImportConnector(), OpenReviewSubmissionsConnector(),
                              HuggingFaceDailyPapersConnector(), OpenAlexWorksConnector()))
