"""FastAPI controller for iMT1026 v3 analyses."""

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse

from yeastmodels_app.services import JobService, YeastModelService


service = YeastModelService()
job_service = JobService(analysis_service=service)
app = FastAPI(title="iMT1026 v3 FBA API", version="0.1.0")


@app.get("/")
def root() -> dict[str, object]:
    return {
        "model": "iMT1026V3",
        "endpoints": [
            "/health",
            "/model/summary",
            "/medium",
            "/medium/conditions",
            "/medium/compare",
            "/medium/interpretation",
            "/network/views",
            "/network",
            "/fva/scopes",
            "/fva",
            "/fba",
            "/jobs",
            "/jobs/fba",
            "/jobs/fva",
            "/jobs/network",
        ],
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/model/summary")
def model_summary() -> dict[str, object]:
    return service.get_summary().to_dict()


@app.get("/medium")
def medium_summary() -> dict[str, object]:
    return service.get_medium_summary().to_dict()


@app.get("/medium/conditions")
def medium_conditions() -> list[dict[str, object]]:
    return [condition.to_dict() for condition in service.get_medium_conditions()]


@app.get("/medium/compare")
def compare_medium_conditions() -> list[dict[str, object]]:
    return [result.to_dict() for result in service.compare_medium_conditions()]


@app.get("/medium/interpretation")
def interpret_medium_conditions() -> dict[str, object]:
    comparisons = service.compare_medium_conditions()
    return service.interpret_medium_comparisons(comparisons).to_dict()


@app.get("/network/views")
def network_views() -> list[dict[str, str]]:
    return service.get_network_view_options()


@app.get("/network")
def network_graph(
    view_id: str = "exchange_to_biomass",
    condition_id: str = "default",
    metabolite_id: str = "met_L_c",
) -> dict[str, object]:
    graph = service.build_network_graph(
        view_id=view_id,
        condition_id=condition_id,
        metabolite_id=metabolite_id,
    )
    payload = graph.to_dict()
    payload["dot"] = graph.to_dot()
    return payload


@app.get("/fva/scopes")
def fva_scopes() -> list[dict[str, str]]:
    return service.get_fva_scope_options()


@app.get("/fva")
def run_fva(
    condition_id: str = "default",
    scope: str = "open_exchange",
    fraction_of_optimum: float = 0.95,
) -> dict[str, object]:
    return service.run_fva_isolated(
        condition_id=condition_id,
        scope=scope,
        fraction_of_optimum=fraction_of_optimum,
    )


@app.post("/fba")
def run_fba() -> dict[str, object]:
    return service.run_fba().to_dict()


@app.post("/jobs/fba")
def create_fba_job(
    parameters: dict[str, object] | None = Body(default=None),
) -> dict[str, object]:
    return job_service.run_fba_job(parameters or {}).to_dict()


@app.post("/jobs/fva")
def create_fva_job(
    parameters: dict[str, object] | None = Body(default=None),
) -> dict[str, object]:
    return job_service.run_fva_job(parameters or {}).to_dict()


@app.post("/jobs/network")
def create_network_job(
    parameters: dict[str, object] | None = Body(default=None),
) -> dict[str, object]:
    return job_service.run_network_job(parameters or {}).to_dict()


@app.get("/jobs")
def list_jobs(limit: int | None = None) -> list[dict[str, object]]:
    return [record.to_dict() for record in job_service.list_jobs(limit=limit)]


@app.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, object]:
    record = job_service.get_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Unknown job '{job_id}'.")
    return record.to_dict()


@app.get("/jobs/{job_id}/download")
def download_job(job_id: str, format: str = "json") -> FileResponse:  # noqa: A002
    if format not in {"json", "csv", "dot"}:
        raise HTTPException(status_code=400, detail="format must be json, csv, or dot.")
    try:
        path, media_type, filename = job_service.get_download(job_id, format)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(path, media_type=media_type, filename=filename)
