from __future__ import annotations

import json
import logging
import shutil
import threading
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from icaf.config.settings import initialize_directories, settings
from icaf.clauses.catalog import clause_names, execution_plan
from icaf.core.engine import Engine
from icaf.oam.oam_manager import process_oam
from icaf.utils.logger import logger
from icaf.web.storage import RunStore, utc_now


CLAUSES = clause_names()
WEB_OUTPUT_DIR = settings.OUTPUT_DIR / "web"
ARTIFACTS_DIR = WEB_OUTPUT_DIR / "runs"
STORE = RunStore(WEB_OUTPUT_DIR / "runs.sqlite3")
RUN_LOCK = threading.Lock()


class RunRequest(BaseModel):
    clause: str
    profile: str = "default"
    ssh_ip: str = Field(min_length=1)
    ssh_user: str = Field(min_length=1)
    ssh_password: str = ""
    snmp_user: str = ""
    snmp_auth_pass: str = ""
    snmp_priv_pass: str = ""
    snmp_community: str = ""
    web_login_url: str = ""
    web_username: str = ""
    web_password: str = ""


app = FastAPI(title="ICAF Local Web UI", version="0.1.0")


@app.get("/api/configuration")
def configuration() -> dict[str, object]:
    profile_dir = settings.BASE_DIR / "icaf" / "profile"
    profiles = sorted({path.stem for path in profile_dir.glob("*.yaml")} | {path.stem for path in profile_dir.glob("*.yml")})
    return {
        "clauses": CLAUSES,
        "profiles": profiles or ["default"],
        "testcases": {clause_id: execution_plan(clause_id) for clause_id in CLAUSES},
    }


@app.post("/api/runs", status_code=202)
async def start_run(
    payload: str = Form(...),
    oam_file: Optional[UploadFile] = File(default=None),
) -> dict[str, str]:
    try:
        request = RunRequest.model_validate(json.loads(payload))
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Invalid run configuration") from exc
    if request.clause not in CLAUSES:
        raise HTTPException(status_code=422, detail="Unsupported clause")

    run_id = str(uuid.uuid4())
    run_dir = ARTIFACTS_DIR / run_id
    for directory in (run_dir / "report", run_dir / "screenshots", run_dir / "input"):
        directory.mkdir(parents=True, exist_ok=True)

    oam_path = None
    if oam_file and oam_file.filename:
        suffix = Path(oam_file.filename).suffix.lower()
        if suffix not in {".xlsx", ".xls"}:
            raise HTTPException(status_code=422, detail="OAM file must be an Excel workbook")
        oam_path = run_dir / "input" / f"oam{suffix}"
        with oam_path.open("wb") as destination:
            shutil.copyfileobj(oam_file.file, destination)

    STORE.create_run(
        {
            "id": run_id,
            "clause": request.clause,
            "profile": request.profile,
            "dut_host": request.ssh_ip,
            "ssh_user": request.ssh_user,
            "status": "queued",
            "created_at": utc_now(),
            "artifact_dir": str(run_dir),
        }
    )
    threading.Thread(
        target=_execute_run,
        args=(run_id, request, oam_path),
        daemon=True,
        name=f"icaf-run-{run_id[:8]}",
    ).start()
    return {"id": run_id, "status": "queued"}


@app.get("/api/runs")
def list_runs() -> list[dict[str, object]]:
    return STORE.list_runs()


@app.get("/api/runs/{run_id}")
def run_detail(run_id: str) -> dict[str, object]:
    run = STORE.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@app.get("/api/runs/{run_id}/artifacts/{relative_path:path}")
def artifact(run_id: str, relative_path: str) -> FileResponse:
    run = STORE.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    root = Path(run["artifact_dir"]).resolve()
    requested = (root / relative_path).resolve()
    if root not in requested.parents or not requested.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(requested, filename=requested.name)


def _execute_run(run_id: str, request: RunRequest, oam_path: Optional[Path]) -> None:
    run = STORE.get_run(run_id)
    if run is None:
        return
    run_dir = Path(run["artifact_dir"])
    log_path = run_dir / "logs.txt"
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))

    # Existing terminal/screenshot facilities are process-wide, so serialize runs.
    with RUN_LOCK:
        STORE.update_run(run_id, status="running", started_at=utc_now())
        logger.addHandler(file_handler)
        try:
            initialize_directories()
            oam_context = process_oam(str(oam_path), request.ssh_ip) if oam_path else None
            engine = Engine(
                clause=request.clause,
                profile=request.profile,
                ssh_user=request.ssh_user,
                ssh_ip=request.ssh_ip,
                ssh_password=request.ssh_password,
                snmp_user=request.snmp_user if request.clause == "1.1.1" else None,
                snmp_auth_pass=request.snmp_auth_pass if request.clause == "1.1.1" else None,
                snmp_priv_pass=request.snmp_priv_pass if request.clause == "1.1.1" else None,
                snmp_community=request.snmp_community if request.clause == "1.1.1" else None,
                web_login_url=request.web_login_url if request.clause == "1.1.1" else None,
                web_username=request.web_username if request.clause == "1.1.1" else None,
                web_password=request.web_password if request.clause == "1.1.1" else None,
                oam_context=oam_context,
            )
            result = engine.start()
            _stage_artifacts(run_id, run_dir, result["report_path"], result["context"].evidence.run_dir)
            STORE.update_run(run_id, status="completed", finished_at=utc_now())
        except Exception as exc:
            logger.exception("Compliance check failed")
            STORE.update_run(run_id, status="failed", finished_at=utc_now(), error_message=str(exc))
        finally:
            logger.removeHandler(file_handler)
            file_handler.close()
            STORE.add_evidence(run_id, "log", "Execution log", "logs.txt")


def _stage_artifacts(run_id: str, run_dir: Path, report_path: str, evidence_dir: str) -> None:
    source_report = Path(report_path)
    if source_report.is_file():
        report_relative = Path("report") / source_report.name
        shutil.copy2(source_report, run_dir / report_relative)
        STORE.add_evidence(run_id, "report", "Compliance report", str(report_relative))

    source_evidence = Path(evidence_dir)
    if not source_evidence.exists():
        return
    supported_images = {".png", ".jpg", ".jpeg", ".webp"}
    for image in source_evidence.rglob("*"):
        if not image.is_file() or image.suffix.lower() not in supported_images:
            continue
        target = _unique_path(run_dir / "screenshots" / image.name)
        shutil.copy2(image, target)
        relative = target.relative_to(run_dir)
        STORE.add_evidence(run_id, "screenshot", image.stem, str(relative))


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    index = 2
    while True:
        candidate = path.with_stem(f"{path.stem}-{index}")
        if not candidate.exists():
            return candidate
        index += 1


frontend_dist = settings.BASE_DIR / "webui" / "dist"
if frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")