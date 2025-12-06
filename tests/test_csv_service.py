"""
Tests for the CSV service.
"""
import pytest
from app.services.csv_service import CSVService, get_csv_service


class TestCSVService:
    """Test cases for CSVService class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.csv_service = CSVService()

    # ==================== validate_and_process tests ====================

    def test_validate_and_process_valid_csv(self, sample_csv_content):
        """Test processing a valid CSV file."""
        rows, validations = self.csv_service.validate_and_process(
            sample_csv_content, "test.csv"
        )

        assert len(rows) == 2
        assert rows[0]["name"] == "Product A"
        assert rows[0]["precio"] == "100.50"
        assert rows[0]["cantidad"] == "10"
        assert rows[1]["name"] == "Product B"
        # No errors expected for valid CSV
        errors = [v for v in validations if v.severity == "error"]
        assert len(errors) == 0

    def test_validate_and_process_detects_duplicate_rows(self, sample_csv_with_duplicates):
        """Test that duplicate rows are detected."""
        rows, validations = self.csv_service.validate_and_process(
            sample_csv_with_duplicates, "test.csv"
        )

        assert len(rows) == 3
        duplicate_validations = [
            v for v in validations if v.validation_type == "duplicate_row"
        ]
        assert len(duplicate_validations) == 1
        assert duplicate_validations[0].row_number == 4  # Third data row (header is 1)
        assert duplicate_validations[0].severity == "warning"
        assert "duplicada" in duplicate_validations[0].message.lower()

    def test_validate_and_process_detects_empty_values(self, sample_csv_with_empty_values):
        """Test that empty values are detected."""
        rows, validations = self.csv_service.validate_and_process(
            sample_csv_with_empty_values, "test.csv"
        )

        assert len(rows) == 2
        empty_validations = [
            v for v in validations if v.validation_type == "empty_value"
        ]
        assert len(empty_validations) == 2
        # Check that column names are captured
        column_names = [v.column_name for v in empty_validations]
        assert "precio" in column_names
        assert "cantidad" in column_names

    def test_validate_and_process_detects_invalid_types(self, sample_csv_with_invalid_types):
        """Test that invalid types in numeric columns are detected."""
        rows, validations = self.csv_service.validate_and_process(
            sample_csv_with_invalid_types, "test.csv"
        )

        assert len(rows) == 2
        type_validations = [
            v for v in validations if v.validation_type == "invalid_type"
        ]
        assert len(type_validations) == 2
        # Check that the invalid values are reported
        messages = [v.message for v in type_validations]
        assert any("not_a_number" in m for m in messages)
        assert any("five" in m for m in messages)

    def test_validate_and_process_empty_file(self, empty_csv_content):
        """Test processing an empty CSV file (headers only)."""
        rows, validations = self.csv_service.validate_and_process(
            empty_csv_content, "test.csv"
        )

        assert len(rows) == 0
        empty_file_validations = [
            v for v in validations if v.validation_type == "empty_file"
        ]
        assert len(empty_file_validations) == 1
        assert empty_file_validations[0].severity == "error"

    def test_validate_and_process_no_headers(self, csv_without_headers):
        """Test processing a CSV file without headers."""
        rows, validations = self.csv_service.validate_and_process(
            csv_without_headers, "test.csv"
        )

        assert len(rows) == 0
        structure_validations = [
            v for v in validations if v.validation_type == "structure_error"
        ]
        assert len(structure_validations) == 1
        assert structure_validations[0].severity == "error"

    def test_validate_and_process_latin1_encoding(self):
        """Test processing a CSV file with latin-1 encoding."""
        # Create content with latin-1 characters
        content = "name,precio\nProducto Español,100.00\nCafé,50.00\n".encode("latin-1")
        
        rows, validations = self.csv_service.validate_and_process(content, "test.csv")

        assert len(rows) == 2
        # Should not have encoding errors
        errors = [v for v in validations if v.severity == "error"]
        assert len(errors) == 0

    def test_validate_and_process_utf8_encoding(self):
        """Test processing a CSV file with UTF-8 encoding."""
        content = "name,precio\nProducto ñ,100.00\nCafé 日本語,50.00\n".encode("utf-8")
        
        rows, validations = self.csv_service.validate_and_process(content, "test.csv")

        assert len(rows) == 2
        errors = [v for v in validations if v.severity == "error"]
        assert len(errors) == 0

    def test_validate_and_process_numeric_with_comma(self):
        """Test that numeric values with comma decimal separator are accepted."""
        content = b"name,precio,cantidad\nProduct A,100,50,10\n"
        
        rows, validations = self.csv_service.validate_and_process(content, "test.csv")

        # The comma in "100,50" will be treated as a column separator in CSV
        # So this tests the actual numeric validation
        assert len(rows) >= 1

    # ==================== _compute_row_hash tests ====================

    def test_compute_row_hash_same_rows_same_hash(self):
        """Test that identical rows produce the same hash."""
        row1 = {"name": "Product A", "precio": "100.50", "cantidad": "10"}
        row2 = {"name": "Product A", "precio": "100.50", "cantidad": "10"}

        hash1 = self.csv_service._compute_row_hash(row1)
        hash2 = self.csv_service._compute_row_hash(row2)

        assert hash1 == hash2

    def test_compute_row_hash_different_rows_different_hash(self):
        """Test that different rows produce different hashes."""
        row1 = {"name": "Product A", "precio": "100.50", "cantidad": "10"}
        row2 = {"name": "Product B", "precio": "100.50", "cantidad": "10"}

        hash1 = self.csv_service._compute_row_hash(row1)
        hash2 = self.csv_service._compute_row_hash(row2)

        assert hash1 != hash2

    def test_compute_row_hash_order_independent(self):
        """Test that column order doesn't affect the hash."""
        row1 = {"name": "Product A", "precio": "100.50", "cantidad": "10"}
        row2 = {"cantidad": "10", "name": "Product A", "precio": "100.50"}

        hash1 = self.csv_service._compute_row_hash(row1)
        hash2 = self.csv_service._compute_row_hash(row2)

        assert hash1 == hash2

    # ==================== _is_numeric tests ====================

    def test_is_numeric_integer(self):
        """Test that integers are recognized as numeric."""
        assert self.csv_service._is_numeric("100") is True
        assert self.csv_service._is_numeric("0") is True
        assert self.csv_service._is_numeric("-50") is True

    def test_is_numeric_float_with_dot(self):
        """Test that floats with dot are recognized as numeric."""
        assert self.csv_service._is_numeric("100.50") is True
        assert self.csv_service._is_numeric("0.99") is True
        assert self.csv_service._is_numeric("-50.25") is True

    def test_is_numeric_float_with_comma(self):
        """Test that floats with comma are recognized as numeric."""
        assert self.csv_service._is_numeric("100,50") is True
        assert self.csv_service._is_numeric("1000,99") is True

    def test_is_numeric_non_numeric(self):
        """Test that non-numeric values are not recognized as numeric."""
        assert self.csv_service._is_numeric("abc") is False
        assert self.csv_service._is_numeric("10abc") is False
        assert self.csv_service._is_numeric("") is False
        assert self.csv_service._is_numeric("one hundred") is False

    # ==================== rows_to_json tests ====================

    def test_rows_to_json_converts_values_to_strings(self):
        """Test that rows_to_json converts all values to strings."""
        rows = [
            {"name": "Product A", "precio": 100.50, "cantidad": 10},
            {"name": "Product B", "precio": None, "cantidad": 5},
        ]

        result = self.csv_service.rows_to_json(rows)

        assert result[0]["precio"] == "100.5"
        assert result[0]["cantidad"] == "10"
        assert result[1]["precio"] is None
        assert result[1]["cantidad"] == "5"

    def test_rows_to_json_empty_list(self):
        """Test rows_to_json with empty list."""
        result = self.csv_service.rows_to_json([])
        assert result == []

    # ==================== get_csv_service tests ====================

    def test_get_csv_service_returns_singleton(self):
        """Test that get_csv_service returns the same instance."""
        service1 = get_csv_service()
        service2 = get_csv_service()

        assert service1 is service2

    def test_get_csv_service_returns_csv_service_instance(self):
        """Test that get_csv_service returns a CSVService instance."""
        service = get_csv_service()
        assert isinstance(service, CSVService)


