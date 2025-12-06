"""
Pytest configuration and fixtures for tests.
"""
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def sample_csv_content():
    """Sample valid CSV content."""
    return b"name,precio,cantidad\nProduct A,100.50,10\nProduct B,200.00,5\n"


@pytest.fixture
def sample_csv_with_duplicates():
    """Sample CSV content with duplicate rows."""
    return b"name,precio,cantidad\nProduct A,100.50,10\nProduct B,200.00,5\nProduct A,100.50,10\n"


@pytest.fixture
def sample_csv_with_empty_values():
    """Sample CSV content with empty values."""
    return b"name,precio,cantidad\nProduct A,,10\nProduct B,200.00,\n"


@pytest.fixture
def sample_csv_with_invalid_types():
    """Sample CSV content with invalid types in numeric columns."""
    return b"name,precio,cantidad\nProduct A,not_a_number,10\nProduct B,200.00,five\n"


@pytest.fixture
def empty_csv_content():
    """Empty CSV with only headers."""
    return b"name,precio,cantidad\n"


@pytest.fixture
def csv_without_headers():
    """CSV content without headers."""
    return b""


@pytest.fixture
def mock_settings():
    """Mock settings for S3 service tests."""
    settings = MagicMock()
    settings.s3_endpoint_url = "http://localhost:4566"
    settings.aws_access_key_id = "test"
    settings.aws_secret_access_key = "test"
    settings.aws_region = "us-east-1"
    settings.s3_bucket_name = "test-bucket"
    return settings


@pytest.fixture
def mock_s3_client():
    """Mock S3 client."""
    return MagicMock()
