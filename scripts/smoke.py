"""Exercise the running local product using its real HTTP API and worker."""

import json
import time
from pathlib import Path

import httpx
from repairlab.config import Settings

settings = Settings()
with httpx.Client(
    base_url="http://127.0.0.1:8000",
    headers={"Authorization": "Bearer " + settings.api_token},
    timeout=15,
    trust_env=False,
) as client:
    health = client.get("/health").raise_for_status().json()
    assert not health["model_calls_enabled"] and not health["embedding_enabled"]
    environment = client.get("/api/environment").raise_for_status().json()
    assert environment["docker"], environment
    demo = client.post("/api/demo").raise_for_status().json()
    run = (
        client.post(
            "/api/runs",
            json={
                "issue_id": demo["issue"]["id"],
                "strategy": "adaptive",
                "model_source": "scripted",
                "script": "repair",
            },
            headers={"Idempotency-Key": "startup-smoke-" + demo["issue"]["id"]},
        )
        .raise_for_status()
        .json()
    )
    started = time.monotonic()
    while time.monotonic() - started < 90:
        detail = client.get("/api/runs/" + run["id"]).raise_for_status().json()
        if detail["status"] in {"succeeded", "failed", "cancelled"}:
            break
        time.sleep(0.3)
    assert detail["status"] == "succeeded", detail.get("terminal_reason")
    assert detail["spent"] == 0 and len(detail["agents"]) == 4
    exported = client.get("/api/runs/" + run["id"] + "/export").raise_for_status().json()
    (settings.data_root / "startup-smoke.json").write_text(
        json.dumps(exported, ensure_ascii=False, indent=2), "utf-8"
    )
    ui = httpx.get("http://127.0.0.1:5173", trust_env=False).raise_for_status()
    assert "RepairLab" in ui.text
    summary = {
        "run_id": run["id"],
        "status": detail["status"],
        "model_source": detail["model_source"],
        "model_cost_cny": detail["spent"],
        "agents": len(detail["agents"]),
        "receipts": len(detail["receipts"]),
        "verification_passed": detail["verifications"][-1]["passed"],
        "model_calls_enabled": health["model_calls_enabled"],
        "ui_http_status": ui.status_code,
        "ui_url": "http://localhost:5173",
    }
    path = Path("docs/verification/startup-smoke.json")
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), "utf-8")
    print(json.dumps(summary, ensure_ascii=False))
