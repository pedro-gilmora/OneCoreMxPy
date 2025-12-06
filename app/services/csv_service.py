"""
CSV processing and validation service.
"""
import csv
import hashlib
import io
from typing import List, Tuple, Dict, Any
from app.schemas.schemas import ValidationResult


class CSVService:
    """Service for CSV file processing and validation."""
    
    def __init__(self):
        self.numeric_columns = {"precio", "cantidad", "monto", "total", "price", "quantity", "amount"}
    
    def validate_and_process(
        self, 
        file_content: bytes, 
        filename: str
    ) -> Tuple[List[Dict[str, Any]], List[ValidationResult]]:
        """
        Validate and process CSV file content.
        
        Returns:
            Tuple of (parsed_rows, validation_results)
        """
        validations: List[ValidationResult] = []
        rows: List[Dict[str, Any]] = []
        
        try:
            # Decode content
            try:
                content = file_content.decode("utf-8")
            except UnicodeDecodeError:
                content = file_content.decode("latin-1")
            
            # Parse CSV
            reader = csv.DictReader(io.StringIO(content))
            
            if not reader.fieldnames:
                validations.append(ValidationResult(
                    validation_type="structure_error",
                    message="El archivo CSV no tiene encabezados",
                    severity="error"
                ))
                return rows, validations
            
            # Track duplicates using row hash
            seen_hashes: Dict[str, int] = {}
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
                rows.append(row)
                
                # Check for duplicate rows
                row_hash = self._compute_row_hash(row)
                if row_hash in seen_hashes:
                    validations.append(ValidationResult(
                        validation_type="duplicate_row",
                        row_number=row_num,
                        message=f"Fila duplicada (igual a fila {seen_hashes[row_hash]})",
                        severity="warning"
                    ))
                else:
                    seen_hashes[row_hash] = row_num
                
                # Validate each column
                for col_name, value in row.items():
                    # Check for empty values
                    if value is None or str(value).strip() == "":
                        validations.append(ValidationResult(
                            validation_type="empty_value",
                            row_number=row_num,
                            column_name=col_name,
                            message=f"Valor vacío en columna '{col_name}'",
                            severity="warning"
                        ))
                        continue
                    
                    # Check for type validation on numeric columns
                    if col_name.lower() in self.numeric_columns:
                        if not self._is_numeric(value):
                            validations.append(ValidationResult(
                                validation_type="invalid_type",
                                row_number=row_num,
                                column_name=col_name,
                                message=f"Tipo incorrecto ('{value}') en columna '{col_name}' - se esperaba número",
                                severity="warning"
                            ))
            
            if not rows:
                validations.append(ValidationResult(
                    validation_type="empty_file",
                    message="El archivo CSV no contiene datos",
                    severity="error"
                ))
                
        except csv.Error as e:
            validations.append(ValidationResult(
                validation_type="parse_error",
                message=f"Error al parsear CSV: {str(e)}",
                severity="error"
            ))
        except Exception as e:
            validations.append(ValidationResult(
                validation_type="unknown_error",
                message=f"Error desconocido: {str(e)}",
                severity="error"
            ))
        
        return rows, validations
    
    def _compute_row_hash(self, row: Dict[str, Any]) -> str:
        """Compute a hash for a row to detect duplicates."""
        # Sort keys for consistent hashing
        sorted_items = sorted(row.items())
        row_str = "|".join(f"{k}:{v}" for k, v in sorted_items)
        return hashlib.md5(row_str.encode()).hexdigest()
    
    def _is_numeric(self, value: str) -> bool:
        """Check if a value is numeric."""
        try:
            float(str(value).replace(",", "."))
            return True
        except (ValueError, TypeError):
            return False
    
    def rows_to_json(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert rows to JSON-serializable format."""
        return [
            {k: str(v) if v is not None else None for k, v in row.items()}
            for row in rows
        ]


# Singleton instance
_csv_service: CSVService | None = None


def get_csv_service() -> CSVService:
    """Get CSV service singleton."""
    global _csv_service
    if _csv_service is None:
        _csv_service = CSVService()
    return _csv_service
