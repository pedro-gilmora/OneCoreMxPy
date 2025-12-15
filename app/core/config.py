"""
Application configuration using Pydantic Settings.
Loads configuration from environment variables and .env file.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = Field(default="OneCoreMxPy")
    app_version: str = Field(default="1.0.0")
    debug: bool = Field(default=False)
    
    # JWT Configuration
    jwt_secret_key: str = Field(...)
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=30)
    
    # Database Configuration
    db_server: str = Field(default=r"(localdb)\MSSQLLocalDB")
    db_name: str = Field(default="OneCoreMxPy")
    db_driver: str = Field(default="ODBC Driver 17 for SQL Server")
    db_user: str = Field(default="")  # Empty for Windows Auth (LocalDB)
    db_password: str = Field(default="")  # Empty for Windows Auth (LocalDB)
    
    # AWS S3 / LocalStack Configuration
    aws_access_key_id: str = Field(default="test")
    aws_secret_access_key: str = Field(default="test")
    aws_region: str = Field(default="us-east-1")
    s3_endpoint_url: str = Field(default="http://localhost:4566")
    s3_bucket_name: str = Field(default="onecoremxpy-bucket")
    
    # File Upload Configuration
    max_file_size_mb: int = Field(default=10)
    allowed_extensions: str = Field(default="csv")
    
    # Document Analysis Configuration
    document_allowed_extensions: str = Field(default="pdf,jpg,jpeg,png")
    max_document_size_mb: int = Field(default=20)
    
    # OpenAI Configuration (for Document Analysis)
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-4o")
    
    @property
    def database_url(self) -> str:
        """Generate the database connection URL for SQLAlchemy."""
        # Use SQL Server authentication if username/password provided
        if self.db_user and self.db_password:
            return (
                f"mssql+pyodbc://{self.db_user}:{self.db_password}@{self.db_server}/{self.db_name}"
                f"?driver={self.db_driver.replace(' ', '+')}&TrustServerCertificate=yes"
            )
        return (
            f"mssql+pyodbc://@{self.db_server}/{self.db_name}"
            f"?driver={self.db_driver.replace(' ', '+')}&TrustServerCertificate=yes"
        )
    
    @property
    def max_file_size_bytes(self) -> int:
        """Convert max file size from MB to bytes."""
        return self.max_file_size_mb * 1024 * 1024
    
    @property
    def allowed_extensions_list(self) -> list[str]:
        """Get allowed extensions as a list."""
        return [ext.strip().lower() for ext in self.allowed_extensions.split(",")]
    
    @property
    def document_allowed_extensions_list(self) -> list[str]:
        """Get allowed document extensions as a list."""
        return [ext.strip().lower() for ext in self.document_allowed_extensions.split(",")]
    
    @property
    def max_document_size_bytes(self) -> int:
        """Convert max document size from MB to bytes."""
        return self.max_document_size_mb * 1024 * 1024
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
