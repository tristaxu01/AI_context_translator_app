from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_settings_roundtrip() -> None:
    response = client.get("/api/settings")
    assert response.status_code == 200
    assert response.json()["target_language"] == "Spanish"

    update = client.put(
        "/api/settings",
        json={
            "target_language": "French",
            "voice": "nova",
            "output_mode": "audio",
        },
    )
    assert update.status_code == 200
    assert update.json() == {
        "target_language": "French",
        "voice": "nova",
        "output_mode": "audio",
    }


def test_file_translation_uses_context(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))

    response = client.post(
        "/api/files/translate",
        files={"file": ("meeting.wav", b"audio-data", "audio/wav")},
        data={
            "target_language": "German",
            "background_context": "medical conference",
            "voice": "alloy",
            "output_mode": "text",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "medical conference" in payload["translation"]
    assert payload["target_language"] == "German"


def test_live_websocket_includes_context() -> None:
    with client.websocket_connect("/ws/live") as socket:
        socket.send_text(
            '{"transcript":"hello doctor","target_language":"Italian","background_context":"medical conference","voice":"alloy","output_mode":"text"}'
        )

        msg = socket.receive_json()
        while msg["type"] != "translation_complete":
            msg = socket.receive_json()

    assert "medical conference" in msg["translation"]
    assert msg["target_language"] == "Italian"
