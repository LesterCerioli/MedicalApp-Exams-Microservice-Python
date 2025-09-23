import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict, Any, List
from app.config import config
import contextlib
import uuid

class Database:  # ← FIXED: Changed from 'Dataase' to 'Database'
    def __init__(self):
        self.connection_string = config.DATABASE_URL
    
    @contextlib.contextmanager
    def get_connection(self):
        """Context manager to handle database connections"""
        conn = psycopg2.connect(
            self.connection_string,
            cursor_factory=RealDictCursor
        )
        try:
            yield conn
        finally:
            conn.close()
    
    def init_db(self):
        """Database initialization - tables already exist"""
        print("INFO: Database tables already exist, skipping table creation")
    
    def organization_exists(self, organization_name: str) -> bool:
        """Checks if an organization exists by name (case-insensitive)"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT EXISTS (SELECT 1 FROM public.organizations WHERE LOWER(TRIM(name)) = LOWER(TRIM(%s))) AS exists",
                        (organization_name,)
                    )
                    result = cursor.fetchone()
                    return result['exists']
        except Exception as e:
            print(f"Error checking organization: {e}")
            return False
    
    def get_organization_id(self, organization_name: str) -> Optional[str]:
        """Gets the organization ID by name (case-insensitive with debug)"""
        try:
            print(f"DEBUG: Searching for organization: '{organization_name}'")
            
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id, name FROM public.organizations WHERE LOWER(TRIM(name)) = LOWER(TRIM(%s))",
                        (organization_name,)
                    )
                    result = cursor.fetchone()
                    
                    if result:
                        print(f"DEBUG: Organization found - ID: {result['id']}, Name: '{result['name']}'")
                        return result['id']
                    else:
                        cursor.execute("SELECT id, name FROM public.organizations")
                        all_orgs = cursor.fetchall()
                        print(f"DEBUG: Available organizations: {[dict(org) for org in all_orgs]}")
                        return None
                        
        except Exception as e:
            print(f"Error fetching organization: {e}")
            return None

    # Exam Scheduling Methods
    def create_exam_scheduling(self, exam_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Creates a new exam scheduling in the database"""
        try:
            print(f"DEBUG: Creating exam scheduling with data: {exam_data}")
            
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        INSERT INTO public.exam_scheduling (
                            organization_id, patient_id, exam_name, exam_description,
                            scheduled_date, scheduled_end_date, exam_duration_minutes,
                            status, max_participants, location, instructions
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING *
                    ''', (
                        exam_data['organization_id'],
                        exam_data.get('patient_id'),
                        exam_data['exam_name'],
                        exam_data.get('exam_description'),
                        exam_data['scheduled_date'],
                        exam_data.get('scheduled_end_date'),
                        exam_data.get('exam_duration_minutes'),
                        exam_data.get('status', 'scheduled'),
                        exam_data.get('max_participants'),
                        exam_data.get('location'),
                        exam_data.get('instructions')
                    ))
                    
                    result = cursor.fetchone()
                    conn.commit()
                    
                    if result:
                        print(f"DEBUG: Exam scheduling created successfully: {dict(result)}")
                        return dict(result)
                    else:
                        print("DEBUG: Exam scheduling creation failed - no result returned")
                        return None
                    
        except psycopg2.IntegrityError as e:
            print(f"Integrity error creating exam scheduling: {e}")
            return None
        except Exception as e:
            print(f"Error creating exam scheduling: {e}")
            return None
    
    def get_exam_by_secure_identifier(self, exam_name: str, organization_id: str) -> Optional[Dict[str, Any]]:
        """Finds exam by name and organization_id (secure identifier)"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT es.*, o.name as organization_name, p.name as patient_name
                        FROM public.exam_scheduling es
                        LEFT JOIN public.organizations o ON es.organization_id = o.id
                        LEFT JOIN public.patients p ON es.patient_id = p.id
                        WHERE es.exam_name = %s AND es.organization_id = %s AND es.deleted_at IS NULL
                    ''', (exam_name, organization_id))
                    
                    result = cursor.fetchone()
                    return dict(result) if result else None
                    
        except Exception as e:
            print(f"Error fetching exam by secure identifier: {e}")
            return None
    
    def update_exam_scheduling(self, exam_name: str, organization_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Updates exam scheduling using secure identifier"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Build dynamic update query
                    set_fields = []
                    values = []
                    
                    for field, value in update_data.items():
                        if value is not None:
                            set_fields.append(f"{field} = %s")
                            values.append(value)
                    
                    if not set_fields:
                        return self.get_exam_by_secure_identifier(exam_name, organization_id)
                    
                    set_clause = ", ".join(set_fields)
                    values.extend([exam_name, organization_id])
                    
                    query = f'''
                        UPDATE public.exam_scheduling 
                        SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                        WHERE exam_name = %s AND organization_id = %s AND deleted_at IS NULL
                        RETURNING *
                    '''
                    
                    cursor.execute(query, values)
                    result = cursor.fetchone()
                    conn.commit()
                    
                    if result:
                        return dict(result)
                    return None
                    
        except Exception as e:
            print(f"Error updating exam scheduling: {e}")
            return None
    
    def delete_exam_scheduling(self, exam_name: str, organization_id: str) -> bool:
        """Soft deletes exam scheduling using secure identifier"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        UPDATE public.exam_scheduling 
                        SET deleted_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                        WHERE exam_name = %s AND organization_id = %s AND deleted_at IS NULL
                        RETURNING exam_name
                    ''', (exam_name, organization_id))
                    
                    result = cursor.fetchone()
                    conn.commit()
                    return result is not None
                    
        except Exception as e:
            print(f"Error deleting exam scheduling: {e}")
            return False
    
    def list_exams_by_organization(self, organization_id: str, page: int = 1, page_size: int = 10, 
                                 status: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """Lists all exams of an organization with pagination"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    where_conditions = ["es.organization_id = %s", "es.deleted_at IS NULL"]
                    params = [organization_id]
                    
                    if status:
                        where_conditions.append("es.status = %s")
                        params.append(status)
                    
                    where_clause = " AND ".join(where_conditions)
                    offset = (page - 1) * page_size
                    
                    query = f'''
                        SELECT es.*, o.name as organization_name, p.name as patient_name
                        FROM public.exam_scheduling es
                        LEFT JOIN public.organizations o ON es.organization_id = o.id
                        LEFT JOIN public.patients p ON es.patient_id = p.id
                        WHERE {where_clause}
                        ORDER BY es.scheduled_date ASC
                        LIMIT %s OFFSET %s
                    '''
                    params.extend([page_size, offset])
                    
                    cursor.execute(query, params)
                    results = cursor.fetchall()
                    return [dict(result) for result in results]
                    
        except Exception as e:
            print(f"Error fetching organization exams: {e}")
            return None
    
    def get_upcoming_exams(self, organization_id: str, hours_ahead: int = 24) -> Optional[List[Dict[str, Any]]]:
        """Gets upcoming exams within specified hours"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT es.*, o.name as organization_name, p.name as patient_name
                        FROM public.exam_scheduling es
                        LEFT JOIN public.organizations o ON es.organization_id = o.id
                        LEFT JOIN public.patients p ON es.patient_id = p.id
                        WHERE es.organization_id = %s 
                        AND es.deleted_at IS NULL
                        AND es.status = 'scheduled'
                        AND es.scheduled_date BETWEEN CURRENT_TIMESTAMP AND CURRENT_TIMESTAMP + (%s || ' hours')::interval
                        ORDER BY es.scheduled_date ASC
                    ''', (organization_id, hours_ahead))
                    
                    results = cursor.fetchall()
                    return [dict(result) for result in results]
                    
        except Exception as e:
            print(f"Error fetching upcoming exams: {e}")
            return None
    
    def get_exam_statistics(self, organization_id: str) -> Optional[Dict[str, Any]]:
        """Gets statistics for exams in an organization"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT 
                            status,
                            COUNT(*) as count,
                            COUNT(*) FILTER (WHERE scheduled_date >= CURRENT_DATE) as upcoming_count
                        FROM public.exam_scheduling 
                        WHERE organization_id = %s AND deleted_at IS NULL
                        GROUP BY status
                    ''', (organization_id,))
                    
                    results = cursor.fetchall()
                    stats = {
                        'total_exams': 0,
                        'upcoming_exams': 0,
                        'by_status': {}
                    }
                    
                    for row in results:
                        status = row['status']
                        count = row['count']
                        upcoming = row['upcoming_count']
                        
                        stats['total_exams'] += count
                        stats['upcoming_exams'] += upcoming
                        stats['by_status'][status] = count
                    
                    return stats
                    
        except Exception as e:
            print(f"Error fetching exam statistics: {e}")
            return None

# Global database instance - FIXED: Now matches the class name
db = Database()