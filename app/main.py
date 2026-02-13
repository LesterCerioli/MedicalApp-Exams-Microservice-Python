from typing import List
from app import auth_service, exam_analysis_audit_service
from fastapi import FastAPI, HTTPException, Depends, Header, Query, Path
from datetime import date, datetime, timedelta
import asyncio
import logging
from typing import Dict, Any, Optional
from uuid import UUID


import jwt
from app import exam_analysis_service
from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.auth_service import auth_token_service
from app.database import db
from app.exam_service import exam_service
from app.schemas import (  # NOTA: os schemas precisarão ser ajustados para REMOVER o campo 'token'
    AnalysesByTypeQuery,
    AnalysesByTypeRequest,
    AnalysesWithoutResultQuery,
    AnalysesWithoutResultRequest,
    AnalysisStatisticsQuery,
    AnalysisStatisticsRequest,
    AuditByDateRangeQuery,
    AuditByOrganizationQuery,
    AuditByUserQuery,
    AuditForAnalysisQuery,
    AuthTokenRequest,
    CreateExamAnalysisRequest,
    DeleteExamAnalysisRequest,
    ExamAnalysisAuditResponse,
    ExamCountsQuery,
    GetExamAnalysisRequest,
    OrganizationAnalysesQuery,
    OrganizationAnalysesRequest,
    OrganizationExamsQuery,
    PaginatedAuditResponse,
    PatientExamsQuery,
    TokenValidationRequest,      # será removido posteriormente
    HealthCheckRequest,          # será removido
    RootRequest,                # será removido
    CreateExamRequest,
    GetExamRequest,
    UpcomingExamsQuery,
    UpdateExamAnalysisBody,
    UpdateExamAnalysisRequest,
    UpdateExamRequest,
    DeleteExamRequest,
    RestoreExamRequest,
    OrganizationExamsRequest,
    PatientExamsRequest,
    UpdateExamStatusRequest,
    BulkUpdateStatusRequest,
    ExamCountsRequest,
    UpcomingExamsRequest,
    ExamsWithoutPatientRequest,
)

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# FastAPI app initialization
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Medical App - Exams Microservice",
    description="API from Exams Microservice",
)

# -----------------------------------------------------------------------------
# CORS middleware
# -----------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://lts-us-website.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Event handlers
# -----------------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    db.init_db()
    logger.info("Database initialized")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Exam service stopped")

