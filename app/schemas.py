from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

class ExamSchedulingCreate(BaseModel):
    organization_id: UUID  
    patient_id: Optional[UUID] = None  
    exam_name: str = Field(..., max_length=200)
    exam_description: Optional[str] = None
    scheduled_date: datetime
    scheduled_end_date: Optional[datetime] = None
    exam_duration_minutes: Optional[int] = Field(None, ge=1)
    status: str = Field(default="scheduled")
    max_participants: Optional[int] = Field(None, ge=1)
    location: Optional[str] = Field(None, max_length=200)
    instructions: Optional[str] = None

    @validator('scheduled_date')
    def scheduled_date_must_be_future(cls, v):
        if v < datetime.now():
            raise ValueError('Scheduled date must be in the future')
        return v

    @validator('status')
    def validate_status(cls, v):
        valid_statuses = {'scheduled', 'in-progress', 'completed', 'cancelled', 'postponed'}
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {valid_statuses}')
        return v

class ExamSchedulingUpdate(BaseModel):
    exam_name: Optional[str] = Field(None, max_length=200)
    exam_description: Optional[str] = None
    scheduled_date: Optional[datetime] = None
    scheduled_end_date: Optional[datetime] = None
    exam_duration_minutes: Optional[int] = Field(None, ge=1)
    status: Optional[str] = None
    max_participants: Optional[int] = Field(None, ge=1)
    location: Optional[str] = Field(None, max_length=200)
    instructions: Optional[str] = None

class ExamSchedulingResponse(BaseModel):
    
    secure_identifier: str
    exam_name: str
    exam_description: Optional[str] = None
    scheduled_date: datetime
    scheduled_end_date: Optional[datetime] = None
    exam_duration_minutes: Optional[int] = None
    status: str
    max_participants: Optional[int] = None
    location: Optional[str] = None
    instructions: Optional[str] = None
    organization_name: Optional[str] = None
    patient_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ExamStatisticsResponse(BaseModel):
    total_exams: int
    upcoming_exams: int
    by_status: Dict[str, int]

class SecureAccessRequest(BaseModel):
    exam_name: str
    organization_name: str

class ExamListRequest(BaseModel):
    organization_name: str
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)
    status: Optional[str] = None