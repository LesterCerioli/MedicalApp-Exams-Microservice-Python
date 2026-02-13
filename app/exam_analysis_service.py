import logging
from uuid import UUID
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from app.database import db

logger = logging.getLogger(__name__)


class ExamAnalysisService:
    
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

    
    async def create_exam_analysis(
        self,
        organization_name: str,
        exam_type: str,
        original_results: Dict[str, Any] | List[Any],
        exam_date: Optional[datetime] = None,
        exam_result: Optional[Dict[str, Any]] = None,
        observations: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        
        logger.info(f"Creating exam analysis for organization: {organization_name}")
        
        if not exam_type or not exam_type.strip():
            raise Exception("Exam type cannot be empty")
        if not original_results:
            raise Exception("Original results cannot be empty")

        try:
            
            organization_id = await self._get_organization_id_by_name(organization_name)
            if not organization_id:
                raise Exception(f"Organization '{organization_name}' not found or is deleted")

            async with db.get_async_connection() as conn:
                cursor = conn.cursor()

                insert_query = """
                    INSERT INTO public.exam_analyses (
                        organizations_id,
                        exam_type,
                        exam_date,
                        original_results,
                        exam_result,
                        observations,
                        analysis_date,
                        created_at,
                        updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    RETURNING *
                """
                cursor.execute(
                    insert_query,
                    (
                        str(organization_id),
                        exam_type.strip(),
                        exam_date or datetime.utcnow(),
                        original_results,      # psycopg2 automatically converts dict/list to JSONB
                        exam_result,
                        observations,
                    )
                )

                created = cursor.fetchone()
                conn.commit()

                if not created:
                    raise Exception("Failed to create exam analysis")

                logger.info(f"Exam analysis created successfully with ID: {created['id']}")
                return dict(created)

        except Exception as e:
            logger.error(f"Error creating exam analysis: {e}")
            raise Exception(f"Database error creating exam analysis: {str(e)}")

    
    async def get_exam_analysis_by_id(self, analysis_id: UUID) -> Optional[Dict[str, Any]]:
        
        logger.info(f"Fetching exam analysis by ID: {analysis_id}")
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT * FROM public.exam_analyses
                    WHERE id = %s
                """
                cursor.execute(query, (str(analysis_id),))
                row = cursor.fetchone()
                if not row:
                    logger.warning(f"Exam analysis not found with ID: {analysis_id}")
                    return None
                return dict(row)
        except Exception as e:
            logger.error(f"Error fetching exam analysis: {e}")
            raise Exception(f"Database error fetching exam analysis: {str(e)}")

    
    async def update_exam_analysis(
        self,
        analysis_id: UUID,
        exam_type: Optional[str] = None,
        exam_date: Optional[datetime] = None,
        original_results: Optional[Dict[str, Any] | List[Any]] = None,
        exam_result: Optional[Dict[str, Any]] = None,
        observations: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        
        logger.info(f"Updating exam analysis with ID: {analysis_id}")
        
        if exam_type is not None and not exam_type.strip():
            raise Exception("Exam type cannot be empty")

        try:
            
            existing = await self.get_exam_analysis_by_id(analysis_id)
            if not existing:
                return None

            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                
                update_fields = []
                params = []

                if exam_type is not None:
                    update_fields.append("exam_type = %s")
                    params.append(exam_type.strip())
                if exam_date is not None:
                    update_fields.append("exam_date = %s")
                    params.append(exam_date)
                if original_results is not None:
                    update_fields.append("original_results = %s")
                    params.append(original_results)
                if exam_result is not None:
                    update_fields.append("exam_result = %s")
                    params.append(exam_result)
                if observations is not None:
                    update_fields.append("observations = %s")
                    params.append(observations)

                if not update_fields:
                    return existing

                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                params.append(str(analysis_id))

                update_query = f"""
                    UPDATE public.exam_analyses
                    SET {', '.join(update_fields)}
                    WHERE id = %s
                    RETURNING *
                """
                cursor.execute(update_query, params)
                updated = cursor.fetchone()
                conn.commit()

                if not updated:
                    return None

                logger.info(f"Exam analysis updated successfully: {analysis_id}")
                return dict(updated)

        except Exception as e:
            logger.error(f"Error updating exam analysis: {e}")
            raise Exception(f"Database error updating exam analysis: {str(e)}")

    
    async def delete_exam_analysis(self, analysis_id: UUID) -> bool:
        
        logger.info(f"Deleting exam analysis with ID: {analysis_id}")
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                query = """
                    DELETE FROM public.exam_analyses
                    WHERE id = %s
                """
                cursor.execute(query, (str(analysis_id),))
                conn.commit()
                success = cursor.rowcount > 0
                if not success:
                    logger.warning(f"Exam analysis not found: {analysis_id}")
                else:
                    logger.info(f"Exam analysis deleted successfully: {analysis_id}")
                return success
        except Exception as e:
            logger.error(f"Error deleting exam analysis: {e}")
            raise Exception(f"Database error deleting exam analysis: {str(e)}")

    
    async def get_organization_analyses(
        self,
        organization_name: str,
        exam_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        
        logger.info(f"Fetching exam analyses for organization: {organization_name}")

        try:
            
            organization_id = await self._get_organization_id_by_name(organization_name)
            if not organization_id:
                raise Exception(f"Organization '{organization_name}' not found or is deleted")

            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                
                conditions = ["organizations_id = %s"]
                params = [str(organization_id)]

                if exam_type:
                    conditions.append("exam_type = %s")
                    params.append(exam_type)
                if start_date:
                    conditions.append("exam_date >= %s")
                    params.append(start_date)
                if end_date:
                    conditions.append("exam_date <= %s")
                    params.append(end_date)

                where_clause = " AND ".join(conditions)

                
                count_query = f"""
                    SELECT COUNT(*) as total
                    FROM public.exam_analyses
                    WHERE {where_clause}
                """
                cursor.execute(count_query, params)
                total_count = cursor.fetchone()["total"]

                
                offset = (page - 1) * page_size
                select_query = f"""
                    SELECT *
                    FROM public.exam_analyses
                    WHERE {where_clause}
                    ORDER BY exam_date DESC, created_at DESC
                    LIMIT %s OFFSET %s
                """
                cursor.execute(select_query, params + [page_size, offset])
                rows = cursor.fetchall()

                items = [dict(row) for row in rows]
                total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1

                logger.info(f"Found {len(items)} analyses for organization {organization_name}")
                return {
                    "analyses": items,
                    "total_count": total_count,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                }

        except Exception as e:
            logger.error(f"Error fetching organization analyses: {e}")
            raise Exception(f"Database error fetching analyses: {str(e)}")

    
    async def get_analyses_without_exam_result(
        self,
        organization_name: str,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        
        logger.info(f"Fetching analyses without exam_result for organization: {organization_name}")

        try:
            organization_id = await self._get_organization_id_by_name(organization_name)
            if not organization_id:
                raise Exception(f"Organization '{organization_name}' not found or is deleted")

            async with db.get_async_connection() as conn:
                cursor = conn.cursor()

                conditions = ["organizations_id = %s", "exam_result IS NULL"]
                params = [str(organization_id)]

                where_clause = " AND ".join(conditions)

                
                count_query = f"""
                    SELECT COUNT(*) as total
                    FROM public.exam_analyses
                    WHERE {where_clause}
                """
                cursor.execute(count_query, params)
                total_count = cursor.fetchone()["total"]

                
                offset = (page - 1) * page_size
                select_query = f"""
                    SELECT *
                    FROM public.exam_analyses
                    WHERE {where_clause}
                    ORDER BY exam_date DESC, created_at DESC
                    LIMIT %s OFFSET %s
                """
                cursor.execute(select_query, params + [page_size, offset])
                rows = cursor.fetchall()

                items = [dict(row) for row in rows]
                total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1

                logger.info(f"Found {len(items)} analyses without exam_result for {organization_name}")
                return {
                    "analyses": items,
                    "total_count": total_count,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                }

        except Exception as e:
            logger.error(f"Error fetching analyses without exam_result: {e}")
            raise Exception(f"Database error fetching analyses: {str(e)}")

    
    async def get_analyses_by_exam_type(
        self,
        organization_name: str,
        exam_type: str,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        
        return await self.get_organization_analyses(
            organization_name=organization_name,
            exam_type=exam_type,
            page=page,
            page_size=page_size,
        )

    
    async def get_analysis_statistics(
        self,
        organization_name: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        
        logger.info(f"Fetching analysis statistics for organization: {organization_name}")

        try:
            organization_id = await self._get_organization_id_by_name(organization_name)
            if not organization_id:
                raise Exception(f"Organization '{organization_name}' not found or is deleted")

            async with db.get_async_connection() as conn:
                cursor = conn.cursor()

                params = [str(organization_id)]
                date_filter = ""
                if start_date and end_date:
                    date_filter = " AND exam_date BETWEEN %s AND %s"
                    params.extend([start_date, end_date])
                elif start_date:
                    date_filter = " AND exam_date >= %s"
                    params.append(start_date)
                elif end_date:
                    date_filter = " AND exam_date <= %s"
                    params.append(end_date)

                
                base_query = f"""
                    SELECT
                        COUNT(*) as total_analyses,
                        COUNT(exam_result) as analyses_with_result,
                        COUNT(*) - COUNT(exam_result) as analyses_without_result
                    FROM public.exam_analyses
                    WHERE organizations_id = %s {date_filter}
                """
                cursor.execute(base_query, params)
                counts = dict(cursor.fetchone())

                
                type_query = f"""
                    SELECT exam_type, COUNT(*) as count
                    FROM public.exam_analyses
                    WHERE organizations_id = %s {date_filter}
                    GROUP BY exam_type
                    ORDER BY count DESC
                    LIMIT 5
                """
                               
                
                type_params = [str(organization_id)]
                if start_date and end_date:
                    type_params.extend([start_date, end_date])
                elif start_date:
                    type_params.append(start_date)
                elif end_date:
                    type_params.append(end_date)

                cursor.execute(type_query, type_params)
                top_types = [dict(row) for row in cursor.fetchall()]

                counts["top_exam_types"] = top_types
                logger.info(f"Statistics fetched for {organization_name}")
                return counts

        except Exception as e:
            logger.error(f"Error fetching analysis statistics: {e}")
            raise Exception(f"Database error fetching statistics: {str(e)}")


# Global instance
exam_analysis_service = ExamAnalysisService()