# -----------------------------------------------------------------------------
# JWT token validation dependency (HEADER only)
# -----------------------------------------------------------------------------
async def get_token_data_from_header(authorization: str = Header(...)) -> Dict[str, Any]:
    """
    Extrai e valida o token JWT do header Authorization: Bearer <token>.
    Retorna os dados decodificados do token.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    if not token:
        raise HTTPException(status_code=401, detail="Token is required")

    if not auth_token_service.validate_token(token):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    try:
        decoded_token = jwt.decode(
            token,
            auth_token_service.jwt_secret,
            algorithms=["HS256"]
        )
        return {
            "client_id": decoded_token.get("client_id"),
            "token": token,
        }
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Token validation failed: {str(e)}"
        )

# -----------------------------------------------------------------------------
# Função auxiliar para manter compatibilidade durante migração (pode ser removida depois)
# -----------------------------------------------------------------------------
async def validate_token_from_body(token: str) -> Dict[str, Any]:
    """DEPRECATED: use get_token_data_from_header instead."""
    return await get_token_data_from_header(f"Bearer {token}")

# =============================================================================
# AUTHENTICATION ENDPOINTS
# =============================================================================

@app.post("/auth/token", tags=["auth"])
async def generate_auth_token(auth_request: AuthTokenRequest):
    """
    Generate JWT authentication token.
    - **client_id**: Client identifier
    - **client_secret**: Client secret
    """
    try:
        if not auth_request.client_id or not auth_request.client_secret:
            raise HTTPException(
                status_code=400,
                detail="Both 'client_id' and 'client_secret' are required"
            )
        result = auth_token_service.generate_token(
            auth_request.client_id,
            auth_request.client_secret
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/auth/validate", tags=["auth"])
async def validate_auth_token(
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """
    Validate JWT authentication token.
    Token must be sent in Authorization header: Bearer <token>
    """
    return {"valid": True, "message": "Token is valid", "client_id": token_data["client_id"]}

@app.get("/auth/token/{client_id}", tags=["auth"])
async def get_valid_token(client_id: str):
    """Get valid token for client_id (if any). This endpoint is public."""
    token = auth_token_service.get_valid_token(client_id)
    if not token:
        raise HTTPException(status_code=404, detail="No valid token found")
    return {"token": token}

@app.delete("/auth/cleanup", tags=["auth"])
async def cleanup_tokens(
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """
    Clean up expired tokens (admin endpoint).
    Requires valid JWT token in Authorization header.
    """
    # Aqui você pode adicionar verificação de permissão de admin se necessário
    deleted_count = auth_token_service.cleanup_expired_tokens()
    return {"message": f"Cleaned up {deleted_count} expired tokens"}

# =============================================================================
# EXAMS ENDPOINTS
# =============================================================================

@app.post("/exams/create", tags=["exams"])
async def create_exam(
    request: CreateExamRequest,  # ATENÇÃO: remova o campo 'token' deste schema!
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """
    Create a new medical exam.
    Authentication: Bearer token in Authorization header.
    """
    try:
        result = await exam_service.create_exam(
            organization_name=request.organization_name,
            exam_type=request.exam_type,
            patient_name=request.patient_name,
            status=request.status,
            requested_at=request.requested_at,
            notes=request.notes,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/exams/get", tags=["exams"])
async def get_exam(
    request: GetExamRequest,  # remova o campo 'token'
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """
    Retrieve a medical exam by its ID.
    Authentication: Bearer token in Authorization header.
    """
    try:
        exam = await exam_service.get_exam_by_id(request.exam_id)
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")
        return exam
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@app.delete("/exams/delete", tags=["exams"])
async def delete_exam(
    request: DeleteExamRequest,  # remova o campo 'token'
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """
    Soft delete a medical exam.
    Authentication: Bearer token in Authorization header.
    """
    try:
        success = await exam_service.delete_exam(request.exam_id)
        if not success:
            raise HTTPException(status_code=404, detail="Exam not found or already deleted")
        return {"success": True, "message": "Exam deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/exams/restore", tags=["exams"])
async def restore_exam(
    request: RestoreExamRequest,  
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """
    Restore a soft‑deleted medical exam.
    Authentication: Bearer token in Authorization header.
    """
    try:
        restored = await exam_service.restore_exam(request.exam_id)
        if not restored:
            raise HTTPException(status_code=404, detail="Exam not found or not deleted")
        return restored
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/exams/organization", tags=["exams"])
async def get_organization_exams(
    request: OrganizationExamsRequest,  # remova o campo 'token'
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """
    List exams for a specific organization with optional filters and pagination.
    Authentication: Bearer token in Authorization header.
    """
    try:
        result = await exam_service.get_organization_exams(
            organization_id=request.organization_id,
            patient_id=request.patient_id,
            status=request.status,
            exam_type=request.exam_type,
            start_date=request.start_date,
            end_date=request.end_date,
            page=request.page,
            page_size=request.page_size,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/exams/patient", tags=["exams"])
async def get_patient_exams(
    request: PatientExamsRequest,  # remova o campo 'token'
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """
    List exams for a specific patient with optional filters and pagination.
    Authentication: Bearer token in Authorization header.
    """
    try:
        result = await exam_service.get_patient_exams(
            patient_id=request.patient_id,
            organization_id=request.organization_id,
            status=request.status,
            start_date=request.start_date,
            end_date=request.end_date,
            page=request.page,
            page_size=request.page_size,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/exams/status", tags=["exams"])
async def update_exam_status(
    request: UpdateExamStatusRequest,  # remova o campo 'token'
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """
    Update only the status of an exam.
    Authentication: Bearer token in Authorization header.
    """
    try:
        success = await exam_service.update_exam_status(request.exam_id, request.status)
        if not success:
            raise HTTPException(status_code=404, detail="Exam not found or already deleted")
        return {"success": True, "message": f"Status updated to {request.status}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/exams/bulk-status", tags=["exams"])
async def bulk_update_status(
    request: BulkUpdateStatusRequest,  # remova o campo 'token'
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """
    Update the status of multiple exams at once.
    Returns the number of successfully updated exams.
    Authentication: Bearer token in Authorization header.
    """
    try:
        updated_count = await exam_service.bulk_update_status(
            exam_ids=request.exam_ids,
            status=request.status,
        )
        return {
            "success": True,
            "updated_count": updated_count,
            "message": f"Updated {updated_count} exams to status {request.status}",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/exams/counts-by-status", tags=["exams"])
async def get_exam_counts_by_status(
    request: ExamCountsRequest,  # remova o campo 'token'
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """
    Get count of exams grouped by status for an organization,
    optionally filtered by date range.
    Authentication: Bearer token in Authorization header.
    """
    try:
        counts = await exam_service.get_exam_counts_by_status(
            organization_id=request.organization_id,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        return counts
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/exams/upcoming", tags=["exams"])
async def get_upcoming_exams(
    request: UpcomingExamsRequest,  # remova o campo 'token'
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """
    Fetch exams scheduled within a date range (typically upcoming).
    Authentication: Bearer token in Authorization header.
    """
    try:
        result = await exam_service.get_upcoming_exams(
            organization_id=request.organization_id,
            from_date=request.from_date,
            to_date=request.to_date,
            page=request.page,
            page_size=request.page_size,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/exams/without-patient", tags=["exams"])
async def get_exams_without_patient(
    request: ExamsWithoutPatientRequest,  # remova o campo 'token'
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """
    Fetch all exams for an organization that are not associated with any patient.
    Authentication: Bearer token in Authorization header.
    """
    try:
        exams = await exam_service.get_exams_without_patient(request.organization_id)
        return {"exams": exams, "count": len(exams)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/exams/organization/{organization_name}", tags=["exams"])
async def get_organization_exams(
    organization_name: str = Path(...),
    query: OrganizationExamsQuery = Depends(),
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """List exams for an organization with filters."""
    try:
        result = await exam_service.get_organization_exams(
            organization_name=organization_name,
            patient_name=query.patient_name,
            status=query.status,
            exam_type=query.exam_type,
            start_date=query.start_date,
            end_date=query.end_date,
            page=query.page,
            page_size=query.page_size,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/exams/patient", tags=["exams"])
async def get_patient_exams(
    query: PatientExamsQuery = Depends(),
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """List exams for a patient with filters."""
    try:
        result = await exam_service.get_patient_exams(
            patient_name=query.patient_name,  # ajuste conforme serviço
            organization_name=query.organization_name,
            status=query.status,
            start_date=query.start_date,
            end_date=query.end_date,
            page=query.page,
            page_size=query.page_size,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@app.get("/exams/counts-by-status", tags=["exams"])
async def get_exam_counts_by_status(
    organization_name: str = Query(...),
    query: ExamCountsQuery = Depends(),
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """Get exam counts grouped by status."""
    try:
        counts = await exam_service.get_exam_counts_by_status(
            organization_name=organization_name,
            start_date=query.start_date,
            end_date=query.end_date,
        )
        return counts
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/exams/upcoming", tags=["exams"])
async def get_upcoming_exams(
    organization_name: str = Query(...),
    query: UpcomingExamsQuery = Depends(),
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """Fetch exams scheduled within a date range."""
    try:
        result = await exam_service.get_upcoming_exams(
            organization_name=organization_name,
            from_date=query.from_date,
            to_date=query.to_date,
            page=query.page,
            page_size=query.page_size,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# EXAM ANALYSIS ENDPOINTS
# =============================================================================

@app.post("/exam-analyses/create", tags=["exam-analyses"])
async def create_exam_analysis(
    request: CreateExamAnalysisRequest,  # remova o campo 'token'
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """
    Create a new exam analysis record.
    Authentication: Bearer token in Authorization header.
    """
    try:
        result = await exam_analysis_service.create_exam_analysis(
            organization_name=request.organization_name,
            exam_type=request.exam_type,
            original_results=request.original_results,
            exam_date=request.exam_date,
            exam_result=request.exam_result,
            observations=request.observations,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/exam-analyses/update", tags=["exam-analyses"])
async def update_exam_analysis(
    request: UpdateExamAnalysisRequest,  # remova o campo 'token'
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """
    Update an existing exam analysis.
    Only fields with non-None values will be updated.
    Authentication: Bearer token in Authorization header.
    """
    try:
        updated = await exam_analysis_service.update_exam_analysis(
            analysis_id=request.analysis_id,
            exam_type=request.exam_type,
            exam_date=request.exam_date,
            original_results=request.original_results,
            exam_result=request.exam_result,
            observations=request.observations,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Exam analysis not found")
        return updated
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/exam-analyses/delete", tags=["exam-analyses"])
async def delete_exam_analysis(
    request: DeleteExamAnalysisRequest,  # remova o campo 'token'
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """
    Permanently delete an exam analysis.
    Authentication: Bearer token in Authorization header.
    """
    try:
        success = await exam_analysis_service.delete_exam_analysis(request.analysis_id)
        if not success:
            raise HTTPException(status_code=404, detail="Exam analysis not found")
        return {"success": True, "message": "Exam analysis deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/exam-analyses/{analysis_id}", tags=["exam-analyses"])
async def get_exam_analysis(
    analysis_id: UUID = Path(...),
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """Retrieve an exam analysis by ID."""
    try:
        analysis = await exam_analysis_service.get_exam_analysis_by_id(analysis_id)
        if not analysis:
            raise HTTPException(status_code=404, detail="Exam analysis not found")
        return analysis
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.patch("/exam-analyses/{analysis_id}", tags=["exam-analyses"])
async def update_exam_analysis(
    analysis_id: UUID = Path(...),
    body: UpdateExamAnalysisBody = None,
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """Partially update an exam analysis."""
    try:
        updated = await exam_analysis_service.update_exam_analysis(
            analysis_id=analysis_id,
            exam_type=body.exam_type,
            exam_date=body.exam_date,
            original_results=body.original_results,
            exam_result=body.exam_result,
            observations=body.observations,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Exam analysis not found")
        return updated
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/exam-analyses/{analysis_id}", tags=["exam-analyses"])
async def delete_exam_analysis(
    analysis_id: UUID = Path(...),
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """Permanently delete an exam analysis."""
    try:
        success = await exam_analysis_service.delete_exam_analysis(analysis_id)
        if not success:
            raise HTTPException(status_code=404, detail="Exam analysis not found")
        return {"success": True, "message": "Exam analysis deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/exam-analyses/organization", tags=["exam-analyses"])
async def get_organization_analyses(
    request: OrganizationAnalysesRequest,  
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """
    List exam analyses for a specific organization with optional filters and pagination.
    Authentication: Bearer token in Authorization header.
    """
    try:
        # Aplica datas padrão se não informadas
        if request.end_date is None:
            request.end_date = datetime.utcnow()
        if request.start_date is None:
            request.start_date = request.end_date - timedelta(days=30)

        result = await exam_analysis_service.get_organization_analyses(
            organization_name=request.organization_name,
            exam_type=request.exam_type,
            start_date=request.start_date,
            end_date=request.end_date,
            page=request.page,
            page_size=request.page_size,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/exam-analyses/without-result", tags=["exam-analyses"])
async def get_analyses_without_exam_result(
    request: AnalysesWithoutResultRequest,  # remova o campo 'token'
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """
    List exam analyses for an organization that do not have an exam_result yet.
    Authentication: Bearer token in Authorization header.
    """
    try:
        result = await exam_analysis_service.get_analyses_without_exam_result(
            organization_name=request.organization_name,
            page=request.page,
            page_size=request.page_size,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/exam-analyses/by-type", tags=["exam-analyses"])
async def get_analyses_by_exam_type(
    request: AnalysesByTypeRequest,  # remova o campo 'token'
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """
    List exam analyses filtered by exact exam type.
    Authentication: Bearer token in Authorization header.
    """
    try:
        result = await exam_analysis_service.get_analyses_by_exam_type(
            organization_name=request.organization_name,
            exam_type=request.exam_type,
            page=request.page,
            page_size=request.page_size,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/exam-analyses/organization/{organization_name}", tags=["exam-analyses"])
async def get_organization_analyses(
    organization_name: str = Path(...),
    query: OrganizationAnalysesQuery = Depends(),
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """List exam analyses for an organization with filters."""
    try:
        
        end_date = query.end_date or datetime.utcnow()
        start_date = query.start_date or (end_date - timedelta(days=30))

        result = await exam_analysis_service.get_organization_analyses(
            organization_name=organization_name,
            exam_type=query.exam_type,
            start_date=start_date,
            end_date=end_date,
            page=query.page,
            page_size=query.page_size,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/exam-analyses/without-result", tags=["exam-analyses"])
async def get_analyses_without_exam_result(
    organization_name: str = Query(...),
    query: AnalysesWithoutResultQuery = Depends(),
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """List exam analyses that do not have an exam_result yet."""
    try:
        result = await exam_analysis_service.get_analyses_without_exam_result(
            organization_name=organization_name,
            page=query.page,
            page_size=query.page_size,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/exam-analyses/by-type", tags=["exam-analyses"])
async def get_analyses_by_exam_type(
    organization_name: str = Query(...),
    query: AnalysesByTypeQuery = Depends(),
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """List exam analyses filtered by exact exam type."""
    try:
        result = await exam_analysis_service.get_analyses_by_exam_type(
            organization_name=organization_name,
            exam_type=query.exam_type,
            page=query.page,
            page_size=query.page_size,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/exam-analyses/statistics", tags=["exam-analyses"])
async def get_analysis_statistics(
    organization_name: str = Query(...),
    query: AnalysisStatisticsQuery = Depends(),
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """Return statistics about exam analyses for an organization."""
    try:
        stats = await exam_analysis_service.get_analysis_statistics(
            organization_name=organization_name,
            start_date=query.start_date,
            end_date=query.end_date,
        )
        return stats
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/audit/organization/{organization_name}", response_model=PaginatedAuditResponse, tags=["exam-audits"])
async def get_audit_by_organization(
    organization_name: str,
    query: AuditByOrganizationQuery = Depends(),
    token: str = Header(..., alias="Authorization")
):
    """
    Returns audit records filtered by organization.
    - **organization_name**: name of the organization (e.g., "Hospital São Paulo")
    - **start_date**: start date/time (optional)
    - **end_date**: end date/time (optional)
    - **action_type**: action type (INSERT, UPDATE, DELETE)
    - **page**: page number (default 1)
    - **page_size**: items per page (default 50)
    """
    await auth_service.validate_token(token)
    result = await exam_analysis_audit_service.get_audit_by_organization(
        organization_name=organization_name,
        start_date=query.start_date,
        end_date=query.end_date,
        action_type=query.action_type,
        page=query.page,
        page_size=query.page_size
    )
    return result


@app.get("/audit/user/{db_user}", response_model=List[ExamAnalysisAuditResponse], tags=["exam-audits"])
async def get_audit_by_user(
    db_user: str,
    query: AuditByUserQuery = Depends(),
    token: str = Header(..., alias="Authorization")
):
    """
    Returns audit records performed by a specific database user.
    - **db_user**: database username (e.g., "app_user")
    - **limit**: maximum number of records (default 100)
    - **offset**: pagination offset
    """
    await auth_service.validate_token(token)
    audits = await exam_analysis_audit_service.get_audit_by_user(
        db_user=db_user,
        limit=query.limit,
        offset=query.offset
    )
    return audits


@app.get("/audit/date-range", response_model=PaginatedAuditResponse, tags=["exam-audits"])
async def get_audit_by_date_range(
    query: AuditByDateRangeQuery = Depends(),
    token: str = Header(..., alias="Authorization")
):
    """
    Returns audit records within a required date range.
    - **start_date**: start date/time
    - **end_date**: end date/time
    - **page**: page number
    - **page_size**: items per page
    """
    await auth_service.validate_token(token)
    result = await exam_analysis_audit_service.get_audit_by_date_range(
        start_date=query.start_date,
        end_date=query.end_date,
        page=query.page,
        page_size=query.page_size
    )
    return result
# =============================================================================
# Rotas de Auditoria
# =============================================================================
@app.get("/audit/analysis/{analysis_id}", response_model=List[ExamAnalysisAuditResponse], tags=["exam-audits"])
async def get_audit_for_analysis(
    analysis_id: UUID,
    query: AuditForAnalysisQuery = Depends(),
    token: str = Header(..., alias="Authorization")
):
    """
    Retorna o histórico de auditoria para uma análise específica.
    - **analysis_id**: UUID da análise
    - **limit**: máximo de registros (padrão 100)
    - **offset**: deslocamento para paginação
    """
    await auth_service.validate_token(token)
    audits = await exam_analysis_audit_service.get_audit_for_analysis(
        analysis_id=analysis_id,
        limit=query.limit,
        offset=query.offset
    )
    return audits

# =============================================================================
# MONITORING ENDPOINTS (agora GET com token no header)
# =============================================================================

@app.get("/health", tags=["monitoring"])
async def health_check(
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """
    Health check endpoint.
    Authentication: Bearer token in Authorization header.
    """
    return {
        "status": "healthy",
        "service": "exam-microservice",
        "version": "1.0.2",
        "authenticated_client": token_data["client_id"],
    }

@app.get("/", tags=["monitoring"])
async def root(
    token_data: Dict[str, Any] = Depends(get_token_data_from_header)
):
    """
    Root endpoint with API information.
    Authentication: Bearer token in Authorization header.
    """
    return {
        "message": "Exam Microservice API",
        "version": "1.0.2",
        "docs": "/docs",
        "redoc": "/redoc",
        "authenticated_client": token_data["client_id"],
    }

# =============================================================================
# DOCUMENTATION ENDPOINTS (public, sem autenticação)
# =============================================================================

@app.get("/docs", include_in_schema=False)
async def get_docs():
    """Redirect to Swagger UI documentation."""
    return RedirectResponse(url="/docs")

@app.get("/redoc", include_in_schema=False)
async def get_redoc():
    """Redirect to ReDoc documentation."""
    return RedirectResponse(url="/redoc")