import asyncio

import httpx

from app.fast_api_app import app, settings


def test_health_session_and_console_trace(monkeypatch, capsys) -> None:
    monkeypatch.setattr(settings, "otel_console", True)

    async def check() -> None:
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client,
        ):
            response = await client.get("/healthz")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

            session = await client.post("/apps/app/users/demo/sessions", json={})
            assert session.status_code == 200
            assert session.json()["id"]

    asyncio.run(check())
    output = capsys.readouterr().out
    assert "vyaparsetu.http.request" in output
    assert "trace_id" in output
