"""ComfyUI HTTP client — wraps GET /system_stats with typed error classes."""
from __future__ import annotations

import httpx


class ComfyUIError(Exception):
    """Structured connectivity error: what was expected, what was found, next step."""

    def __init__(self, what_expected: str, what_found: str, next_step: str) -> None:
        self.what_expected = what_expected
        self.what_found = what_found
        self.next_step = next_step
        super().__init__(f"{what_expected} — {what_found} — {next_step}")


class ComfyUIClient:
    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self._base = base_url.rstrip("/")
        self._timeout = timeout

    def system_stats(self) -> dict[str, object]:
        """GET /system_stats — raises ComfyUIError on any connectivity failure."""
        url = f"{self._base}/system_stats"
        try:
            response = httpx.get(url, timeout=self._timeout)
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]
        except httpx.ConnectError as exc:
            raise ComfyUIError(
                what_expected=f"ComfyUI unter {self._base}",
                what_found="Verbindung abgelehnt",
                next_step="Prüfen, ob ComfyUI läuft und die URL korrekt ist",
            ) from exc
        except httpx.TimeoutException as exc:
            raise ComfyUIError(
                what_expected=f"Antwort in {self._timeout:.0f} s",
                what_found="Timeout",
                next_step="Timeout erhöhen oder ComfyUI-Last prüfen",
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise ComfyUIError(
                what_expected="HTTP 200",
                what_found=f"HTTP {exc.response.status_code}",
                next_step="ComfyUI-Logs prüfen",
            ) from exc
