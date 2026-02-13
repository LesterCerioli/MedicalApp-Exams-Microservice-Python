from datetime import date, datetime
from enum import Enum
from typing import Dict, Optional, List, Any, Union
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, ValidationInfo


# =============================================================================
# Auth Schemas
# =============================================================================

class AuthTokenRequest(BaseModel):
    client_id: str
    client_secret: str


class TokenValidationRequest(BaseModel):
    token: str


class TokenValidationResponse(BaseModel):
    valid: bool
    message: str


class AuthenticatedRequest(BaseModel):
    token: str


# =============================================================================
# Health / Root Schemas
# =============================================================================

class HealthCheckRequest(AuthenticatedRequest):
    pass


class RootRequest(AuthenticatedRequest):
    pass


# =============================================================================
# Exam Service - Request Models
# =============================================================================

class CreateExamRequest(AuthenticatedRequest):
    organization_name: str
    exam_type: str
    patient_name: str
    status: str = "pending"
    requested_at: Optional[date] = None
    notes: Optional[str] = None

    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid = ["pending", "scheduled", "completed", "cancelled", "in_progress"]
        if v not in valid:
            raise ValueError(f"Status must be one of: {valid}")
        return v

    @field_validator('exam_type')
    @classmethod
    def validate_exam_type(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Exam type cannot be empty")
        return v.strip()


class GetExamRequest(AuthenticatedRequest):
    exam_id: UUID


class UpdateExamRequest(AuthenticatedRequest):
    exam_id: UUID
    exam_type: Optional[str] = None
    status: Optional[str] = None
    requested_at: Optional[date] = None
    notes: Optional[str] = None
    patient_name: Optional[str] = None  # CORRIGIDO: era 'str' sem Optional, agora Optional

    @field_validator('status')
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid = ["pending", "scheduled", "completed", "cancelled", "in_progress"]
            if v not in valid:
                raise ValueError(f"Status must be one of: {valid}")
        return v

    @field_validator('exam_type')
    @classmethod
    def validate_exam_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Exam type cannot be empty")
        return v.strip() if v else v


class DeleteExamRequest(AuthenticatedRequest):
    exam_id: UUID


class RestoreExamRequest(AuthenticatedRequest):
    exam_id: UUID


class OrganizationExamsRequest(AuthenticatedRequest):
    organization_name: str
    patient_name: Optional[str] = None  # CORRIGIDO: era obrigatório, agora opcional
    status: Optional[str] = None
    exam_type: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    page: int = 1
    page_size: int = 50

    @field_validator('page')
    @classmethod
    def validate_page(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page must be >= 1")
        return v

    @field_validator('page_size')
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page size must be >= 1")
        if v > 100:
            raise ValueError("Page size cannot exceed 100")
        return v


class PatientExamsRequest(AuthenticatedRequest):
    patient_name: str  # era obrigatório e estava faltando
    organization_name: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    page: int = 1
    page_size: int = 50

    @field_validator('page')
    @classmethod
    def validate_page(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page must be >= 1")
        return v

    @field_validator('page_size')
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page size must be >= 1")
        if v > 100:
            raise ValueError("Page size cannot exceed 100")
        return v


class UpdateExamStatusRequest(AuthenticatedRequest):
    exam_id: UUID
    status: str

    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid = ["pending", "scheduled", "completed", "cancelled", "in_progress"]
        if v not in valid:
            raise ValueError(f"Status must be one of: {valid}")
        return v


class BulkUpdateStatusRequest(AuthenticatedRequest):
    exam_ids: List[UUID]
    status: str

    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid = ["pending", "scheduled", "completed", "cancelled", "in_progress"]
        if v not in valid:
            raise ValueError(f"Status must be one of: {valid}")
        return v

    @field_validator('exam_ids')
    @classmethod
    def validate_exam_ids(cls, v: List[UUID]) -> List[UUID]:
        if not v:
            raise ValueError("exam_ids cannot be empty")
        return v


class ExamCountsRequest(AuthenticatedRequest):
    organization_name: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class UpcomingExamsRequest(AuthenticatedRequest):
    organization_name: str
    from_date: date
    to_date: date
    page: int = 1
    page_size: int = 50

    @field_validator('page')
    @classmethod
    def validate_page(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page must be >= 1")
        return v

    @field_validator('page_size')
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page size must be >= 1")
        if v > 100:
            raise ValueError("Page size cannot exceed 100")
        return v

    @field_validator('to_date')
    @classmethod
    def validate_date_range(cls, v: date, info: ValidationInfo) -> date:
        from_date = info.data.get('from_date')
        if from_date and v < from_date:
            raise ValueError("to_date must be >= from_date")
        return v


class ExamsWithoutPatientRequest(AuthenticatedRequest):
    organization_name: str


# =============================================================================
# Exam Service - Response Models
# =============================================================================

class ExamResponse(BaseModel):
    id: UUID
    organization_id: UUID
    patient_id: Optional[UUID] = None
    exam_type: str
    status: str
    requested_at: Optional[date] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaginatedExamsResponse(BaseModel):
    exams: List[ExamResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int


# =============================================================================
# Exam Analysis Service - Request Models
# =============================================================================

class CreateExamAnalysisRequest(AuthenticatedRequest):
    organization_name: str
    exam_type: str
    original_results: Union[Dict[str, Any], List[Any]]
    exam_date: Optional[datetime] = None
    exam_result: Optional[Dict[str, Any]] = None
    observations: Optional[Dict[str, Any]] = None

    @field_validator('exam_type')
    @classmethod
    def validate_exam_type(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Exam type cannot be empty")
        return v.strip()

    @field_validator('original_results')
    @classmethod
    def validate_original_results(cls, v: Any) -> Any:
        if v is None:
            raise ValueError("Original results cannot be empty")
        return v


class GetExamAnalysisRequest(AuthenticatedRequest):
    analysis_id: UUID


class UpdateExamAnalysisRequest(AuthenticatedRequest):
    analysis_id: UUID
    exam_type: Optional[str] = None
    exam_date: Optional[datetime] = None
    original_results: Optional[Union[Dict[str, Any], List[Any]]] = None
    exam_result: Optional[Dict[str, Any]] = None
    observations: Optional[Dict[str, Any]] = None

    @field_validator('exam_type')
    @classmethod
    def validate_exam_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Exam type cannot be empty")
        return v.strip() if v else v


class DeleteExamAnalysisRequest(AuthenticatedRequest):
    analysis_id: UUID


class OrganizationAnalysesRequest(AuthenticatedRequest):
    organization_name: str
    exam_type: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    page: int = 1
    page_size: int = 50

    @field_validator('page')
    @classmethod
    def validate_page(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page must be >= 1")
        return v

    @field_validator('page_size')
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page size must be >= 1")
        if v > 100:
            raise ValueError("Page size cannot exceed 100")
        return v

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v: Optional[date], info: ValidationInfo) -> Optional[date]:
        if v is not None and info.data.get('start_date') and v < info.data['start_date']:
            raise ValueError("end_date must be >= start_date")
        return v


class AnalysesWithoutResultRequest(AuthenticatedRequest):
    organization_name: str
    page: int = 1
    page_size: int = 50

    @field_validator('page')
    @classmethod
    def validate_page(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page must be >= 1")
        return v

    @field_validator('page_size')
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page size must be >= 1")
        if v > 100:
            raise ValueError("Page size cannot exceed 100")
        return v


class AnalysesByTypeRequest(AuthenticatedRequest):
    organization_name: str
    exam_type: str
    page: int = 1
    page_size: int = 50

    @field_validator('page')
    @classmethod
    def validate_page(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page must be >= 1")
        return v

    @field_validator('page_size')
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page size must be >= 1")
        if v > 100:
            raise ValueError("Page size cannot exceed 100")
        return v


class AnalysisStatisticsRequest(AuthenticatedRequest):
    organization_name: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v: Optional[date], info: ValidationInfo) -> Optional[date]:
        if v is not None and info.data.get('start_date') and v < info.data['start_date']:
            raise ValueError("end_date must be >= start_date")
        return v


# =============================================================================
# Exam Analysis Service - Response Models
# =============================================================================

class ExamAnalysisResponse(BaseModel):
    id: UUID
    organizations_id: UUID
    exam_type: str
    exam_date: Optional[datetime] = None
    original_results: Optional[Union[Dict[str, Any], List[Any]]] = None
    analyzed_results: Optional[Dict[str, Any]] = None
    observations: Optional[Dict[str, Any]] = None
    analysis_date: Optional[datetime] = None
    exam_result: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaginatedAnalysesResponse(BaseModel):
    analyses: List[ExamAnalysisResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class AnalysisStatisticsResponse(BaseModel):
    total_analyses: int
    analyses_with_result: int
    analyses_without_result: int
    top_exam_types: List[Dict[str, Any]]


# =============================================================================
# NOVOS SCHEMAS PARA OS ENDPOINTS REFATORADOS (SEM CAMPO 'token')
# =============================================================================



class UpdateExamBody(BaseModel):
    """Corpo para PATCH /exams/{exam_id} (atualização parcial)"""
    exam_type: Optional[str] = None
    status: Optional[str] = None
    requested_at: Optional[date] = None
    notes: Optional[str] = None
    patient_name: Optional[str] = None

    @field_validator('status')
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid = ["pending", "scheduled", "completed", "cancelled", "in_progress"]
            if v not in valid:
                raise ValueError(f"Status must be one of: {valid}")
        return v

    @field_validator('exam_type')
    @classmethod
    def validate_exam_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Exam type cannot be empty")
        return v.strip() if v else v


class UpdateExamStatusBody(BaseModel):
    """Corpo para PATCH /exams/{exam_id}/status"""
    status: str

    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid = ["pending", "scheduled", "completed", "cancelled", "in_progress"]
        if v not in valid:
            raise ValueError(f"Status must be one of: {valid}")
        return v


class BulkUpdateStatusBody(BaseModel):
    """Corpo para POST /exams/bulk-status (sem token)"""
    exam_ids: List[UUID]
    status: str

    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid = ["pending", "scheduled", "completed", "cancelled", "in_progress"]
        if v not in valid:
            raise ValueError(f"Status must be one of: {valid}")
        return v

    @field_validator('exam_ids')
    @classmethod
    def validate_exam_ids(cls, v: List[UUID]) -> List[UUID]:
        if not v:
            raise ValueError("exam_ids cannot be empty")
        return v




class OrganizationExamsQuery(BaseModel):
    """Query parameters para GET /exams/organization/{organization_name}"""
    patient_name: Optional[str] = None
    status: Optional[str] = None
    exam_type: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    page: int = 1
    page_size: int = 50

    @field_validator('page')
    @classmethod
    def validate_page(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page must be >= 1")
        return v

    @field_validator('page_size')
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page size must be >= 1")
        if v > 100:
            raise ValueError("Page size cannot exceed 100")
        return v


class PatientExamsQuery(BaseModel):
    """Query parameters para GET /exams/patient"""
    patient_name: str
    organization_name: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    page: int = 1
    page_size: int = 50

    @field_validator('page')
    @classmethod
    def validate_page(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page must be >= 1")
        return v

    @field_validator('page_size')
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page size must be >= 1")
        if v > 100:
            raise ValueError("Page size cannot exceed 100")
        return v


class ExamCountsQuery(BaseModel):
    """Query parameters para GET /exams/counts-by-status"""
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class UpcomingExamsQuery(BaseModel):
    """Query parameters para GET /exams/upcoming"""
    from_date: date
    to_date: date
    page: int = 1
    page_size: int = 50

    @field_validator('page')
    @classmethod
    def validate_page(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page must be >= 1")
        return v

    @field_validator('page_size')
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page size must be >= 1")
        if v > 100:
            raise ValueError("Page size cannot exceed 100")
        return v

    @field_validator('to_date')
    @classmethod
    def validate_date_range(cls, v: date, info: ValidationInfo) -> date:
        from_date = info.data.get('from_date')
        if from_date and v < from_date:
            raise ValueError("to_date must be >= from_date")
        return v


class ExamsWithoutPatientQuery(BaseModel):
    """Query parameters para GET /exams/without-patient (vazio, usa apenas organization_name)"""
    pass



class UpdateExamAnalysisBody(BaseModel):
    """Corpo para PATCH /exam-analyses/{analysis_id}"""
    exam_type: Optional[str] = None
    exam_date: Optional[datetime] = None
    original_results: Optional[Union[Dict[str, Any], List[Any]]] = None
    exam_result: Optional[Dict[str, Any]] = None
    observations: Optional[Dict[str, Any]] = None

    @field_validator('exam_type')
    @classmethod
    def validate_exam_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Exam type cannot be empty")
        return v.strip() if v else v



class OrganizationAnalysesQuery(BaseModel):
    """Query parameters para GET /exam-analyses/organization/{organization_name}"""
    exam_type: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    page: int = 1
    page_size: int = 50

    @field_validator('page')
    @classmethod
    def validate_page(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page must be >= 1")
        return v

    @field_validator('page_size')
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page size must be >= 1")
        if v > 100:
            raise ValueError("Page size cannot exceed 100")
        return v

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v: Optional[date], info: ValidationInfo) -> Optional[date]:
        if v is not None and info.data.get('start_date') and v < info.data['start_date']:
            raise ValueError("end_date must be >= start_date")
        return v


class AnalysesWithoutResultQuery(BaseModel):
    """Query parameters para GET /exam-analyses/without-result"""
    page: int = 1
    page_size: int = 50

    @field_validator('page')
    @classmethod
    def validate_page(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page must be >= 1")
        return v

    @field_validator('page_size')
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page size must be >= 1")
        if v > 100:
            raise ValueError("Page size cannot exceed 100")
        return v


class AnalysesByTypeQuery(BaseModel):
    """Query parameters para GET /exam-analyses/by-type"""
    exam_type: str
    page: int = 1
    page_size: int = 50

    @field_validator('page')
    @classmethod
    def validate_page(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page must be >= 1")
        return v

    @field_validator('page_size')
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page size must be >= 1")
        if v > 100:
            raise ValueError("Page size cannot exceed 100")
        return v


class AnalysisStatisticsQuery(BaseModel):
    """Query parameters para GET /exam-analyses/statistics"""
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v: Optional[date], info: ValidationInfo) -> Optional[date]:
        if v is not None and info.data.get('start_date') and v < info.data['start_date']:
            raise ValueError("end_date must be >= start_date")
        return v
    
    
# =============================================================================
# Exam Analysis Audit Service - Schemas
# =============================================================================

class ExamAnalysisAuditResponse(BaseModel):
    """Schema para um registro de auditoria de análise de exame"""
    id: UUID
    exam_analyses_id: UUID
    action_type: str  # INSERT, UPDATE, DELETE
    old_data: Optional[Dict[str, Any]] = None
    new_data: Optional[Dict[str, Any]] = None
    changed_fields: Optional[List[List[str]]] = None  # array de [campo, valor_antigo, valor_novo]
    application_name: Optional[str] = None
    db_user: Optional[str] = None
    changed_at: datetime
    # Campos adicionais quando há JOIN com exam_analyses (opcionais)
    exam_type: Optional[str] = None
    organizations_id: Optional[UUID] = None

    class Config:
        from_attributes = True


class PaginatedAuditResponse(BaseModel):
    """Resposta paginada para listagens de auditoria"""
    audits: List[ExamAnalysisAuditResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int


# ----- Query Parameters para endpoints GET -----

class AuditForAnalysisQuery(BaseModel):
    """Query parameters para GET /audit/analysis/{analysis_id}"""
    limit: int = Field(100, ge=1, le=1000, description="Número máximo de registros")
    offset: int = Field(0, ge=0, description="Deslocamento para paginação")


class AuditByOrganizationQuery(BaseModel):
    """Query parameters para GET /audit/organization/{organization_name}"""
    start_date: Optional[datetime] = Field(None, description="Data/hora inicial (inclusive)")
    end_date: Optional[datetime] = Field(None, description="Data/hora final (inclusive)")
    action_type: Optional[str] = Field(None, description="Filtrar por tipo de ação (INSERT, UPDATE, DELETE)")
    page: int = Field(1, ge=1, description="Número da página")
    page_size: int = Field(50, ge=1, le=100, description="Itens por página")

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v: Optional[datetime], info: ValidationInfo) -> Optional[datetime]:
        if v is not None and info.data.get('start_date') and v < info.data['start_date']:
            raise ValueError("end_date must be >= start_date")
        return v


class AuditByUserQuery(BaseModel):
    """Query parameters para GET /audit/user/{db_user}"""
    limit: int = Field(100, ge=1, le=1000, description="Número máximo de registros")
    offset: int = Field(0, ge=0, description="Deslocamento para paginação")


class AuditByDateRangeQuery(BaseModel):
    """Query parameters para GET /audit/date-range"""
    start_date: datetime = Field(..., description="Data/hora inicial (obrigatório)")
    end_date: datetime = Field(..., description="Data/hora final (obrigatório)")
    page: int = Field(1, ge=1, description="Número da página")
    page_size: int = Field(50, ge=1, le=100, description="Itens por página")

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v: datetime, info: ValidationInfo) -> datetime:
        if v < info.data.get('start_date'):
            raise ValueError("end_date must be >= start_date")
        return v