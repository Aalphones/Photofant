"""ComfyUI HTTP client — wraps /system_stats, /upload/image, /prompt, /history."""
from __future__ import annotations

from pathlib import Path
from typing import Any

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

    def upload_image(self, file_path: Path) -> str:
        """POST /upload/image — returns the filename ComfyUI assigned."""
        url = f"{self._base}/upload/image"
        try:
            with file_path.open("rb") as file_handle:
                response = httpx.post(
                    url,
                    files={"image": (file_path.name, file_handle, "image/png")},
                    timeout=self._timeout,
                )
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            return str(data["name"])
        except httpx.ConnectError as exc:
            raise ComfyUIError(
                what_expected=f"ComfyUI unter {self._base}",
                what_found="Verbindung abgelehnt beim Bild-Upload",
                next_step="Prüfen, ob ComfyUI läuft und die URL korrekt ist",
            ) from exc
        except httpx.TimeoutException as exc:
            raise ComfyUIError(
                what_expected=f"Antwort in {self._timeout:.0f} s",
                what_found="Timeout beim Bild-Upload",
                next_step="Timeout erhöhen oder ComfyUI-Last prüfen",
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise ComfyUIError(
                what_expected="HTTP 200 beim Bild-Upload",
                what_found=f"HTTP {exc.response.status_code}",
                next_step="ComfyUI-Logs prüfen",
            ) from exc
        except (KeyError, ValueError) as exc:
            raise ComfyUIError(
                what_expected="{'name': ...} in Upload-Antwort",
                what_found=f"Unerwartete Antwort: {exc}",
                next_step="ComfyUI-Version prüfen",
            ) from exc

    def submit_prompt(self, prompt: dict[str, Any], client_id: str = "photofant") -> str:
        """POST /prompt — returns prompt_id."""
        url = f"{self._base}/prompt"
        try:
            response = httpx.post(
                url,
                json={"prompt": prompt, "client_id": client_id},
                timeout=self._timeout,
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            return str(data["prompt_id"])
        except httpx.ConnectError as exc:
            raise ComfyUIError(
                what_expected=f"ComfyUI unter {self._base}",
                what_found="Verbindung abgelehnt beim Prompt-Submit",
                next_step="Prüfen, ob ComfyUI läuft und die URL korrekt ist",
            ) from exc
        except httpx.TimeoutException as exc:
            raise ComfyUIError(
                what_expected=f"Antwort in {self._timeout:.0f} s",
                what_found="Timeout beim Prompt-Submit",
                next_step="Timeout erhöhen oder ComfyUI-Last prüfen",
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise ComfyUIError(
                what_expected="HTTP 200 beim Prompt-Submit",
                what_found=f"HTTP {exc.response.status_code}",
                next_step="ComfyUI-Logs prüfen",
            ) from exc
        except (KeyError, ValueError) as exc:
            raise ComfyUIError(
                what_expected="{'prompt_id': ...} in Prompt-Antwort",
                what_found=f"Unerwartete Antwort: {exc}",
                next_step="ComfyUI-Version prüfen",
            ) from exc

    def get_history(self, prompt_id: str) -> dict[str, Any]:
        """GET /history/{prompt_id} — returns history dict, empty dict on error."""
        url = f"{self._base}/history/{prompt_id}"
        try:
            response = httpx.get(url, timeout=self._timeout)
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError):
            return {}

    def view_image(self, filename: str, subfolder: str = "", image_type: str = "output") -> bytes:
        """GET /view — download an output image by filename. Raises ComfyUIError on failure."""
        url = f"{self._base}/view"
        params = {"filename": filename, "subfolder": subfolder, "type": image_type}
        try:
            response = httpx.get(url, params=params, timeout=self._timeout)
            response.raise_for_status()
            return response.content
        except httpx.ConnectError as exc:
            raise ComfyUIError(
                what_expected=f"ComfyUI unter {self._base}",
                what_found="Verbindung abgelehnt beim Bild-Download",
                next_step="Prüfen, ob ComfyUI läuft und die URL korrekt ist",
            ) from exc
        except httpx.TimeoutException as exc:
            raise ComfyUIError(
                what_expected=f"Antwort in {self._timeout:.0f} s",
                what_found="Timeout beim Bild-Download",
                next_step="Timeout erhöhen oder ComfyUI-Last prüfen",
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise ComfyUIError(
                what_expected="HTTP 200 beim Bild-Download",
                what_found=f"HTTP {exc.response.status_code}",
                next_step=f"Datei '{filename}' in ComfyUI output-Ordner prüfen",
            ) from exc