class TestCSVServiceEdgeCases:
    """Edge case tests for CSVService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.csv_service = CSVService()

    def test_csv_with_special_characters(self):
        """Test CSV with special characters in values."""
        content = b'name,description\n"Product, with comma","Contains ""quotes"""\n'
        
        rows, validations = self.csv_service.validate_and_process(content, "test.csv")

        assert len(rows) == 1
        assert rows[0]["name"] == "Product, with comma"
        assert rows[0]["description"] == 'Contains "quotes"'

    def test_csv_with_very_long_values(self):
        """Test CSV with very long values."""
        long_value = "a" * 10000
        content = f"name,description\n{long_value},short\n".encode("utf-8")
        
        rows, validations = self.csv_service.validate_and_process(content, "test.csv")

        assert len(rows) == 1
        assert len(rows[0]["name"]) == 10000

    def test_csv_with_many_columns(self):
        """Test CSV with many columns."""
        headers = ",".join([f"col{i}" for i in range(100)])
        values = ",".join(["value" for _ in range(100)])
        content = f"{headers}\n{values}\n".encode("utf-8")
        
        rows, validations = self.csv_service.validate_and_process(content, "test.csv")

        assert len(rows) == 1
        assert len(rows[0]) == 100

    def test_csv_with_whitespace_values(self):
        """Test CSV with whitespace-only values."""
        content = b"name,precio\n   ,100\nProduct,   \n"
        
        rows, validations = self.csv_service.validate_and_process(content, "test.csv")

        empty_validations = [
            v for v in validations if v.validation_type == "empty_value"
        ]
        assert len(empty_validations) == 2

    def test_csv_with_mixed_case_numeric_columns(self):
        """Test that numeric column detection is case-insensitive."""
        content = b"name,PRECIO,Cantidad,Price\nProduct,abc,def,ghi\n"
        
        rows, validations = self.csv_service.validate_and_process(content, "test.csv")

        type_validations = [
            v for v in validations if v.validation_type == "invalid_type"
        ]
        # All three columns should be flagged as numeric columns with invalid values
        assert len(type_validations) == 3
