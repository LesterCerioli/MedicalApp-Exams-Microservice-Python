import random
import uuid
import string
from datetime import datetime, date
from typing import Optional, Dict, Any, List
import logging
from app.database import db_primary, db_secondary

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClinicalExamService:
    def __init__(self):
        """Initialize the clinical exam service with multiple database connections."""
        self._create_exam_orders_table_if_not_exists()
    
    def _get_organization_id_by_name(self, organization_name: str) -> Optional[uuid.UUID]:
        """Convert organization name to organization ID."""
        try:
            query = """
                SELECT id FROM public.organizations 
                WHERE name = %s AND deleted_at IS NULL
            """
            results = db_primary.execute_query(query, (organization_name,))
            return results[0]['id'] if results else None
        except Exception as e:
            logger.error(f"Error finding organization by name: {e}")
            raise
    
    def _get_doctor_id_by_identifier(self, identifier: str, organization_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Convert CRM or DEA identifier to doctor ID.
        
        Args:
            identifier: CRM registry (Brazil) or DEA registration (USA)
            organization_id: Organization UUID
            
        Returns:
            Doctor dictionary with ID or None if not found
        """
        try:
            # First try to find by CRM (Brazilian doctors)
            query_crm = """
                SELECT id, full_name, crm_registry, dea_registration
                FROM public.doctors 
                WHERE crm_registry = %s AND organization_id = %s AND deleted_at IS NULL
            """
            results_crm = db_primary.execute_query(query_crm, (identifier, str(organization_id)))
            
            if results_crm:
                logger.info(f"Doctor found by CRM: {identifier}")
                doctor = results_crm[0]
                doctor['registry_type'] = 'CRM'
                return doctor
            
            # If not found by CRM, try by DEA registration (USA doctors)
            query_dea = """
                SELECT id, full_name, crm_registry, dea_registration
                FROM public.doctors 
                WHERE dea_registration = %s AND organization_id = %s AND deleted_at IS NULL
            """
            results_dea = db_primary.execute_query(query_dea, (identifier, str(organization_id)))
            
            if results_dea:
                logger.info(f"Doctor found by DEA registration: {identifier}")
                doctor = results_dea[0]
                doctor['registry_type'] = 'DEA'
                return doctor
            
            logger.warning(f"Doctor not found by CRM or DEA: {identifier}")
            return None
            
        except Exception as e:
            logger.error(f"Error finding doctor by identifier: {e}")
            raise
    
    def _get_patient_id_by_identifier(self, identifier: str, organization_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Convert CPF or SSN identifier to patient ID.
        
        Args:
            identifier: CPF number (Brazil) or SSN (USA)
            organization_id: Organization UUID
            
        Returns:
            Patient dictionary with ID or None if not found
        """
        try:
            # First try to find by CPF (Brazilian patients)
            query_cpf = """
                SELECT id, name, cpf, ssn
                FROM public.patients 
                WHERE cpf = %s AND organization_id = %s AND deleted_at IS NULL
            """
            results_cpf = db_primary.execute_query(query_cpf, (identifier, organization_id))
            
            if results_cpf:
                logger.info(f"Patient found by CPF: {identifier}")
                patient = results_cpf[0]
                patient['identifier_type'] = 'CPF'
                return patient
            
            # If not found by CPF, try by SSN (USA patients)
            query_ssn = """
                SELECT id, name, cpf, ssn
                FROM public.patients 
                WHERE ssn = %s AND organization_id = %s AND deleted_at IS NULL
            """
            results_ssn = db_primary.execute_query(query_ssn, (identifier, organization_id))
            
            if results_ssn:
                logger.info(f"Patient found by SSN: {identifier}")
                patient = results_ssn[0]
                patient['identifier_type'] = 'SSN'
                return patient
            
            logger.warning(f"Patient not found by CPF or SSN: {identifier}")
            return None
            
        except Exception as e:
            logger.error(f"Error finding patient by identifier: {e}")
            raise

    def _create_exam_orders_table_if_not_exists(self):
        """Create exam_orders table in secondary database if it doesn't exist."""
        create_table_query = """
            CREATE TABLE IF NOT EXISTS public.exam_orders (
                id UUID PRIMARY KEY,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMPTZ,
                organization_id UUID NOT NULL,
                doctor_id UUID NOT NULL,
                patient_id UUID NOT NULL,
                exam_name TEXT NOT NULL,
                exam_description TEXT,
                emission_date DATE NOT NULL,
                additional_details TEXT,
                status TEXT DEFAULT 'PENDING',
                priority TEXT DEFAULT 'ROUTINE',
                exam_number_identification TEXT UNIQUE
            )
        """
        
        create_index_queries = [
            "CREATE INDEX IF NOT EXISTS idx_exam_orders_doctor_id ON public.exam_orders(doctor_id)",
            "CREATE INDEX IF NOT EXISTS idx_exam_orders_patient_id ON public.exam_orders(patient_id)",
            "CREATE INDEX IF NOT EXISTS idx_exam_orders_organization_id ON public.exam_orders(organization_id)",
            "CREATE INDEX IF NOT EXISTS idx_exam_orders_status ON public.exam_orders(status)",
            "CREATE INDEX IF NOT EXISTS idx_exam_orders_emission_date ON public.exam_orders(emission_date)",
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_exam_orders_exam_number ON public.exam_orders(exam_number_identification)"
        ]
        
        try:
            # Create table in secondary database
            db_secondary.execute_query(create_table_query, fetch=False)
            
            # Create indexes in secondary database
            for index_query in create_index_queries:
                db_secondary.execute_query(index_query, fetch=False)
                
            logger.info("Exam orders table created or verified successfully in secondary database")
        except Exception as e:
            logger.error(f"Error creating exam orders table: {e}")
            raise

    def _generate_exam_number_identification(self) -> str:
        """
        Generate a unique alphanumeric exam number identification.
        Format: 20 characters (alphabetic + numeric)
        
        Returns:
            Generated exam number identification string
        """
        # Generate 20-character alphanumeric string
        characters = string.ascii_uppercase + string.digits
        exam_number = ''.join(random.choice(characters) for _ in range(20))
        
        # Verify uniqueness
        try:
            with db_secondary.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT COUNT(*) FROM public.exam_orders WHERE exam_number_identification = %s",
                        (exam_number,)
                    )
                    result = cursor.fetchone()
                    if result['count'] > 0:
                        logger.warning("Exam number collision detected, regenerating...")
                        return self._generate_exam_number_identification()
            
            return exam_number
        except Exception as e:
            logger.error(f"Error generating exam number: {e}")
            # Fallback: return generated number without uniqueness check
            return exam_number
    
    def create_exam_order(
        self,
        doctor_identifier: str,
        patient_identifier: str,
        organization_name: str,
        exam_name: str,
        emission_date: str,
        additional_details: Optional[str] = None,
        exam_description: Optional[str] = None,
        priority: str = "ROUTINE",
        exam_number_identification: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new clinical exam order.
        
        CONVERTS:
        - organization_name → organization_id
        - doctor_identifier (CRM/DEA) → doctor_id
        - patient_identifier (CPF/SSN) → patient_id
        
        Args:
            doctor_identifier: Doctor's CRM registry (Brazil) or DEA registration (USA)
            patient_identifier: Patient's CPF number (Brazil) or SSN (USA)
            organization_name: Organization name
            exam_name: Name of the exam
            emission_date: Date of exam order emission (YYYY-MM-DD)
            additional_details: Additional details about the exam order
            exam_description: Description of the exam
            priority: Priority level (ROUTINE, URGENT, EMERGENCY)
            exam_number_identification: Optional custom exam number
            
        Returns:
            Dictionary containing the created exam order details
            
        Raises:
            ValueError: If organization, doctor or patient not found
        """
        try:
            # Convert organization_name to organization_id
            organization_id = self._get_organization_id_by_name(organization_name)
            if not organization_id:
                raise ValueError(f"Organization with name '{organization_name}' not found")
            
            # Convert doctor_identifier to doctor_id
            doctor = self._get_doctor_id_by_identifier(doctor_identifier, organization_id)
            if not doctor:
                raise ValueError(f"Doctor with identifier '{doctor_identifier}' not found in organization '{organization_name}'")
            
            # Convert patient_identifier to patient_id
            patient = self._get_patient_id_by_identifier(patient_identifier, organization_id)
            if not patient:
                raise ValueError(f"Patient with identifier '{patient_identifier}' not found in organization '{organization_name}'")
            
            # Validate and parse emission date
            emission_date_obj = datetime.strptime(emission_date, '%Y-%m-%d').date()
            
            # Generate or validate exam number identification
            if exam_number_identification is None:
                exam_number_identification = self._generate_exam_number_identification()
            else:
                existing_order = self.get_exam_order_by_exam_number(exam_number_identification)
                if existing_order:
                    raise ValueError(f"Exam number '{exam_number_identification}' already exists")
            
            logger.info(f"Using exam number: {exam_number_identification}")
            
            # Create exam order in secondary database
            exam_order_id = uuid.uuid4()
            current_time = datetime.now()
            
            # Add registry/identifier types to additional details for tracking
            doctor_info = f"Doctor registry: {doctor['registry_type']} - {doctor_identifier}"
            patient_info = f"Patient identifier: {patient['identifier_type']} - {patient_identifier}"
            exam_number_info = f"Exam Number: {exam_number_identification}"
            
            registry_details = f"{exam_number_info}\n{doctor_info}\n{patient_info}"
            final_additional_details = additional_details
            if additional_details:
                final_additional_details = f"{registry_details}\n{additional_details}"
            else:
                final_additional_details = registry_details
            
            query = """
                INSERT INTO public.exam_orders 
                (id, created_at, updated_at, organization_id, doctor_id, patient_id, 
                 exam_name, exam_description, emission_date, additional_details, priority,
                 exam_number_identification)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            success = db_secondary.execute_query(
                query,
                (exam_order_id, current_time, current_time, organization_id, 
                 doctor['id'], patient['id'], exam_name, exam_description, 
                 emission_date_obj, final_additional_details, priority,
                 exam_number_identification),
                fetch=False
            )
            
            if success:
                # Retrieve the complete exam order details
                exam_order = self.get_exam_order_by_exam_number(exam_number_identification)
                logger.info(f"Exam order created successfully with number: {exam_number_identification}")
                return exam_order
            else:
                raise Exception("Failed to create exam order")
            
        except ValueError as e:
            logger.error(f"Invalid input: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating exam order: {e}")
            raise
    
    def get_exam_order_by_exam_number(self, exam_number_identification: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve exam order by exam number identification from secondary database.
        
        Args:
            exam_number_identification: Unique exam number string
            
        Returns:
            Dictionary with exam order details
        """
        try:
            query = """
                SELECT 
                    eo.id,
                    eo.created_at,
                    eo.updated_at,
                    eo.organization_id,
                    eo.doctor_id,
                    eo.patient_id,
                    eo.exam_name,
                    eo.exam_description,
                    eo.emission_date,
                    eo.additional_details,
                    eo.status,
                    eo.priority,
                    eo.exam_number_identification
                FROM public.exam_orders eo
                WHERE eo.exam_number_identification = %s AND eo.deleted_at IS NULL
            """
            results = db_secondary.execute_query(query, (exam_number_identification,))
            return results[0] if results else None
            
        except Exception as e:
            logger.error(f"Error retrieving exam order by exam number: {e}")
            raise

def main():
    """Example usage of the ClinicalExamService."""
    exam_service = ClinicalExamService()
    
    try:
        # Create an exam order using human-readable identifiers
        exam_order = exam_service.create_exam_order(
            doctor_identifier="CRM12345",           # CRM registry
            patient_identifier="123.456.789-00",    # CPF number
            organization_name="Hospital Albert Einstein",  # Organization name
            exam_name="Complete Blood Count",
            emission_date="2024-01-15",
            additional_details="Fasting required for 12 hours before the test",
            exam_description="Complete blood count with differential",
            priority="ROUTINE"
        )
        
        print("Exam Order Created Successfully:")
        for key, value in exam_order.items():
            print(f"{key}: {value}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()