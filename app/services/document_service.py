"""
Document Analysis Service using OpenAI for AI-powered document classification and data extraction.
"""
import json
import base64
import io
from typing import Optional, Tuple
from functools import lru_cache

from openai import AsyncOpenAI
from PIL import Image
import PyPDF2

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.models import Document, InvoiceData, InfoData
from app.schemas.schemas import (
    DocumentTypeEnum,
    DocumentAnalysisResult,
    InvoiceDataBase,
    InfoDataBase,
    InvoiceProduct,
    SentimentEnum,
)

settings = get_settings()


class DocumentService:
    """Service class for document analysis using Microsoft Semantic Kernel."""
    
    def __init__(self):
        """Initialize OpenAI client."""
        self.client = None
        # Use model from settings, fallback to gpt-4o-mini
        self.model = settings.openai_model if settings.openai_model else "gpt-4o-mini"
        
        if settings.openai_api_key:
            try:
                self.client = AsyncOpenAI(api_key=settings.openai_api_key)
            except Exception as e:
                print(f"Warning: Failed to initialize OpenAI client: {e}")
                self.client = None
        
        self.db = SessionLocal()
    
    def _is_ai_available(self) -> bool:
        """Check if AI service is available."""
        return self.client is not None and settings.openai_api_key
    
    def _save_to_database(self, document: Document):
        """Save or update document in database."""
        try:
            self.db.merge(document)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"Error saving document to database: {e}")
    
    def _get_document_by_s3_key(self, s3_key: str) -> Optional[Document]:
        """Retrieve document from database by S3 key."""
        try:
            from app.models.models import Document as DocumentModel
            return self.db.query(DocumentModel).filter(DocumentModel.s3_key == s3_key).first()
        except Exception as e:
            print(f"Error retrieving document: {e}")
            return None
    
    def get_all_documents(self, user_id: int = None) -> list:
        """Retrieve all documents from database, optionally filtered by user."""
        try:
            from app.models.models import Document as DocumentModel
            query = self.db.query(DocumentModel)
            if user_id:
                query = query.filter(DocumentModel.user_id == user_id)
            return query.all()
        except Exception as e:
            print(f"Error retrieving documents: {e}")
            return []
    
    def get_document_by_id(self, doc_id: int) -> Optional[Document]:
        """Retrieve specific document from database by ID."""
        try:
            from app.models.models import Document as DocumentModel
            return self.db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
        except Exception as e:
            print(f"Error retrieving document by ID: {e}")
            return None
    
    def query_invoices(self, user_id: int = None) -> list:
        """Query all invoices from database, optionally filtered by user."""
        try:
            from app.models.models import Document as DocumentModel, InvoiceData
            query = self.db.query(InvoiceData).join(DocumentModel)
            if user_id:
                query = query.filter(DocumentModel.user_id == user_id)
            return query.all()
        except Exception as e:
            print(f"Error querying invoices: {e}")
            return []
    
    def query_info_documents(self, user_id: int = None) -> list:
        """Query all information documents from database, optionally filtered by user."""
        try:
            from app.models.models import Document as DocumentModel, InfoData
            query = self.db.query(InfoData).join(DocumentModel)
            if user_id:
                query = query.filter(DocumentModel.user_id == user_id)
            return query.all()
        except Exception as e:
            print(f"Error querying info documents: {e}")
            return []
    
    def _extract_text_from_pdf(self, file_content: bytes) -> str:
        """Extract text content from PDF file."""
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
            return text.strip()
        except Exception as e:
            print(f"Error extracting PDF text: {e}")
            return ""
    
    def _encode_image_to_base64(self, file_content: bytes, content_type: str) -> str:
        """Encode image to base64 for OpenAI Vision API."""
        base64_image = base64.b64encode(file_content).decode('utf-8')
        return f"data:{content_type};base64,{base64_image}"
    
    def _get_classification_prompt(self) -> str:
        """Get the prompt for document classification."""
        return """Analiza el siguiente documento y clasifícalo en una de estas categorías:

1. "factura" - Si el documento contiene datos económicos/financieros como:
   - Montos, precios, totales
   - Números de factura
   - Información de cliente y proveedor
   - Listado de productos o servicios con precios

2. "informacion" - Si el documento contiene texto general como:
   - Cartas, memorándums
   - Documentos informativos
   - Reportes sin datos financieros detallados
   - Cualquier documento que no sea una factura

Responde ÚNICAMENTE con un JSON en el siguiente formato:
{
    "document_type": "factura" o "informacion",
    "confidence": 0.0 a 1.0
}
"""
    
    def _get_invoice_extraction_prompt(self) -> str:
        """Get the prompt for invoice data extraction."""
        return """Extrae los siguientes datos de esta factura:

1. Información del Cliente:
   - Nombre del cliente
   - Dirección del cliente

2. Información del Proveedor:
   - Nombre del proveedor
   - Dirección del proveedor

3. Detalles de la Factura:
   - Número de factura
   - Fecha de la factura
   - Total de la factura
   - Moneda (si se indica, por defecto MXN)

4. Productos/Servicios (lista de items):
   - Cantidad
   - Nombre/Descripción
   - Precio unitario
   - Total del item

Responde ÚNICAMENTE con un JSON en el siguiente formato:
{
    "client_name": "nombre o null",
    "client_address": "dirección o null",
    "provider_name": "nombre o null",
    "provider_address": "dirección o null",
    "invoice_number": "número o null",
    "invoice_date": "fecha como string o null",
    "invoice_total": número o null,
    "currency": "MXN" u otra moneda,
    "products": [
        {
            "quantity": número o null,
            "name": "nombre del producto",
            "unit_price": número o null,
            "total": número o null
        }
    ]
}

Si no puedes extraer algún dato, usa null. Asegúrate de que los números sean valores numéricos, no strings.
"""
    
    def _get_info_extraction_prompt(self) -> str:
        """Get the prompt for information document extraction."""
        return """Analiza este documento informativo y extrae:

1. Descripción: Una descripción breve del contenido del documento (1-2 oraciones)
2. Resumen: Un resumen más detallado del contenido (3-5 oraciones)
3. Análisis de Sentimiento:
   - Tipo: "positivo", "negativo" o "neutral"
   - Score: Un valor de -1.0 (muy negativo) a 1.0 (muy positivo)
4. Temas Clave: Lista de los temas principales del documento

Responde ÚNICAMENTE con un JSON en el siguiente formato:
{
    "description": "descripción breve",
    "summary": "resumen detallado",
    "sentiment": "positivo", "negativo" o "neutral",
    "sentiment_score": número de -1.0 a 1.0,
    "key_topics": ["tema1", "tema2", "tema3"]
}
"""
    
    async def analyze_document(
        self,
        file_content: bytes,
        content_type: str,
        filename: str,
        s3_key: str = None,
        user_id: int = None
    ) -> DocumentAnalysisResult:
        """
        Analyze a document using Semantic Kernel to classify and extract data.
        Results are stored in the SQL database.
        
        Args:
            file_content: The document content as bytes
            content_type: MIME type of the document
            filename: Original filename
            s3_key: S3 key for file location
            user_id: User ID who uploaded the document
            
        Returns:
            DocumentAnalysisResult with classification and extracted data
        """
        if not self._is_ai_available():
            # Return a default result if AI is not configured
            return DocumentAnalysisResult(
                document_type=DocumentTypeEnum.PENDIENTE,
                confidence=0.0,
                raw_text="AI service not configured. Please set OPENAI_API_KEY.",
                invoice_data=None,
                info_data=None
            )
        
        # Extract text or prepare image for analysis
        raw_text = ""
        is_image = content_type.startswith("image/")
        
        if content_type == "application/pdf":
            raw_text = self._extract_text_from_pdf(file_content)
        
        # Step 1: Classify the document
        doc_type, confidence = await self._classify_document(
            file_content, content_type, raw_text, is_image
        )
        
        # Step 2: Extract data based on classification
        invoice_data = None
        info_data = None
        
        if doc_type == DocumentTypeEnum.FACTURA:
            invoice_data, extraction_text = await self._extract_invoice_data(
                file_content, content_type, raw_text, is_image
            )
            raw_text = extraction_text or raw_text
        else:
            info_data, extraction_text = await self._extract_info_data(
                file_content, content_type, raw_text, is_image
            )
            raw_text = extraction_text or raw_text
        
        # Step 3: Save to database
        if s3_key:
            try:
                from app.models.models import Document as DocumentModel
                from app.models.models import InvoiceData as InvoiceDataModel
                from app.models.models import InfoData as InfoDataModel
                from app.models.models import InvoiceProduct as InvoiceProductModel
                from datetime import datetime
                
                document = DocumentModel(
                    filename=filename,
                    original_filename=filename,
                    s3_key=s3_key,
                    file_size=len(file_content),
                    content_type=content_type,
                    document_type=doc_type.value,
                    analysis_status="completed",
                    user_id=user_id
                )
                
                self.db.add(document)
                self.db.flush()  # Flush to get the document ID
                
                # If invoice data, save to database
                if invoice_data:
                    inv = InvoiceDataModel(
                        document_id=document.id,
                        client_name=invoice_data.client_name,
                        client_address=invoice_data.client_address,
                        provider_name=invoice_data.provider_name,
                        provider_address=invoice_data.provider_address,
                        invoice_number=invoice_data.invoice_number,
                        invoice_date=invoice_data.invoice_date,
                        invoice_total=invoice_data.invoice_total,
                        currency=invoice_data.currency,
                        products_json=json.dumps([p.dict() for p in invoice_data.products]) if invoice_data.products else "[]",
                        raw_text=raw_text
                    )
                    self.db.add(inv)
                
                # If info data, save to database
                if info_data:
                    info = InfoDataModel(
                        document_id=document.id,
                        description=info_data.description,
                        summary=info_data.summary,
                        sentiment=info_data.sentiment,
                        sentiment_score=info_data.sentiment_score,
                        key_topics_json=json.dumps(info_data.key_topics) if info_data.key_topics else "[]",
                        raw_text=raw_text
                    )
                    self.db.add(info)
                
                self.db.commit()
                    
            except Exception as e:
                self.db.rollback()
                print(f"Error saving analysis results to database: {e}")
        
        return DocumentAnalysisResult(
            document_type=doc_type,
            confidence=confidence,
            invoice_data=invoice_data,
            info_data=info_data,
            raw_text=raw_text
        )
    
    async def _classify_document(
        self,
        file_content: bytes,
        content_type: str,
        raw_text: str,
        is_image: bool
    ) -> Tuple[DocumentTypeEnum, float]:
        """Classify the document type using OpenAI."""
        try:
            # Build the prompt with document content
            system_prompt = self._get_classification_prompt()
            
            if is_image:
                base64_image = self._encode_image_to_base64(file_content, content_type)
                user_message = f"Clasifica este documento:\n\n{base64_image}"
            else:
                user_message = f"Clasifica este documento:\n\n{raw_text[:4000]}"
            
            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean up the response if it contains markdown code blocks
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            
            result = json.loads(result_text)
            doc_type = DocumentTypeEnum(result.get("document_type", "informacion"))
            confidence = float(result.get("confidence", 0.5))
            
            return doc_type, confidence
            
        except Exception as e:
            print(f"Error classifying document: {e}")
            return DocumentTypeEnum.INFORMACION, 0.0
    
    async def _extract_invoice_data(
        self,
        file_content: bytes,
        content_type: str,
        raw_text: str,
        is_image: bool
    ) -> Tuple[Optional[InvoiceDataBase], str]:
        """Extract invoice data using OpenAI."""
        try:
            system_prompt = self._get_invoice_extraction_prompt()
            
            if is_image:
                base64_image = self._encode_image_to_base64(file_content, content_type)
                user_message = f"Extrae los datos de esta factura:\n\n{base64_image}"
            else:
                user_message = f"Extrae los datos de esta factura:\n\n{raw_text[:8000]}"
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean up the response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            
            result = json.loads(result_text)
            
            # Parse products
            products = []
            for p in result.get("products", []):
                products.append(InvoiceProduct(
                    quantity=p.get("quantity"),
                    name=p.get("name"),
                    unit_price=p.get("unit_price"),
                    total=p.get("total")
                ))
            
            invoice_data = InvoiceDataBase(
                client_name=result.get("client_name"),
                client_address=result.get("client_address"),
                provider_name=result.get("provider_name"),
                provider_address=result.get("provider_address"),
                invoice_number=result.get("invoice_number"),
                invoice_date=result.get("invoice_date"),
                invoice_total=result.get("invoice_total"),
                currency=result.get("currency", "MXN"),
                products=products
            )
            
            return invoice_data, raw_text
            
        except Exception as e:
            print(f"Error extracting invoice data: {e}")
            return None, raw_text
    
    async def _extract_info_data(
        self,
        file_content: bytes,
        content_type: str,
        raw_text: str,
        is_image: bool
    ) -> Tuple[Optional[InfoDataBase], str]:
        """Extract information document data using OpenAI."""
        try:
            system_prompt = self._get_info_extraction_prompt()
            
            if is_image:
                base64_image = self._encode_image_to_base64(file_content, content_type)
                user_message = f"Analiza este documento:\n\n{base64_image}"
            else:
                user_message = f"Analiza este documento:\n\n{raw_text[:8000]}"
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean up the response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            
            result = json.loads(result_text)
            
            info_data = InfoDataBase(
                description=result.get("description"),
                summary=result.get("summary"),
                sentiment=result.get("sentiment"),
                sentiment_score=result.get("sentiment_score"),
                key_topics=result.get("key_topics", [])
            )
            
            return info_data, raw_text
            
        except Exception as e:
            print(f"Error extracting info data: {e}")
            return None, raw_text
    
    def get_content_type(self, filename: str) -> str:
        """Get MIME type based on file extension."""
        ext = filename.rsplit(".", 1)[-1].lower()
        content_types = {
            "pdf": "application/pdf",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png"
        }
        return content_types.get(ext, "application/octet-stream")
    
    def close(self):
        """Close database session."""
        if self.db:
            self.db.close()
    
    def __del__(self):
        """Cleanup when service is destroyed."""
        self.close()


@lru_cache()
def get_document_service() -> DocumentService:
    """Get cached document service instance."""
    return DocumentService()
