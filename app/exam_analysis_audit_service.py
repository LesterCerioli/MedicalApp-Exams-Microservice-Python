import logging
from uuid import UUID
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Tuple
from app.database import db

logger = logging.getLogger(__name__)

class ExamAnalysisAuditService:
    
    async def _get_organization_id_by_name(self, organization_name: str) -> Optional[UUID]:
        
        logger.debug(f"Resolving organization ID for name: {organization_name}")
        async with db.get_async_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM public.organizations WHERE name = %s AND deleted_at IS NULL",
                (organization_name,)
            )
            org = cursor.fetchone()
            if not org:
                return None
            return UUID(org['id'])

    async def _get_analysis_organization_id(self, analysis_id: UUID) -> Optional[UUID]:
        
        async with db.get_async_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT organizations_id FROM public.exam_analyses WHERE id = %s",
                (str(analysis_id),)
            )
            row = cursor.fetchone()
            return UUID(row['organizations_id']) if row else None

    
    async def log_insert(
        self,
        analysis_id: UUID,
        new_data: Dict[str, Any],
        application_name: Optional[str] = None
    ) -> bool:
        
        logger.info(f"Logging INSERT for exam analysis ID: {analysis_id}")
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                query = """
                    INSERT INTO public.exam_analyses_audit (
                        exam_analyses_id,
                        action_type,
                        new_data,
                        application_name
                    ) VALUES (%s, 'INSERT', %s::jsonb, %s)
                """
                cursor.execute(query, (str(analysis_id), new_data, application_name))
                conn.commit()
                logger.debug(f"INSERT audit logged for analysis {analysis_id}")
                return True
        except Exception as e:
            logger.error(f"Error logging INSERT audit: {e}")
            raise Exception(f"Database error logging audit: {str(e)}")

    async def log_update(
        self,
        analysis_id: UUID,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any],
        changed_fields: List[Tuple[str, str, str]],  # (campo, valor_antigo, valor_novo)
        application_name: Optional[str] = None
    ) -> bool:
        
        logger.info(f"Logging UPDATE for exam analysis ID: {analysis_id}")
        try:
            
            changed_fields_array = [
                [str(field), str(old), str(new)] for field, old, new in changed_fields
            ]

            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                query = """
                    INSERT INTO public.exam_analyses_audit (
                        exam_analyses_id,
                        action_type,
                        old_data,
                        new_data,
                        changed_fields,
                        application_name
                    ) VALUES (%s, 'UPDATE', %s::jsonb, %s::jsonb, %s, %s)
                """
                cursor.execute(
                    query,
                    (
                        str(analysis_id),
                        old_data,
                        new_data,
                        changed_fields_array,
                        application_name
                    )
                )
                conn.commit()
                logger.debug(f"UPDATE audit logged for analysis {analysis_id}")
                return True
        except Exception as e:
            logger.error(f"Error logging UPDATE audit: {e}")
            raise Exception(f"Database error logging audit: {str(e)}")

    async def log_delete(
        self,
        analysis_id: UUID,
        old_data: Dict[str, Any],
        application_name: Optional[str] = None
    ) -> bool:
        
        logger.info(f"Logging DELETE for exam analysis ID: {analysis_id}")
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                query = """
                    INSERT INTO public.exam_analyses_audit (
                        exam_analyses_id,
                        action_type,
                        old_data,
                        application_name
                    ) VALUES (%s, 'DELETE', %s::jsonb, %s)
                """
                cursor.execute(query, (str(analysis_id), old_data, application_name))
                conn.commit()
                logger.debug(f"DELETE audit logged for analysis {analysis_id}")
                return True
        except Exception as e:
            logger.error(f"Error logging DELETE audit: {e}")
            raise Exception(f"Database error logging audit: {str(e)}")

    
    async def get_audit_for_analysis(
        self,
        analysis_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        
        logger.info(f"Fetching audit for analysis ID: {analysis_id}")
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT *
                    FROM public.exam_analyses_audit
                    WHERE exam_analyses_id = %s
                    ORDER BY changed_at DESC
                    LIMIT %s OFFSET %s
                """
                cursor.execute(query, (str(analysis_id), limit, offset))
                rows = cursor.fetchall()
                audits = [dict(row) for row in rows]
                logger.info(f"Found {len(audits)} audit records for analysis {analysis_id}")
                return audits
        except Exception as e:
            logger.error(f"Error fetching audit for analysis: {e}")
            raise Exception(f"Database error fetching audit: {str(e)}")

    async def get_audit_by_organization(
        self,
        organization_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        action_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        
        logger.info(f"Fetching audit for organization: {organization_name}")

        try:
            org_id = await self._get_organization_id_by_name(organization_name)
            if not org_id:
                raise Exception(f"Organization '{organization_name}' not found")

            async with db.get_async_connection() as conn:
                cursor = conn.cursor()

                conditions = ["ea.organizations_id = %s"]
                params = [str(org_id)]

                if start_date:
                    conditions.append("a.changed_at >= %s")
                    params.append(start_date)
                if end_date:
                    conditions.append("a.changed_at <= %s")
                    params.append(end_date)
                if action_type:
                    conditions.append("a.action_type = %s")
                    params.append(action_type)

                where_clause = " AND ".join(conditions)
                
                count_query = f"""
                    SELECT COUNT(*) as total
                    FROM public.exam_analyses_audit a
                    JOIN public.exam_analyses ea ON a.exam_analyses_id = ea.id
                    WHERE {where_clause}
                """
                cursor.execute(count_query, params)
                total_count = cursor.fetchone()["total"]

                
                offset = (page - 1) * page_size
                select_query = f"""
                    SELECT a.*, ea.exam_type, ea.organizations_id
                    FROM public.exam_analyses_audit a
                    JOIN public.exam_analyses ea ON a.exam_analyses_id = ea.id
                    WHERE {where_clause}
                    ORDER BY a.changed_at DESC
                    LIMIT %s OFFSET %s
                """
                cursor.execute(select_query, params + [page_size, offset])
                rows = cursor.fetchall()

                audits = [dict(row) for row in rows]
                total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1

                logger.info(f"Found {len(audits)} audit records for organization {organization_name}")
                return {
                    "audits": audits,
                    "total_count": total_count,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                }

        except Exception as e:
            logger.error(f"Error fetching audit by organization: {e}")
            raise Exception(f"Database error fetching audit: {str(e)}")

    async def get_audit_by_user(
        self,
        db_user: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        
        logger.info(f"Fetching audit for DB user: {db_user}")
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT *
                    FROM public.exam_analyses_audit
                    WHERE db_user = %s
                    ORDER BY changed_at DESC
                    LIMIT %s OFFSET %s
                """
                cursor.execute(query, (db_user, limit, offset))
                rows = cursor.fetchall()
                audits = [dict(row) for row in rows]
                logger.info(f"Found {len(audits)} audit records for user {db_user}")
                return audits
        except Exception as e:
            logger.error(f"Error fetching audit by user: {e}")
            raise Exception(f"Database error fetching audit: {str(e)}")

    async def get_audit_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        
        logger.info(f"Fetching audit from {start_date} to {end_date}")
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                conditions = ["changed_at >= %s", "changed_at <= %s"]
                params = [start_date, end_date]

                count_query = f"""
                    SELECT COUNT(*) as total
                    FROM public.exam_analyses_audit
                    WHERE {' AND '.join(conditions)}
                """
                cursor.execute(count_query, params)
                total_count = cursor.fetchone()["total"]

                offset = (page - 1) * page_size
                select_query = f"""
                    SELECT *
                    FROM public.exam_analyses_audit
                    WHERE {' AND '.join(conditions)}
                    ORDER BY changed_at DESC
                    LIMIT %s OFFSET %s
                """
                cursor.execute(select_query, params + [page_size, offset])
                rows = cursor.fetchall()

                audits = [dict(row) for row in rows]
                total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1

                logger.info(f"Found {len(audits)} audit records in date range")
                return {
                    "audits": audits,
                    "total_count": total_count,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                }
        except Exception as e:
            logger.error(f"Error fetching audit by date range: {e}")
            raise Exception(f"Database error fetching audit: {str(e)}")



exam_analysis_audit_service = ExamAnalysisAuditService()