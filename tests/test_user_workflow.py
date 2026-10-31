from repairlab.db import RunRow
from repairlab.domain import TaskContract


async def test_public_model_config_never_returns_key(client, app):
    settings = app.state.settings
    settings.deepseek_api_key = "sk-private-config-value"
    disabled = (await client.get("/api/config")).json()
    assert disabled["model_calls_enabled"] is False
    settings.model_calls_enabled = True
    settings.input_cny_per_million = 2
    settings.output_cny_per_million = 8
    settings.price_snapshot = "test-price-snapshot"
    response = await client.get("/api/config")
    assert settings.deepseek_api_key not in response.text
    assert response.json()["model_ready"] and response.json()["default_source"] == "deepseek"
    settings.deepseek_api_key = ""
    assert (await client.get("/api/config")).json()["reason"] == "api_key_missing"


async def test_run_limits_are_lowered_and_preserved_on_retry(client, app, demo):
    limits = {"max_cost_cny": 0.5, "max_calls": 8, "max_seconds": 120}
    body = {"issue_id": demo["issue"]["id"], "limits": limits}
    headers = {"Idempotency-Key": "bounded-run"}
    submitted = await client.post("/api/runs", json=body, headers=headers)
    assert submitted.status_code == 200, submitted.text
    run = submitted.json()
    assert run["versions"]["limits"] == limits
    with app.state.db.sessions() as session:
        contract = app.state.ledger.contract(session, session.get(RunRow, run["id"]))
        assert contract.max_cost_cny == 0.5 and contract.max_calls == 8 and contract.max_seconds == 120
    duplicate = await client.post("/api/runs", json=body, headers=headers)
    assert duplicate.json()["id"] == run["id"]
    changed = await client.post(
        "/api/runs", json={**body, "limits": {**limits, "max_cost_cny": 0.4}}, headers=headers
    )
    assert changed.status_code == 409
    await client.post(f"/api/runs/{run['id']}/control/cancel")
    retry = (await client.post(f"/api/runs/{run['id']}/control/retry")).json()
    assert retry["id"] != run["id"] and retry["versions"]["limits"] == limits


async def test_run_cannot_raise_issue_budget(client, app, demo):
    contract = TaskContract.model_validate(demo["issue"]["contract"]).model_copy(
        update={"max_cost_cny": 0.25, "max_calls": 5, "max_seconds": 60}
    )
    issue = app.state.platform.create_issue(contract)
    response = await client.post(
        "/api/runs",
        json={"issue_id": issue["id"], "limits": {"max_cost_cny": 1, "max_calls": 5, "max_seconds": 60}},
    )
    assert response.status_code == 409 and "exceed" in response.json()["detail"]


async def test_ready_validation_before_real_run_is_queued(client, app, demo):
    app.state.settings.model_calls_enabled = True
    app.state.settings.deepseek_api_key = ""
    response = await client.post(
        "/api/runs", json={"issue_id": demo["issue"]["id"], "model_source": "deepseek"}
    )
    assert response.status_code == 409 and response.json()["detail"] == "api_key_missing"
