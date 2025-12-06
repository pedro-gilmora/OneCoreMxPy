"""
AWS S3 service for file storage using LocalStack.
"""
import boto3
from botocore.exceptions import ClientError
from app.core.config import get_settings

settings = get_settings()


class S3Service:
    """Service class for S3 operations."""
    
    def __init__(self):
        """Initialize S3 client for LocalStack."""
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
        )
        self.bucket_name = settings.s3_bucket_name
    
    def ensure_bucket_exists(self) -> bool:
        """Create bucket if it doesn't exist."""
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
            return True
        except ClientError:
            try:
                self.client.create_bucket(Bucket=self.bucket_name)
                return True
            except ClientError as e:
                print(f"Error creating bucket: {e}")
                return False
    
    async def upload_file(
        self,
        file_content: bytes,
        s3_key: str,
        content_type: str = "text/csv"
    ) -> dict:
        """
        Upload a file to S3.
        
        Args:
            file_content: The file content as bytes
            s3_key: The key (path) where the file will be stored in S3
            content_type: The MIME type of the file
            
        Returns:
            Dict with upload result
        """
        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
            )
            return {
                "success": True,
                "bucket": self.bucket_name,
                "key": s3_key,
                "url": f"{settings.s3_endpoint_url}/{self.bucket_name}/{s3_key}"
            }
        except ClientError as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def download_file(self, s3_key: str) -> bytes | None:
        """
        Download a file from S3.
        
        Args:
            s3_key: The key (path) of the file in S3
            
        Returns:
            File content as bytes or None if error
        """
        try:
            response = self.client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return response["Body"].read()
        except ClientError:
            return None
    
    async def delete_file(self, s3_key: str) -> bool:
        """
        Delete a file from S3.
        
        Args:
            s3_key: The key (path) of the file in S3
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
        except ClientError:
            return False
    
    def get_file_url(self, s3_key: str) -> str:
        """Generate a URL for the file."""
        return f"{settings.s3_endpoint_url}/{self.bucket_name}/{s3_key}"


# Singleton instance
_s3_service: S3Service | None = None


def get_s3_service() -> S3Service:
    """Get or create S3 service instance."""
    global _s3_service
    if _s3_service is None:
        _s3_service = S3Service()
        _s3_service.ensure_bucket_exists()
    return _s3_service
