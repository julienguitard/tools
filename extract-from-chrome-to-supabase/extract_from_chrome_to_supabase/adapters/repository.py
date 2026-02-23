"""Supabase and mock link repositories."""

from __future__ import annotations

import json

from ..domain import Link


class SupabaseLinkRepository:
    """HTTP adapter for Supabase edge functions."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def fetch_existing(self) -> list[dict]:
        import httpx

        resp = httpx.get(
            f"{self._base_url}/functions/v1/select-table",
            params={"table": "links"},
            headers=self._headers,
        )
        resp.raise_for_status()
        return resp.json()

    def save_links(self, links: list[Link]) -> None:
        import httpx

        payload = [link.to_dict() for link in links]
        resp = httpx.post(
            f"{self._base_url}/functions/v1/insert-links",
            headers=self._headers,
            json=payload,
        )
        resp.raise_for_status()


class MockLinkRepository:
    """Fake implementation for local testing."""

    def fetch_existing(self) -> list[dict]:
        return [
            {"url": "https://example.com/already-saved", "category": "other"},
        ]

    def save_links(self, links: list[Link]) -> None:
        print(f"\n  [MOCK POST] {json.dumps([l.to_dict() for l in links], indent=2)}")
