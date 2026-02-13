import logging
from uuid import UUID
from datetime import date
from typing import List, Optional, Dict, Any
from app.database import db

logger = logging.getLogger(__name__)


class ExamService:

    
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

    async def _get_patient_id_by_name_and_organization(
        self,
        patient_name: str,
        organization_id: UUID
    ) -> Optional[UUID]:
        
        logger.debug(f"Resolving patient ID for name '{patient_name}' in organization {organization_id}")
        async with db.get_async_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM public.patients WHERE name = %s AND organization_id = %s AND deleted_at IS NULL",
                (patient_name, str(organization_id))
            )
            rows = cursor.fetchall()
            if not rows:
                return None
            if len(rows) > 1:
                raise Exception(
                    f"Multiple patients with name '{patient_name}' found in organization. "
                    "Please use CPF/SSN or patient ID."
                )
            return UUID(rows[0]['id'])

    
    async def create_exam(
        self,
        organization_name: str,
        exam_type: str,
        patient_name: Optional[str] = None,
        status: str = "pending",
        requested_at: Optional[date] = None,
        notes: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:

        logger.info(f"Creating exam for organization: {organization_name}")
        
        if not exam_type:
            raise Exception("Exam type cannot be empty")

        valid_statuses = ["pending", "scheduled", "completed", "cancelled", "in_progress"]
        if status not in valid_statuses:
            raise Exception(f"Invalid status. Must be one of: {valid_statuses}")

        try:
            
            organization_id = await self._get_organization_id_by_name(organization_name)
            if not organization_id:
                raise Exception(f"Organization '{organization_name}' not found or is deleted")

            
            patient_id = None
            if patient_name:
                patient_id = await self._get_patient_id_by_name_and_organization(patient_name, organization_id)
                if not patient_id:
                    raise Exception(
                        f"Patient '{patient_name}' not found in organization '{organization_name}'"
                    )

            async with db.get_async_connection() as conn:
                cursor = conn.cursor()

                
                insert_query = """
                    INSERT INTO public.medical_exams (
                        organization_id, patient_id, exam_type, status,
                        requested_at, notes, created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    RETURNING *
                """
                cursor.execute(
                    insert_query,
                    (
                        str(organization_id),
                        str(patient_id) if patient_id else None,
                        exam_type,
                        status,
                        requested_at,
                        notes,
                    ),
                )

                created_exam = cursor.fetchone()
                conn.commit()

                if not created_exam:
                    raise Exception("Failed to create exam")

                logger.info(f"Exam created successfully with ID: {created_exam['id']}")
                return dict(created_exam)

        except Exception as e:
            logger.error(f"Error creating exam: {e}")
            raise Exception(f"Database error creating exam: {str(e)}")

    
    async def get_exam_by_id(self, exam_id: UUID) -> Optional[Dict[str, Any]]:
        logger.info(f"Fetching exam by ID: {exam_id}")
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT * FROM public.medical_exams
                    WHERE id = %s AND deleted_at IS NULL
                """
                cursor.execute(query, (str(exam_id),))
                exam = cursor.fetchone()
                if not exam:
                    logger.warning(f"Exam not found with ID: {exam_id}")
                    return None
                logger.info(f"Exam found: {exam_id}")
                return dict(exam)
        except Exception as e:
            logger.error(f"Error fetching exam: {e}")
            raise Exception(f"Database error fetching exam: {str(e)}")

    
    async def update_exam(
        self,
        exam_id: UUID,
        exam_type: Optional[str] = None,
        status: Optional[str] = None,
        requested_at: Optional[date] = None,
        notes: Optional[str] = None,
        patient_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:

        logger.info(f"Updating exam with ID: {exam_id}")

        if status is not None:
            valid_statuses = ["pending", "scheduled", "completed", "cancelled", "in_progress"]
            if status not in valid_statuses:
                raise Exception(f"Invalid status. Must be one of: {valid_statuses}")

        try:
            
            current_exam = await self.get_exam_by_id(exam_id)
            if not current_exam:
                return None

            
            patient_id = None
            if patient_name is not None:
                org_id = UUID(current_exam["organization_id"])
                patient_id = await self._get_patient_id_by_name_and_organization(patient_name, org_id)
                if not patient_id:
                    raise Exception(
                        f"Patient '{patient_name}' not found in the organization of this exam"
                    )

            async with db.get_async_connection() as conn:
                cursor = conn.cursor()

                
                update_fields = []
                params = []

                if exam_type is not None:
                    update_fields.append("exam_type = %s")
                    params.append(exam_type)
                if status is not None:
                    update_fields.append("status = %s")
                    params.append(status)
                if requested_at is not None:
                    update_fields.append("requested_at = %s")
                    params.append(requested_at)
                if notes is not None:
                    update_fields.append("notes = %s")
                    params.append(notes)
                if patient_name is not None:
                    update_fields.append("patient_id = %s")
                    params.append(str(patient_id) if patient_id else None)

                if not update_fields:
                    return current_exam

                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                params.append(str(exam_id))

                update_query = f"""
                    UPDATE public.medical_exams
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND deleted_at IS NULL
                    RETURNING *
                """
                cursor.execute(update_query, params)
                updated_exam = cursor.fetchone()
                conn.commit()

                if not updated_exam:
                    return None

                logger.info(f"Exam updated successfully: {exam_id}")
                return dict(updated_exam)

        except Exception as e:
            logger.error(f"Error updating exam: {e}")
            raise Exception(f"Database error updating exam: {str(e)}")

    
    async def delete_exam(self, exam_id: UUID) -> bool:
        logger.info(f"Deleting exam with ID: {exam_id}")
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                query = """
                    UPDATE public.medical_exams
                    SET deleted_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND deleted_at IS NULL
                """
                cursor.execute(query, (str(exam_id),))
                conn.commit()
                success = cursor.rowcount > 0
                if not success:
                    logger.warning(f"Exam not found or already deleted: {exam_id}")
                    return False
                logger.info(f"Exam deleted successfully: {exam_id}")
                return True
        except Exception as e:
            logger.error(f"Error deleting exam: {e}")
            raise Exception(f"Database error deleting exam: {str(e)}")

    async def restore_exam(self, exam_id: UUID) -> Optional[Dict[str, Any]]:
        logger.info(f"Restoring exam: {exam_id}")
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                query = """
                    UPDATE public.medical_exams
                    SET deleted_at = NULL, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND deleted_at IS NOT NULL
                    RETURNING *
                """
                cursor.execute(query, (str(exam_id),))
                restored_exam = cursor.fetchone()
                conn.commit()
                if not restored_exam:
                    logger.warning(f"Exam not found or not deleted: {exam_id}")
                    return None
                logger.info(f"Exam restored successfully: {exam_id}")
                return dict(restored_exam)
        except Exception as e:
            logger.error(f"Error restoring exam: {e}")
            raise Exception(f"Database error restoring exam: {str(e)}")

    

    async def get_organization_exams(
        self,
        organization_name: str,
        patient_name: Optional[str] = None,
        status: Optional[str] = None,
        exam_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:

        logger.info(f"Fetching exams for organization: {organization_name}")

        try:
            
            organization_id = await self._get_organization_id_by_name(organization_name)
            if not organization_id:
                raise Exception(f"Organization '{organization_name}' not found or is deleted")

            
            patient_id = None
            if patient_name:
                patient_id = await self._get_patient_id_by_name_and_organization(patient_name, organization_id)
                if not patient_id:
                    raise Exception(
                        f"Patient '{patient_name}' not found in organization '{organization_name}'"
                    )

            async with db.get_async_connection() as conn:
                cursor = conn.cursor()

                conditions = ["organization_id = %s", "deleted_at IS NULL"]
                params = [str(organization_id)]

                if patient_id:
                    conditions.append("patient_id = %s")
                    params.append(str(patient_id))
                if status:
                    conditions.append("status = %s")
                    params.append(status)
                if exam_type:
                    conditions.append("exam_type = %s")
                    params.append(exam_type)
                if start_date:
                    conditions.append("requested_at >= %s")
                    params.append(start_date)
                if end_date:
                    conditions.append("requested_at <= %s")
                    params.append(end_date)

                where_clause = " AND ".join(conditions)

                
                count_query = f"""
                    SELECT COUNT(*) as total
                    FROM public.medical_exams
                    WHERE {where_clause}
                """
                cursor.execute(count_query, params)
                total_count = cursor.fetchone()["total"]

                
                offset = (page - 1) * page_size
                select_query = f"""
                    SELECT *
                    FROM public.medical_exams
                    WHERE {where_clause}
                    ORDER BY requested_at DESC NULLS LAST, created_at DESC
                    LIMIT %s OFFSET %s
                """
                cursor.execute(select_query, params + [page_size, offset])
                exams = cursor.fetchall()

                exams_list = [dict(exam) for exam in exams]
                total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1

                logger.info(f"Found {len(exams_list)} exams for organization {organization_name}")
                return {
                    "exams": exams_list,
                    "total_count": total_count,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                }

        except Exception as e:
            logger.error(f"Error fetching organization exams: {e}")
            raise Exception(f"Database error fetching exams: {str(e)}")

    
    async def get_patient_exams(
        self,
        patient_name: str,
        organization_name: str,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:

        logger.info(f"Fetching exams for patient: {patient_name} in organization: {organization_name}")

        try:
            
            organization_id = await self._get_organization_id_by_name(organization_name)
            if not organization_id:
                raise Exception(f"Organization '{organization_name}' not found or is deleted")

            
            patient_id = await self._get_patient_id_by_name_and_organization(patient_name, organization_id)
            if not patient_id:
                raise Exception(
                    f"Patient '{patient_name}' not found in organization '{organization_name}'"
                )

            async with db.get_async_connection() as conn:
                cursor = conn.cursor()

                conditions = ["patient_id = %s", "deleted_at IS NULL"]
                params = [str(patient_id)]

                conditions.append("organization_id = %s")
                params.append(str(organization_id))

                if status:
                    conditions.append("status = %s")
                    params.append(status)
                if start_date:
                    conditions.append("requested_at >= %s")
                    params.append(start_date)
                if end_date:
                    conditions.append("requested_at <= %s")
                    params.append(end_date)

                where_clause = " AND ".join(conditions)

                
                count_query = f"""
                    SELECT COUNT(*) as total
                    FROM public.medical_exams
                    WHERE {where_clause}
                """
                cursor.execute(count_query, params)
                total_count = cursor.fetchone()["total"]

                
                offset = (page - 1) * page_size
                select_query = f"""
                    SELECT *
                    FROM public.medical_exams
                    WHERE {where_clause}
                    ORDER BY requested_at DESC NULLS LAST, created_at DESC
                    LIMIT %s OFFSET %s
                """
                cursor.execute(select_query, params + [page_size, offset])
                exams = cursor.fetchall()

                exams_list = [dict(exam) for exam in exams]
                total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1

                logger.info(f"Found {len(exams_list)} exams for patient {patient_name}")
                return {
                    "exams": exams_list,
                    "total_count": total_count,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                }

        except Exception as e:
            logger.error(f"Error fetching patient exams: {e}")
            raise Exception(f"Database error fetching patient exams: {str(e)}")

    
    async def update_exam_status(self, exam_id: UUID, status: str) -> bool:
        logger.info(f"Updating exam status: {exam_id} -> {status}")
        valid_statuses = ["pending", "scheduled", "completed", "cancelled", "in_progress"]
        if status not in valid_statuses:
            raise Exception(f"Invalid status. Must be one of: {valid_statuses}")
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                query = """
                    UPDATE public.medical_exams
                    SET status = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND deleted_at IS NULL
                """
                cursor.execute(query, (status, str(exam_id)))
                conn.commit()
                success = cursor.rowcount > 0
                if not success:
                    logger.warning(f"Exam not found or not updated: {exam_id}")
                    return False
                logger.info(f"Exam status updated successfully: {exam_id}")
                return True
        except Exception as e:
            logger.error(f"Error updating exam status: {e}")
            raise Exception(f"Database error updating exam status: {str(e)}")

    async def bulk_update_status(self, exam_ids: List[UUID], status: str) -> int:
        logger.info(f"Bulk updating status for {len(exam_ids)} exams to {status}")
        if not exam_ids:
            return 0
        valid_statuses = ["pending", "scheduled", "completed", "cancelled", "in_progress"]
        if status not in valid_statuses:
            raise Exception(f"Invalid status. Must be one of: {valid_statuses}")
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                id_strings = [str(eid) for eid in exam_ids]

                update_query = """
                    UPDATE public.medical_exams
                    SET status = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ANY(%s::uuid[]) AND deleted_at IS NULL
                """
                cursor.execute(update_query, (status, id_strings))
                conn.commit()

                verify_query = """
                    SELECT COUNT(*) as updated_count
                    FROM public.medical_exams
                    WHERE id = ANY(%s::uuid[]) AND status = %s AND deleted_at IS NULL
                """
                cursor.execute(verify_query, (id_strings, status))
                count_result = cursor.fetchone()
                updated_count = count_result["updated_count"] if count_result else 0

                logger.info(f"Bulk update completed: {updated_count} exams updated")
                return updated_count

        except Exception as e:
            logger.error(f"Error in bulk update status: {e}")
            raise Exception(f"Database error in bulk update: {str(e)}")

    
    async def get_exam_counts_by_status(
        self,
        organization_name: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, int]:

        logger.info(f"Fetching exam counts by status for organization: {organization_name}")

        try:
            organization_id = await self._get_organization_id_by_name(organization_name)
            if not organization_id:
                raise Exception(f"Organization '{organization_name}' not found or is deleted")

            async with db.get_async_connection() as conn:
                cursor = conn.cursor()

                conditions = ["organization_id = %s", "deleted_at IS NULL"]
                params = [str(organization_id)]

                if start_date:
                    conditions.append("requested_at >= %s")
                    params.append(start_date)
                if end_date:
                    conditions.append("requested_at <= %s")
                    params.append(end_date)

                where_clause = " AND ".join(conditions)

                query = f"""
                    SELECT status, COUNT(*) as count
                    FROM public.medical_exams
                    WHERE {where_clause}
                    GROUP BY status
                """
                cursor.execute(query, params)
                results = cursor.fetchall()

                counts = {row["status"]: row["count"] for row in results}
                for s in ["pending", "scheduled", "completed", "cancelled", "in_progress"]:
                    counts.setdefault(s, 0)

                logger.info(f"Exam counts fetched for organization {organization_name}")
                return counts

        except Exception as e:
            logger.error(f"Error fetching exam counts: {e}")
            raise Exception(f"Database error fetching exam counts: {str(e)}")

    
    async def get_upcoming_exams(
        self,
        organization_name: str,
        from_date: date,
        to_date: date,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:

        logger.info(f"Fetching upcoming exams for organization {organization_name} from {from_date} to {to_date}")

        try:
            organization_id = await self._get_organization_id_by_name(organization_name)
            if not organization_id:
                raise Exception(f"Organization '{organization_name}' not found or is deleted")

            async with db.get_async_connection() as conn:
                cursor = conn.cursor()

                conditions = [
                    "organization_id = %s",
                    "deleted_at IS NULL",
                    "requested_at >= %s",
                    "requested_at <= %s",
                ]
                params = [str(organization_id), from_date, to_date]

                where_clause = " AND ".join(conditions)

                count_query = f"""
                    SELECT COUNT(*) as total
                    FROM public.medical_exams
                    WHERE {where_clause}
                """
                cursor.execute(count_query, params)
                total_count = cursor.fetchone()["total"]

                offset = (page - 1) * page_size
                select_query = f"""
                    SELECT *
                    FROM public.medical_exams
                    WHERE {where_clause}
                    ORDER BY requested_at ASC
                    LIMIT %s OFFSET %s
                """
                cursor.execute(select_query, params + [page_size, offset])
                exams = cursor.fetchall()

                exams_list = [dict(exam) for exam in exams]
                total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1

                logger.info(f"Found {len(exams_list)} upcoming exams")
                return {
                    "exams": exams_list,
                    "total_count": total_count,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                }

        except Exception as e:
            logger.error(f"Error fetching upcoming exams: {e}")
            raise Exception(f"Database error fetching upcoming exams: {str(e)}")

    
    async def get_exams_without_patient(self, organization_name: str) -> List[Dict[str, Any]]:
        
        logger.info(f"Fetching exams without patient for organization: {organization_name}")

        try:
            organization_id = await self._get_organization_id_by_name(organization_name)
            if not organization_id:
                raise Exception(f"Organization '{organization_name}' not found or is deleted")

            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT *
                    FROM public.medical_exams
                    WHERE organization_id = %s
                      AND patient_id IS NULL
                      AND deleted_at IS NULL
                    ORDER BY requested_at DESC, created_at DESC
                """
                cursor.execute(query, (str(organization_id),))
                exams = cursor.fetchall()

                exams_list = [dict(exam) for exam in exams]
                logger.info(f"Found {len(exams_list)} exams without patient")
                return exams_list

        except Exception as e:
            logger.error(f"Error fetching exams without patient: {e}")
            raise Exception(f"Database error fetching exams: {str(e)}")

    
    async def get_patient_name_by_exam_id(self, exam_id: UUID) -> Optional[str]:
        
        logger.info(f"Fetching patient name for exam ID: {exam_id}")
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT p.name
                    FROM public.medical_exams e
                    LEFT JOIN public.patients p ON e.patient_id = p.id AND p.deleted_at IS NULL
                    WHERE e.id = %s AND e.deleted_at IS NULL
                """
                cursor.execute(query, (str(exam_id),))
                result = cursor.fetchone()
                if result:
                    return result['name']
                return None
        except Exception as e:
            logger.error(f"Error fetching patient name for exam {exam_id}: {e}")
            raise Exception(f"Database error fetching patient name: {str(e)}")



exam_service = ExamService()