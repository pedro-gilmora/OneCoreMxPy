"""
Tests for Document Analysis Service.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.document_service import DocumentService, get_document_service
from app.schemas.schemas import DocumentTypeEnum


class TestDocumentService:
    """Test cases for DocumentService."""
    
    def test_get_content_type_pdf(self):
        """Test content type detection for PDF files."""
        service = DocumentService()
        assert service.get_content_type("test.pdf") == "application/pdf"
    
    def test_get_content_type_jpg(self):
        """Test content type detection for JPG files."""
        service = DocumentService()
        assert service.get_content_type("test.jpg") == "image/jpeg"
        assert service.get_content_type("test.jpeg") == "image/jpeg"
    
    def test_get_content_type_png(self):
        """Test content type detection for PNG files."""
        service = DocumentService()
        assert service.get_content_type("test.png") == "image/png"
    
    def test_get_content_type_unknown(self):
        """Test content type detection for unknown files."""
        service = DocumentService()
        assert service.get_content_type("test.xyz") == "application/octet-stream"
    
    def test_is_ai_available_without_key(self):
        """Test AI availability check when API key is not set."""
        with patch('app.services.document_service.settings') as mock_settings:
            mock_settings.openai_api_key = ""
            service = DocumentService()
            assert not service._is_ai_available()
    
    @pytest.mark.asyncio
    async def test_analyze_document_without_ai(self):
        """Test document analysis when AI is not available."""
        service = DocumentService()
        service.client = None  # Simulate no API key
        
        result = await service.analyze_document(
            file_content=b"test content",
            content_type="application/pdf",
            filename="test.pdf"
        )
        
        assert result.document_type == DocumentTypeEnum.PENDIENTE
        assert result.confidence == 0.0
        assert "not configured" in result.raw_text.lower()
    
    def test_encode_image_to_base64(self):
        """Test image encoding to base64."""
        service = DocumentService()
        test_content = b"test image content"
        
        result = service._encode_image_to_base64(test_content, "image/png")
        
        assert result.startswith("data:image/png;base64,")
    
    def test_classification_prompt(self):
        """Test that classification prompt contains expected keywords."""
        service = DocumentService()
        prompt = service._get_classification_prompt()
        
        assert "factura" in prompt.lower()
        assert "informacion" in prompt.lower()
        assert "json" in prompt.lower()
    
    def test_invoice_extraction_prompt(self):
        """Test that invoice extraction prompt contains expected keywords."""
        service = DocumentService()
        prompt = service._get_invoice_extraction_prompt()
        
        assert "cliente" in prompt.lower()
        assert "proveedor" in prompt.lower()
        assert "factura" in prompt.lower()
        assert "productos" in prompt.lower()
    
    def test_info_extraction_prompt(self):
        """Test that info extraction prompt contains expected keywords."""
        service = DocumentService()
        prompt = service._get_info_extraction_prompt()
        
        assert "descripción" in prompt.lower()
        assert "resumen" in prompt.lower()
        assert "sentimiento" in prompt.lower()


class TestGetDocumentService:
    """Test cases for get_document_service function."""
    
    def test_returns_document_service_instance(self):
        """Test that get_document_service returns a DocumentService instance."""
        service = get_document_service()
        assert isinstance(service, DocumentService)
    
    def test_returns_cached_instance(self):
        """Test that get_document_service returns the same cached instance."""
        service1 = get_document_service()
        service2 = get_document_service()
        assert service1 is service2
