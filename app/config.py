

import os
from dotenv import load_dotenv

load_dotenv()
class Config:
    DB_HOST = os.getenv('DB_HOST')
    DB_PORT = os.getenv('DB_PORT')
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_NAME = os.getenv('DB_NAME')
    DB_TIMEZONE = os.getenv('DB_TIMEZONE', 'UTC')

    DBX_HOST = os.getenv('DBX_HOST', os.getenv('DB_HOST'))  # Default to primary DB host if not specified
    DBX_PORT = os.getenv('DBX_PORT', os.getenv('DB_PORT'))  # Default to primary DB port if not specified
    DBX_USER = os.getenv('DBX_USER', os.getenv('DB_USER'))  # Default to primary DB user if not specified
    DBX_PASSWORD = os.getenv('DBX_PASSWORD', os.getenv('DB_PASSWORD'))  # Default to primary DB password if not specified
    DBX_NAME = os.getenv('DBX_NAME', 'medical_dbx')  # Default database name for secondary DB
    DBX_TIMEZONE = os.getenv('DBX_TIMEZONE', 'UTC')

    @property
    def DATABASE_URL(self):
        """Returns the primary database connection string"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        
    @property
    def DATABASE_URL_SECONDARY(self):
        """Returns the secondary database connection string"""
        return f"postgresql://{self.DBX_USER}:{self.DBX_PASSWORD}@{self.DBX_HOST}:{self.DBX_PORT}/{self.DBX_NAME}"
    
config = Config()
    
    
