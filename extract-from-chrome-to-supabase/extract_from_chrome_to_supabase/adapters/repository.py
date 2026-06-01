"""Supabase and mock link repositories."""

from __future__ import annotations

import json

from ..domain import Link, StoredLink, Url


class SupabaseLinkRepository:
    """HTTP adapter for Supabase edge functions.

    The gateway authenticates on the ``apikey`` header. Write endpoints such
    as ``insert-links`` additionally require an authenticated *user* token
    (RLS / ``auth.uid()``): the ``apikey`` alone lets you read but returns
    401 on inserts. When ``email``/``password`` are supplied, the adapter
    performs a password-grant token exchange (the Postman flow) and sends the
    resulting ``access_token`` as a Bearer token.
    """

    def __init__(
        self,
        base_url: Url,
        api_key: str,
        *,
        email: str = "",
        password: str = "",
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._email = email
        self._password = password
        self._token: str | None = None

    # -- auth ----------------------------------------------------------------

    def _access_token(self) -> str | None:
        """Return a Bearer token, exchanging credentials once and caching it.

        Falls back to the API key itself when it already is a legacy 3-part
        JWT, or to ``None`` (apikey-only auth) when no credentials are given.
        """
        if self._token is not None:
            return self._token

        if self._email and self._password:
            import httpx

            resp = httpx.post(
                f"{self._base_url}/auth/v1/token",
                params={"grant_type": "password"},
                headers={"apikey": self._api_key, "Content-Type": "application/json"},
                json={"email": self._email, "password": self._password},
            )
            resp.raise_for_status()
            self._token = resp.json()["access_token"]
            return self._token

        if self._api_key.count(".") == 2:  # legacy anon/service_role JWT
            self._token = self._api_key
            return self._token

        return None

    def _headers(self) -> dict[str, str]:
        headers = {"apikey": self._api_key, "Content-Type": "application/json"}
        token = self._access_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    # -- reads / writes ------------------------------------------------------

    def fetch_existing(self) -> list[StoredLink]:
        import httpx

        resp = httpx.get(
            f"{self._base_url}/functions/v1/select-table",
            params={"table": "links"},
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def save_links(self, links: list[Link]) -> None:
        import httpx

        payload = [link.to_dict() for link in links]
        resp = httpx.post(
            f"{self._base_url}/functions/v1/insert-links",
            headers=self._headers(),
            json=payload,
        )
        resp.raise_for_status()


class MockLinkRepository:
    """Fake implementation for local testing."""

    def fetch_existing(self) -> list[StoredLink]:
        return [
            {"url": "https://example.com/already-saved", "category": "other"},
        ]

    def save_links(self, links: list[Link]) -> None:
        print(f"\n  [MOCK POST] {json.dumps([l.to_dict() for l in links], indent=2)}")
