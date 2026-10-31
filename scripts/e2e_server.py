"""Start real API and worker for Playwright; no fake backend or model endpoints."""

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
mock_mode = os.environ.get("E2E_MOCK_DEEPSEEK") == "true"
api_port = os.environ.get("E2E_API_PORT", "8000")
data_directory = str(ROOT / (".cache/e2e-real-mode-data" if mock_mode else ".cache/e2e-data"))
os.environ.update(
    {
        "MODEL_CALLS_ENABLED": "false",
        "EMBEDDING_ENABLED": "false",
        "LANGSMITH_TRACING": "false",
        "DATA_ROOT": data_directory,
        "DATABASE_URL": os.environ.get(
            "E2E_DATABASE_URL", "sqlite:///" + data_directory.replace("\\", "/") + "/ledger.db"
        ),
        "REPOSITORY_ROOT": str(ROOT / "fixtures/repos"),
        "TASK_ROOT": str(ROOT / "fixtures/tasks"),
        "API_TOKEN": "local-dev-change-me",
    }
)
if mock_mode:
    # Test-only factory forces an in-memory HTTP transport in BOTH API and worker.
    os.environ.update(
        {
            "MODEL_CALLS_ENABLED": "true",
            "DEEPSEEK_API_KEY": "mock-transport-only",
            "INPUT_CNY_PER_MILLION": "2",
            "OUTPUT_CNY_PER_MILLION": "8",
            "PRICE_SNAPSHOT": "e2e-mock-pricing",
        }
    )
Path(os.environ["DATA_ROOT"]).mkdir(parents=True, exist_ok=True)
subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
processes = [
    subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "tests.e2e_mock_app:create_mock_app" if mock_mode else "repairlab.api:create_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            api_port,
        ]
    ),
    subprocess.Popen(
        [sys.executable, "-m", "tests.e2e_mock_app"]
        if mock_mode
        else [sys.executable, "-m", "repairlab.cli", "worker"]
    ),
]
try:
    while all(p.poll() is None for p in processes):
        time.sleep(0.2)
finally:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        process.wait(timeout=10)
