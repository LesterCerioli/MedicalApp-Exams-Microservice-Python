import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict, Any, List
from app.config import config
import contextlib
import uuid

class Database:
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
        """Initializes the users table with proper constraints"""
        # Como as tabelas já existem, este método pode ser simplificado
        # ou até removido se não for necessário criar tabelas
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
                    # Busca com TRIM e case-insensitive
                    cursor.execute(
                        "SELECT id, name FROM public.organizations WHERE LOWER(TRIM(name)) = LOWER(TRIM(%s))",
                        (organization_name,)
                    )
                    result = cursor.fetchone()
                    
                    if result:
                        print(f"DEBUG: Organization found - ID: {result['id']}, Name: '{result['name']}'")
                        return result['id']
                    else:
                        # Listar todas as organizações para debug
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
                    # Gera UUID manualmente
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

    @contextlib.asynccontextmanager
    async def get_async_connection(self):
        loop = asyncio.get_event_loop()
        conn = await loop.run_in_executor(
            None,
            lambda: psycopg2.connect(
                self.connection_string,
                cursor_factory=RealDictCursor
            )
        )
        try:
            yield conn
        finally:
            await loop.run_in_executor(None, conn.close)
            
    async def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        async with self.get_async_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            results = cursor.fetchall()
            conn.commit()
            return [dict(row) for row in results] if results else []
        
    async def execute_update(self, query: str, params: tuple = None) -> bool:
        async with self.get_async_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            conn.commit()
            return cursor.rowcount > 0
        
    async def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict[str, Any]]:
        async with self.get_async_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            result = cursor.fetchone()
            return dict(result) if result else None
    


# Global database instance
db = Database()