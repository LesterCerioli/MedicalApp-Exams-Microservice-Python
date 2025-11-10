import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict, Any, List, Union
from app.config import config
import contextlib
import uuid

class Database:
    def __init__(self, database_type: str = 'primary'):
        """
        Initialize database connection for primary or secondary database.
        
        Args:
            database_type: 'primary' for medical_db, 'secondary' for medical_dbx
        """
        self.database_type = database_type
        self.connection_string = self._get_connection_string()
    
    def _get_connection_string(self) -> str:
        """Get connection string based on database type"""
        if self.database_type == 'secondary':
            return config.DATABASE_URL_SECONDARY
        else:
            return config.DATABASE_URL
    
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
        """Initializes the users table with proper constraints"""
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
                    # Search with TRIM and case-insensitive
                    cursor.execute(
                        "SELECT id, name FROM public.organizations WHERE LOWER(TRIM(name)) = LOWER(TRIM(%s))",
                        (organization_name,)
                    )
                    result = cursor.fetchone()
                    
                    if result:
                        print(f"DEBUG: Organization found - ID: {result['id']}, Name: '{result['name']}'")
                        return result['id']
                    else:
                        # List all organizations for debug
                        cursor.execute("SELECT id, name FROM public.organizations")
                        all_orgs = cursor.fetchall()
                        print(f"DEBUG: Available organizations: {[dict(org) for org in all_orgs]}")
                        return None
                        
        except Exception as e:
            print(f"Error fetching organization: {e}")
            return None
    
    def create_user(self, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Creates a new user in the database"""
        try:
            print(f"DEBUG: Creating user with data: {user_data}")
            
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Generate UUID manually
                    user_id = str(uuid.uuid4())
                    
                    cursor.execute('''
                        INSERT INTO public.users (id, name, email, password, role, organization_id, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        RETURNING id, name, email, role, created_at, updated_at
                    ''', (
                        user_id,
                        user_data['name'],
                        user_data['email'],
                        user_data['password'],
                        user_data['role'],
                        user_data['organization_id']
                    ))
                    
                    result = cursor.fetchone()
                    conn.commit()
                    
                    if result:
                        print(f"DEBUG: User created successfully: {dict(result)}")
                        return dict(result)
                    else:
                        print("DEBUG: User creation failed - no result returned")
                        return None
                    
        except psycopg2.IntegrityError as e:
            print(f"Integrity error creating user (duplicate email?): {e}")
            return None
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
    
    def get_user_by_email_and_org(self, email: str, organization_id: str) -> Optional[Dict[str, Any]]:
        """Finds user by email and organization_id"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT id, name, email, password, role, organization_id, created_at
                        FROM public.users 
                        WHERE email = %s AND organization_id = %s AND deleted_at IS NULL
                    ''', (email, organization_id))
                    
                    result = cursor.fetchone()
                    return dict(result) if result else None
                    
        except Exception as e:
            print(f"Error fetching user: {e}")
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Finds user by ID"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT id, name, email, password, role, organization_id, created_at
                        FROM public.users WHERE id = %s AND deleted_at IS NULL
                    ''', (user_id,))
                    
                    result = cursor.fetchone()
                    return dict(result) if result else None
                    
        except Exception as e:
            print(f"Error fetching user by ID: {e}")
            return None
    
    def get_organization_users(self, organization_id: str) -> Optional[List[Dict[str, Any]]]:
        """Lists all users of an organization"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT id, name, email, role, created_at
                        FROM public.users 
                        WHERE organization_id = %s AND deleted_at IS NULL
                        ORDER BY created_at DESC
                    ''', (organization_id,))
                    
                    results = cursor.fetchall()
                    return [dict(result) for result in results]
        except Exception as e:
            print(f"Error fetching organization users: {e}")
            return None

    
    def execute_query(self, query: str, params: tuple = None, fetch: bool = True) -> Optional[Union[List[Dict[str, Any]], bool]]:
        """
        Execute a custom SQL query on the database.
        
        Args:
            query: SQL query to execute
            params: Parameters for the query
            fetch: Whether to fetch results or just execute
            
        Returns:
            Query results if fetch=True, otherwise success status
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params or ())
                    
                    if fetch:
                        results = cursor.fetchall()
                        return [dict(result) for result in results]
                    else:
                        conn.commit()
                        return True
                        
        except Exception as e:
            print(f"Error executing query: {e}")
            return None

# Global database instances
db_primary = Database('primary')
db_secondary = Database('secondary')