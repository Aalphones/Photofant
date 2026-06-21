"""Tests für ComfyUIClient (Unit) und /api/comfyui/test-connection (Route)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from photofant.comfyui.client import ComfyUIClient, ComfyUIError
from photofant.main import create_app

# ── ComfyUIClient Unit-Tests ──────────────────────────────────────────────────

def _make_response(status_code: int = 200, json_body: dict | None = None) -> httpx.Response:
    body = json.dumps(json_body or {}).encode()
    request = httpx.Request("GET", "http://127.0.0.1:8188/system_stats")
    return httpx.Response(
        status_code,
        content=body,
        headers={"content-type": "application/json"},
        request=request,
    )


class TestComfyUIClientSuccess:
    @patch("photofant.comfyui.client.httpx.get")
    def test_returns_json_on_200(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _make_response(200, {"system": {"comfyui_version": "0.3.7"}})
        client = ComfyUIClient("http://127.0.0.1:8188")
        result = client.system_stats()
        assert result == {"system": {"comfyui_version": "0.3.7"}}
        mock_get.assert_called_once_with("http://127.0.0.1:8188/system_stats", timeout=10.0)


class TestComfyUIClientErrors:
    @patch("photofant.comfyui.client.httpx.get", side_effect=httpx.ConnectError("refused"))
    def test_connect_error_raises_comfyui_error(self, _: MagicMock) -> None:
        client = ComfyUIClient("http://127.0.0.1:8188")
        with pytest.raises(ComfyUIError) as exc_info:
            client.system_stats()
        error = exc_info.value
        assert "Verbindung abgelehnt" in error.what_found
        assert error.next_step != ""

    @patch("photofant.comfyui.client.httpx.get", side_effect=httpx.TimeoutException("timed out"))
    def test_timeout_raises_comfyui_error(self, _: MagicMock) -> None:
        client = ComfyUIClient("http://127.0.0.1:8188", timeout=5.0)
        with pytest.raises(ComfyUIError) as exc_info:
            client.system_stats()
        error = exc_info.value
        assert "Timeout" in error.what_found
        assert "5" in error.what_expected

    @patch("photofant.comfyui.client.httpx.get")
    def test_http_error_status_raises_comfyui_error(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _make_response(503)
        client = ComfyUIClient("http://127.0.0.1:8188")
        with pytest.raises(ComfyUIError) as exc_info:
            client.system_stats()
        error = exc_info.value
        assert "503" in error.what_found


# ── Route-Test: POST /api/comfyui/test-connection ────────────────────────────

@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
@patch("photofant.api.comfyui.ComfyUIClient")
async def test_test_connection_success(mock_client_cls: MagicMock, app, tmp_path, monkeypatch) -> None:
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        json.dumps({"comfyui": {"enabled": True, "base_url": "http://127.0.0.1:8188",
                                "client_id": "photofant", "output_dir": "", "timeout": 10}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("PHOTOFANT_SETTINGS_PATH", str(settings_file))

    mock_instance = MagicMock()
    mock_instance.system_stats.return_value = {"system": {"comfyui_version": "0.3.7"}}
    mock_client_cls.return_value = mock_instance

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/comfyui/test-connection")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "0.3.7" in body["detail"]


@pytest.mark.asyncio
@patch("photofant.api.comfyui.ComfyUIClient")
async def test_test_connection_failure(mock_client_cls: MagicMock, app, tmp_path, monkeypatch) -> None:
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        json.dumps({"comfyui": {"enabled": True, "base_url": "http://127.0.0.1:9999",
                                "client_id": "photofant", "output_dir": "", "timeout": 10}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("PHOTOFANT_SETTINGS_PATH", str(settings_file))

    mock_instance = MagicMock()
    mock_instance.system_stats.side_effect = ComfyUIError(
        what_expected="ComfyUI unter http://127.0.0.1:9999",
        what_found="Verbindung abgelehnt",
        next_step="Prüfen, ob ComfyUI läuft",
    )
    mock_client_cls.return_value = mock_instance

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/comfyui/test-connection")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert "Verbindung abgelehnt" in body["detail"]
