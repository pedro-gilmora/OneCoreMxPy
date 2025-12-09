"""
Tests for Event Service.
"""
import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from io import BytesIO
from sqlalchemy.orm import Session

from app.services.event_service import EventService, get_event_service
from app.schemas.schemas import EventTypeEnum, EventLogFilter
from app.models.models import EventLog


class TestEventService:
    """Test cases for EventService."""
    
    def test_create_event(self):
        """Test event creation."""
        service = EventService()
        mock_db = MagicMock(spec=Session)
        mock_event = MagicMock()
        
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()
        
        with patch.object(EventLog, '__init__', lambda self, **kwargs: None):
            result = service.create_event(
                db=mock_db,
                event_type=EventTypeEnum.DOCUMENT_UPLOAD,
                description="Test event",
                user_id=1,
                document_id=1,
                metadata={"test": "data"}
            )
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    def test_log_document_upload(self):
        """Test logging document upload event."""
        service = EventService()
        mock_db = MagicMock(spec=Session)
        
        with patch.object(service, 'create_event') as mock_create:
            service.log_document_upload(
                db=mock_db,
                document_id=1,
                filename="test.pdf",
                user_id=1
            )
            
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args.kwargs['event_type'] == EventTypeEnum.DOCUMENT_UPLOAD
            assert "test.pdf" in call_args.kwargs['description']
    
    def test_log_ai_analysis_success(self):
        """Test logging successful AI analysis event."""
        service = EventService()
        mock_db = MagicMock(spec=Session)
        
        with patch.object(service, 'create_event') as mock_create:
            service.log_ai_analysis(
                db=mock_db,
                document_id=1,
                document_type="factura",
                user_id=1,
                success=True
            )
            
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args.kwargs['event_type'] == EventTypeEnum.AI_ANALYSIS
            assert "completado" in call_args.kwargs['description'].lower()
    
    def test_log_ai_analysis_failure(self):
        """Test logging failed AI analysis event."""
        service = EventService()
        mock_db = MagicMock(spec=Session)
        
        with patch.object(service, 'create_event') as mock_create:
            service.log_ai_analysis(
                db=mock_db,
                document_id=1,
                document_type="unknown",
                user_id=1,
                success=False,
                error="Test error"
            )
            
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert "error" in call_args.kwargs['description'].lower()
    
    def test_log_user_interaction(self):
        """Test logging user interaction event."""
        service = EventService()
        mock_db = MagicMock(spec=Session)
        
        with patch.object(service, 'create_event') as mock_create:
            service.log_user_interaction(
                db=mock_db,
                action="Test action",
                user_id=1,
                document_id=1,
                details={"key": "value"}
            )
            
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args.kwargs['event_type'] == EventTypeEnum.USER_INTERACTION
    
    def test_log_system_event(self):
        """Test logging system event."""
        service = EventService()
        mock_db = MagicMock(spec=Session)
        
        with patch.object(service, 'create_event') as mock_create:
            service.log_system_event(
                db=mock_db,
                description="System event test",
                metadata={"status": "ok"}
            )
            
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args.kwargs['event_type'] == EventTypeEnum.SYSTEM
    
    def test_event_to_response(self):
        """Test converting event model to response schema."""
        service = EventService()
        mock_db = MagicMock(spec=Session)
        
        # Create mock event
        mock_event = MagicMock()
        mock_event.id = 1
        mock_event.event_type = "subida_documento"
        mock_event.description = "Test description"
        mock_event.document_id = 1
        mock_event.user_id = 1
        mock_event.metadata_json = json.dumps({"test": "data"})
        mock_event.created_at = datetime.utcnow()
        
        # Create mock user
        mock_user = MagicMock()
        mock_user.username = "testuser"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        result = service.event_to_response(mock_event, mock_db)
        
        assert result.id == 1
        assert result.event_type == "subida_documento"
        assert result.username == "testuser"
        assert result.metadata == {"test": "data"}
    
    def test_event_to_response_no_user(self):
        """Test converting event model without user."""
        service = EventService()
        mock_db = MagicMock(spec=Session)
        
        mock_event = MagicMock()
        mock_event.id = 1
        mock_event.event_type = "sistema"
        mock_event.description = "System event"
        mock_event.document_id = None
        mock_event.user_id = None
        mock_event.metadata_json = None
        mock_event.created_at = datetime.utcnow()
        
        result = service.event_to_response(mock_event, mock_db)
        
        assert result.username is None
        assert result.metadata is None


class TestEventLogFilter:
    """Test cases for EventLogFilter."""
    
    def test_filter_with_all_fields(self):
        """Test filter with all fields populated."""
        filter_obj = EventLogFilter(
            event_type=EventTypeEnum.DOCUMENT_UPLOAD,
            description_search="test",
            date_from=datetime(2024, 1, 1),
            date_to=datetime(2024, 12, 31),
            user_id=1
        )
        
        assert filter_obj.event_type == EventTypeEnum.DOCUMENT_UPLOAD
        assert filter_obj.description_search == "test"
        assert filter_obj.user_id == 1
    
    def test_filter_with_no_fields(self):
        """Test filter with no fields populated."""
        filter_obj = EventLogFilter()
        
        assert filter_obj.event_type is None
        assert filter_obj.description_search is None
        assert filter_obj.date_from is None
        assert filter_obj.date_to is None
        assert filter_obj.user_id is None


class TestGetEventService:
    """Test cases for get_event_service function."""
    
    def test_returns_event_service_instance(self):
        """Test that get_event_service returns an EventService instance."""
        service = get_event_service()
        assert isinstance(service, EventService)
    
    def test_returns_cached_instance(self):
        """Test that get_event_service returns the same cached instance."""
        service1 = get_event_service()
        service2 = get_event_service()
        assert service1 is service2
