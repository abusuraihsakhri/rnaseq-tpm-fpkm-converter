"""
FastAPI REST API Server for Rnaseq Tpm Fpkm Converter.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from rnaseq_norm import calculate_metrics
from pydantic import BaseModel
from .base import AuditLogger, PHIGuard
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Rnaseq Tpm Fpkm Converter API",
    description="RNA-seq TPM and FPKM normalization with an optional legacy audit service",
    version="3.1.0",
)


class NormalizationRequest(BaseModel):
    counts: List[float]
    lengths_bp: List[float]
    library_size: Optional[float] = None


@app.post("/api/normalize")
def api_normalize(payload: NormalizationRequest):
    try:
        return calculate_metrics(payload.counts, payload.lengths_bp, payload.library_size)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


class ChatRequest(BaseModel):
    query: str


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "rnaseq-tpm-fpkm-converter", "domain": "RNA-seq expression normalization", "version": "3.1.0"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "NOMINAL_OPTIMAL"
    }


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    dossier = supervisor.process_task(payload)
    return dossier.to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/audit/logs")
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}


# Register static frontend last so API routes retain precedence.
app.mount("/", StaticFiles(directory=str(Path(__file__).resolve().parent.parent / "web"), html=True), name="web")
