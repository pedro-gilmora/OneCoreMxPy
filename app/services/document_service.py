"""
Document Analysis Service using OpenAI for AI-powered document classification and data extraction.
"""
import json
import base64
import io
from typing import Optional, Tuple
from functools import lru_cache

from openai import OpenAI
from PIL import Image
import PyPDF2

from app.core.config import get_settings
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
    """Service class for document analysis using OpenAI."""
    
    def __init__(self):
        """Initialize OpenAI client."""
        self.client = None
        if settings.openai_api_key:
            self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
    
    def _is_ai_available(self) -> bool:
        """Check if AI service is available."""
        return self.client is not None and settings.openai_api_key
    
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
        filename: str
    ) -> DocumentAnalysisResult:
        """
        Analyze a document using OpenAI to classify and extract data.
        
        Args:
            file_content: The document content as bytes
            content_type: MIME type of the document
            filename: Original filename
            
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
            messages = [
                {"role": "system", "content": self._get_classification_prompt()}
            ]
            
            if is_image:
                # Use vision API for images
                base64_image = self._encode_image_to_base64(file_content, content_type)
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Clasifica este documento:"},
                        {"type": "image_url", "image_url": {"url": base64_image}}
                    ]
                })
            else:
                # Use text for PDFs
                messages.append({
                    "role": "user",
                    "content": f"Clasifica este documento:\n\n{raw_text[:4000]}"
                })
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=200,
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
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
            messages = [
                {"role": "system", "content": self._get_invoice_extraction_prompt()}
            ]
            
            if is_image:
                base64_image = self._encode_image_to_base64(file_content, content_type)
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extrae los datos de esta factura:"},
                        {"type": "image_url", "image_url": {"url": base64_image}}
                    ]
                })
            else:
                messages.append({
                    "role": "user",
                    "content": f"Extrae los datos de esta factura:\n\n{raw_text[:8000]}"
                })
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=2000,
                temperature=0.1
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
            messages = [
                {"role": "system", "content": self._get_info_extraction_prompt()}
            ]
            
            if is_image:
                base64_image = self._encode_image_to_base64(file_content, content_type)
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analiza este documento:"},
                        {"type": "image_url", "image_url": {"url": base64_image}}
                    ]
                })
            else:
                messages.append({
                    "role": "user",
                    "content": f"Analiza este documento:\n\n{raw_text[:8000]}"
                })
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=2000,
                temperature=0.3
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


@lru_cache()
def get_document_service() -> DocumentService:
    """Get cached document service instance."""
    return DocumentService()
