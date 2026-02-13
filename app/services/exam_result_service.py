from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.database import db
from app.services.exam_scheduling_service import exam_scheduling_service
from app.schemas import (
    ExamSchedulingCreate,
    ExamSchedulingUpdate,
    ExamSchedulingResponse,
    ExamStatisticsResponse,
    SecureAccessRequest,
    ExamListRequest
)

# Initialize FastAPI app
app = FastAPI(
    title="Medical Exam Scheduling API",
    description="API for managing medical exam scheduling with secure data handling",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize database connections on startup"""
    print("INFO: Medical Exam Scheduling API starting up...")
    # Database connection is handled by the context manager, no need to initialize here

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    print("INFO: Medical Exam Scheduling API shutting down...")

# Health check endpoint
@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
        
        return {
            "status": "healthy",
            "service": "exam-scheduling-api",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}"
        )

# Root endpoint
@app.get("/", status_code=status.HTTP_200_OK)
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Medical Exam API",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "create_exam": "POST /exams/",
            "get_exam": "GET /exams/{secure_identifier}",
            "update_exam": "PUT /exams/{secure_identifier}",
            "delete_exam": "DELETE /exams/{secure_identifier}",
            "list_exams": "GET /exams/",
            "upcoming_exams": "GET /exams/upcoming/",
            "statistics": "GET /exams/statistics/"
        }
    }

# Exam Scheduling Endpoints

@app.post("/exams/", 
          response_model=ExamSchedulingResponse, 
          status_code=status.HTTP_201_CREATED,
          summary="Create a new exam scheduling",
          description="Create a new exam scheduling record with secure data handling")
async def create_exam_scheduling(exam_data: ExamSchedulingCreate):
    """
    Create a new exam scheduling.
    
    - **organization_id**: Internal UUID of the organization (not exposed in response)
    - **patient_id**: Internal UUID of the patient (optional, not exposed in response)
    - **exam_name**: Name of the exam (used as secure identifier)
    - **scheduled_date**: Date and time when the exam is scheduled
    - **status**: Current status of the exam (default: scheduled)
    """
    try:
        print(f"DEBUG: Creating exam scheduling for organization: {exam_data.organization_id}")
        
        # Convert Pydantic model to dict for service processing
        exam_dict = exam_data.dict()
        
        result = exam_scheduling_service.create_exam_scheduling(exam_dict)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create exam scheduling. Organization may not exist or exam name might be duplicate."
            )
        
        return ExamSchedulingResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"ERROR: Unexpected error creating exam: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while creating exam scheduling"
        )

@app.get("/exams/{exam_name}", 
         response_model=ExamSchedulingResponse,
         summary="Get exam by secure identifier",
         description="Retrieve exam scheduling details using exam name and organization name as secure identifiers")
async def get_exam_scheduling(
    exam_name: str,
    organization_name: str = Query(..., description="Organization name for secure access"),
    patient_name: Optional[str] = Query(None, description="Optional patient name for additional verification")
):
    """
    Get exam scheduling details by secure identifier.
    
    - **exam_name**: Name of the exam (acts as secure identifier)
    - **organization_name**: Name of the organization (required for access control)
    - **patient_name**: Optional patient name for additional verification
    """
    try:
        print(f"DEBUG: Fetching exam: '{exam_name}' for organization: '{organization_name}'")
        
        # Verify access first
        if not exam_scheduling_service.verify_exam_access(exam_name, organization_name, patient_name):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam not found or access denied"
            )
        
        exam = exam_scheduling_service.get_exam_by_secure_identifier(exam_name, organization_name)
        
        if not exam:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam scheduling not found"
            )
        
        return ExamSchedulingResponse(**exam)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Unexpected error fetching exam: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while fetching exam scheduling"
        )

@app.put("/exams/{exam_name}",
         response_model=ExamSchedulingResponse,
         summary="Update exam scheduling",
         description="Update exam scheduling details using secure identifiers")
async def update_exam_scheduling(
    exam_name: str,
    update_data: ExamSchedulingUpdate,
    organization_name: str = Query(..., description="Organization name for secure access")
):
    """
    Update exam scheduling details.
    
    - **exam_name**: Name of the exam to update
    - **organization_name**: Organization name for verification
    - **update_data**: Fields to update (only provided fields will be updated)
    """
    try:
        print(f"DEBUG: Updating exam: '{exam_name}' for organization: '{organization_name}'")
        
        # Convert Pydantic model to dict
        update_dict = update_data.dict(exclude_unset=True)
        
        result = exam_scheduling_service.update_exam_scheduling(
            exam_name, 
            organization_name, 
            update_dict
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam scheduling not found or update failed"
            )
        
        return ExamSchedulingResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Unexpected error updating exam: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while updating exam scheduling"
        )

@app.delete("/exams/{exam_name}",
            status_code=status.HTTP_200_OK,
            summary="Delete exam scheduling",
            description="Soft delete exam scheduling using secure identifiers")
async def delete_exam_scheduling(
    exam_name: str,
    organization_name: str = Query(..., description="Organization name for secure access")
):
    """
    Delete exam scheduling (soft delete).
    
    - **exam_name**: Name of the exam to delete
    - **organization_name**: Organization name for verification
    """
    try:
        print(f"DEBUG: Deleting exam: '{exam_name}' for organization: '{organization_name}'")
        
        success = exam_scheduling_service.delete_exam_scheduling(exam_name, organization_name)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam scheduling not found or already deleted"
            )
        
        return {
            "message": "Exam scheduling deleted successfully",
            "exam_name": exam_name,
            "organization": organization_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Unexpected error deleting exam: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while deleting exam scheduling"
        )

@app.get("/exams/",
         response_model=List[ExamSchedulingResponse],
         summary="List exams by organization",
         description="List all exam schedules for an organization with pagination")
async def list_exam_schedules(
    organization_name: str = Query(..., description="Organization name to filter exams"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    status: Optional[str] = Query(None, description="Filter by exam status")
):
    """
    List exam schedules for an organization.
    
    - **organization_name**: Name of the organization
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 10, max: 100)
    - **status**: Filter by status (scheduled, in-progress, completed, cancelled, postponed)
    """
    try:
        print(f"DEBUG: Listing exams for organization: '{organization_name}', page: {page}, status: {status}")
        
        exams = exam_scheduling_service.list_exams_by_organization(
            organization_name, page, page_size, status
        )
        
        return [ExamSchedulingResponse(**exam) for exam in exams]
        
    except Exception as e:
        print(f"ERROR: Unexpected error listing exams: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while listing exam schedules"
        )

@app.get("/exams/upcoming/",
         response_model=List[ExamSchedulingResponse],
         summary="Get upcoming exams",
         description="Get exams scheduled within the next specified hours")
async def get_upcoming_exams(
    organization_name: str = Query(..., description="Organization name"),
    hours_ahead: int = Query(24, ge=1, le=168, description="Hours ahead to look for exams (1-168)")
):
    """
    Get upcoming exams within the next specified hours.
    
    - **organization_name**: Name of the organization
    - **hours_ahead**: Number of hours to look ahead (default: 24, max: 168 (1 week))
    """
    try:
        print(f"DEBUG: Getting upcoming exams for organization: '{organization_name}', hours: {hours_ahead}")
        
        exams = exam_scheduling_service.get_upcoming_exams_secure(organization_name, hours_ahead)
        
        return [ExamSchedulingResponse(**exam) for exam in exams]
        
    except Exception as e:
        print(f"ERROR: Unexpected error fetching upcoming exams: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while fetching upcoming exams"
        )

@app.get("/exams/statistics/",
         response_model=ExamStatisticsResponse,
         summary="Get exam statistics",
         description="Get statistics for exams in an organization")
async def get_exam_statistics(
    organization_name: str = Query(..., description="Organization name")
):
    """
    Get exam statistics for an organization.
    
    - **organization_name**: Name of the organization
    """
    try:
        print(f"DEBUG: Getting statistics for organization: '{organization_name}'")
        
        stats = exam_scheduling_service.get_exam_statistics(organization_name)
        
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found or no exam data available"
            )
        
        return ExamStatisticsResponse(**stats)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Unexpected error fetching statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while fetching exam statistics"
        )

@app.post("/exams/verify-access/",
          status_code=status.HTTP_200_OK,
          summary="Verify exam access",
          description="Verify if the current user has access to a specific exam")
async def verify_exam_access(access_request: SecureAccessRequest):
    """
    Verify access to an exam scheduling record.
    
    - **exam_name**: Name of the exam
    - **organization_name**: Name of the organization
    """
    try:
        print(f"DEBUG: Verifying access for exam: '{access_request.exam_name}' in org: '{access_request.organization_name}'")
        
        has_access = exam_scheduling_service.verify_exam_access(
            access_request.exam_name,
            access_request.organization_name
        )
        
        return {
            "has_access": has_access,
            "exam_name": access_request.exam_name,
            "organization": access_request.organization_name
        }
        
    except Exception as e:
        print(f"ERROR: Unexpected error verifying access: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while verifying access"
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Global HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Global exception handler"""
    print(f"ERROR: Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  
        log_level="info"
    )