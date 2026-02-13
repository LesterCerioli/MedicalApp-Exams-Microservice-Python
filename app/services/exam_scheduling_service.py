from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from app.database import db

class ExamSchedulingService:
    
    def get_organization_id_by_name(self, organization_name: str) -> Optional[str]:
        """Gets organization ID by name (case-insensitive with debug)"""
        print(f"DEBUG: Searching for organization name: '{organization_name}'")
        return db.get_organization_id(organization_name)
    
    def get_organization_id_exact(self, organization_name: str) -> Optional[str]:
        """Exact match for organization name (including spaces)"""
        try:
            print(f"DEBUG: Exact search for: '{organization_name}'")
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id FROM public.organizations WHERE name = %s",
                        (organization_name,)
                    )
                    result = cursor.fetchone()
                    print(f"DEBUG: Exact match result: {result}")
                    return result['id'] if result else None
        except Exception as e:
            print(f"Error fetching organization (exact): {e}")
            return None
    
    def get_organization_id_trim(self, organization_name: str) -> Optional[str]:
        """Trimmed match for organization name"""
        try:
            print(f"DEBUG: Trimmed search for: '{organization_name}'")
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id FROM public.organizations WHERE TRIM(name) = TRIM(%s)",
                        (organization_name,)
                    )
                    result = cursor.fetchone()
                    print(f"DEBUG: Trimmed match result: {result}")
                    return result['id'] if result else None
        except Exception as e:
            print(f"Error fetching organization (trim): {e}")
            return None
    
    def get_all_organizations(self) -> List[Dict[str, Any]]:
        """Get all organizations for debugging"""
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id, name FROM public.organizations")
                    results = cursor.fetchall()
                    org_list = [dict(result) for result in results]
                    print(f"DEBUG: All organizations in DB: {org_list}")
                    return org_list
        except Exception as e:
            print(f"Error fetching organizations: {e}")
            return []
    
    def organization_exists(self, organization_name: str) -> bool:
        """Checks if organization exists"""
        return db.organization_exists(organization_name)
    
    def create_exam_scheduling(self, exam_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Creates a new exam scheduling with organization validation"""
        try:
            print(f"DEBUG: Creating exam scheduling for organization ID: {exam_data.get('organization_id')}")
            print(f"DEBUG: Exam details - Name: {exam_data.get('exam_name')}")
            
            # Verify organization exists
            org_id = exam_data.get('organization_id')
            if not org_id:
                print("DEBUG: Organization ID not provided")
                return None
            
            # Verify organization exists by checking if we can get its name
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT name FROM public.organizations WHERE id = %s",
                        (org_id,)
                    )
                    org_result = cursor.fetchone()
                    if not org_result:
                        print(f"DEBUG: Organization with ID {org_id} not found")
                        return None
            
            print(f"DEBUG: Organization verified successfully")
            
            result = db.create_exam_scheduling(exam_data)
            
            if result:
                print(f"DEBUG: Exam scheduling created successfully")
                # Sanitize data before returning
                return self._sanitize_exam_data(result)
            else:
                print("DEBUG: Exam scheduling creation failed")
            
            return result
            
        except Exception as e:
            print(f"ERROR creating exam scheduling: {e}")
            return None
    
    def get_exam_by_secure_identifier(self, exam_name: str, organization_name: str) -> Optional[Dict[str, Any]]:
        """Gets exam by secure identifier (exam name + organization name)"""
        try:
            print(f"DEBUG: Getting exam by secure identifier: '{exam_name}' for org: '{organization_name}'")
            
            org_id = self.get_organization_id_by_name(organization_name)
            if not org_id:
                print(f"DEBUG: Organization '{organization_name}' not found")
                return None
            
            result = db.get_exam_by_secure_identifier(exam_name, org_id)
            
            if result:
                return self._sanitize_exam_data(result)
            return None
            
        except Exception as e:
            print(f"Error getting exam by secure identifier: {e}")
            return None
    
    def update_exam_scheduling(self, exam_name: str, organization_name: str, 
                             update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Updates exam scheduling using secure identifiers"""
        try:
            print(f"DEBUG: Updating exam: '{exam_name}' for org: '{organization_name}'")
            
            org_id = self.get_organization_id_by_name(organization_name)
            if not org_id:
                print(f"DEBUG: Organization '{organization_name}' not found")
                return None
            
            result = db.update_exam_scheduling(exam_name, org_id, update_data)
            
            if result:
                return self._sanitize_exam_data(result)
            return None
            
        except Exception as e:
            print(f"Error updating exam scheduling: {e}")
            return None
    
    def delete_exam_scheduling(self, exam_name: str, organization_name: str) -> bool:
        """Deletes exam scheduling using secure identifiers"""
        try:
            print(f"DEBUG: Deleting exam: '{exam_name}' for org: '{organization_name}'")
            
            org_id = self.get_organization_id_by_name(organization_name)
            if not org_id:
                print(f"DEBUG: Organization '{organization_name}' not found")
                return False
            
            return db.delete_exam_scheduling(exam_name, org_id)
            
        except Exception as e:
            print(f"Error deleting exam scheduling: {e}")
            return False
    
    def list_exams_by_organization(self, organization_name: str, page: int = 1, 
                                 page_size: int = 10, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists exams for an organization with secure data"""
        try:
            print(f"DEBUG: Listing exams for org: '{organization_name}', page: {page}, status: {status}")
            
            org_id = self.get_organization_id_by_name(organization_name)
            if not org_id:
                print(f"DEBUG: Organization '{organization_name}' not found")
                return []
            
            results = db.list_exams_by_organization(org_id, page, page_size, status)
            
            if results:
                return [self._sanitize_exam_data(result) for result in results]
            return []
            
        except Exception as e:
            print(f"Error listing exams: {e}")
            return []
    
    def get_upcoming_exams_secure(self, organization_name: str, hours_ahead: int = 24) -> List[Dict[str, Any]]:
        """Gets upcoming exams with secure data"""
        try:
            print(f"DEBUG: Getting upcoming exams for org: '{organization_name}', hours: {hours_ahead}")
            
            org_id = self.get_organization_id_by_name(organization_name)
            if not org_id:
                print(f"DEBUG: Organization '{organization_name}' not found")
                return []
            
            results = db.get_upcoming_exams(org_id, hours_ahead)
            
            if results:
                return [self._sanitize_exam_data(result) for result in results]
            return []
            
        except Exception as e:
            print(f"Error getting upcoming exams: {e}")
            return []
    
    def get_exam_statistics(self, organization_name: str) -> Dict[str, Any]:
        """Gets exam statistics for an organization"""
        try:
            print(f"DEBUG: Getting statistics for org: '{organization_name}'")
            
            org_id = self.get_organization_id_by_name(organization_name)
            if not org_id:
                print(f"DEBUG: Organization '{organization_name}' not found")
                return {}
            
            return db.get_exam_statistics(org_id) or {}
            
        except Exception as e:
            print(f"Error getting exam statistics: {e}")
            return {}
    
    def verify_exam_access(self, exam_name: str, organization_name: str, 
                          patient_name: Optional[str] = None) -> bool:
        """Verify if user has access to this exam data"""
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = """
                        SELECT es.id, p.name as patient_name
                        FROM public.exam_scheduling es
                        LEFT JOIN patients p ON es.patient_id = p.id
                        WHERE es.exam_name = %s AND es.organization_id = %s AND es.deleted_at IS NULL
                    """
                    org_id = self.get_organization_id_by_name(organization_name)
                    if not org_id:
                        return False
                    
                    cursor.execute(query, (exam_name, org_id))
                    result = cursor.fetchone()
                    
                    if not result:
                        return False
                    
                    # Additional patient name verification if provided
                    if patient_name and result['patient_name']:
                        return result['patient_name'].lower() == patient_name.lower()
                    
                    return True
        except Exception as e:
            print(f"Error verifying exam access: {e}")
            return False
    
    def _sanitize_exam_data(self, exam_data: Dict[str, Any]) -> Dict[str, Any]:
        """Removes sensitive internal IDs from response data"""
        sanitized = exam_data.copy()
        
        # Remove internal UUIDs that shouldn't be exposed
        sensitive_fields = ['id', 'patient_id', 'organization_id', 'patient_internal_id']
        for field in sensitive_fields:
            sanitized.pop(field, None)
        
        # Add secure identifier (exam name + organization combo)
        sanitized['secure_identifier'] = exam_data.get('exam_name', '')
        
        return sanitized

# Global service instance
exam_scheduling_service = ExamSchedulingService()