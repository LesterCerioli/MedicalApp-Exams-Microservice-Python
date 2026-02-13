"""
Medical App Exams Microservice - Python


"""

__version__ = "1.0.0"
__author__ = "Medical App Team"
__description__ = "User management microservice with FastAPI and PostgreSQL"


from app.main import app
from app.config import config
from app.database import db
from .auth_service import AuthTokenService, auth_token_service


__all__ = [
    
    "AuthTokenService"
    
    
]
package_initialized = False

def initialize_package():
    """Initialize package components"""
    global package_initialized