"""Tests for JSON utility functions."""

from src.utils.json_utils import extract_json_from_text, normalize_optional_fields


class TestExtractJsonFromText:
    """Test cases for extract_json_from_text function."""

    def test_extract_valid_json_only(self):
        """Test extracting when the entire text is valid JSON."""
        text = '{"key": "value", "number": 42}'
        result = extract_json_from_text(text)
        assert result == {"key": "value", "number": 42}

    def test_extract_json_with_prefix(self):
        """Test extracting JSON with text before it."""
        text = 'Here is the response: {"key": "value"}'
        result = extract_json_from_text(text)
        assert result == {"key": "value"}

    def test_extract_json_with_suffix(self):
        """Test extracting JSON with text after it."""
        text = '{"key": "value"} That was the JSON'
        result = extract_json_from_text(text)
        assert result == {"key": "value"}

    def test_extract_json_with_surrounding_text(self):
        """Test extracting JSON with text before and after."""
        text = 'Response: {"key": "value", "nested": {"inner": true}} Done.'
        result = extract_json_from_text(text)
        assert result == {"key": "value", "nested": {"inner": True}}

    def test_extract_nested_json(self):
        """Test extracting JSON with nested objects."""
        text = '{"outer": {"inner": {"deep": "value"}}}'
        result = extract_json_from_text(text)
        assert result == {"outer": {"inner": {"deep": "value"}}}

    def test_extract_json_with_arrays(self):
        """Test extracting JSON containing arrays."""
        text = '{"items": [1, 2, 3], "names": ["a", "b"]}'
        result = extract_json_from_text(text)
        assert result == {"items": [1, 2, 3], "names": ["a", "b"]}

    def test_extract_json_multiline(self):
        """Test extracting multiline JSON."""
        text = """
        Here's the data:
        {
            "key": "value",
            "number": 42,
            "nested": {
                "inner": true
            }
        }
        """
        result = extract_json_from_text(text)
        assert result["key"] == "value"
        assert result["number"] == 42
        assert result["nested"]["inner"] is True

    def test_no_json_returns_none(self):
        """Test that text without JSON returns None."""
        text = "This is just plain text without any JSON"
        result = extract_json_from_text(text)
        assert result is None

    def test_invalid_json_returns_none(self):
        """Test that invalid JSON returns None."""
        text = '{"key": "value", "missing": closing bracket'
        result = extract_json_from_text(text)
        assert result is None

    def test_empty_text_returns_none(self):
        """Test that empty text returns None."""
        assert extract_json_from_text("") is None
        assert extract_json_from_text("   ") is None

    def test_json_array_returns_none(self):
        """Test that JSON arrays (not objects) return None."""
        text = "[1, 2, 3, 4]"
        result = extract_json_from_text(text)
        assert result is None

    def test_multiple_json_objects(self):
        """Test extracting when there are multiple JSON objects."""
        text = '{"first": 1} some text {"second": 2}'
        result = extract_json_from_text(text)
        # Should return the first valid JSON object found
        assert result == {"first": 1}


class TestNormalizeOptionalFields:
    """Test cases for normalize_optional_fields function."""

    def test_normalize_none_value(self):
        """Test that None values remain None."""
        data = {"field1": None, "field2": "value"}
        result = normalize_optional_fields(data, ["field1"])
        assert result["field1"] is None
        assert result["field2"] == "value"

    def test_normalize_null_string(self):
        """Test that 'null' string becomes None."""
        data = {"field1": "null", "field2": "value"}
        result = normalize_optional_fields(data, ["field1"])
        assert result["field1"] is None
        assert result["field2"] == "value"

    def test_normalize_none_string(self):
        """Test that 'None' string becomes None."""
        data = {"field1": "None", "field2": "value"}
        result = normalize_optional_fields(data, ["field1"])
        assert result["field1"] is None
        assert result["field2"] == "value"

    def test_normalize_empty_list(self):
        """Test that empty lists become None."""
        data = {"field1": [], "field2": [1, 2, 3]}
        result = normalize_optional_fields(data, ["field1", "field2"])
        assert result["field1"] is None
        assert result["field2"] == [1, 2, 3]  # Non-empty list unchanged

    def test_normalize_multiple_fields(self):
        """Test normalizing multiple fields at once."""
        data = {
            "field1": "null",
            "field2": [],
            "field3": "None",
            "field4": "keep this",
            "field5": None,
        }
        result = normalize_optional_fields(data, ["field1", "field2", "field3", "field5"])
        assert result["field1"] is None
        assert result["field2"] is None
        assert result["field3"] is None
        assert result["field4"] == "keep this"
        assert result["field5"] is None

    def test_normalize_missing_field(self):
        """Test that missing fields are ignored."""
        data = {"field1": "value"}
        result = normalize_optional_fields(data, ["field1", "field2"])
        assert result["field1"] == "value"
        assert "field2" not in result

    def test_normalize_preserves_other_values(self):
        """Test that non-null values are preserved."""
        data = {
            "field1": "actual value",
            "field2": {"nested": "object"},
            "field3": 123,
            "field4": True,
        }
        result = normalize_optional_fields(data, ["field1", "field2", "field3", "field4"])
        assert result["field1"] == "actual value"
        assert result["field2"] == {"nested": "object"}
        assert result["field3"] == 123
        assert result["field4"] is True

    def test_normalize_modifies_in_place(self):
        """Test that the function modifies the dictionary in place."""
        data = {"field1": "null"}
        result = normalize_optional_fields(data, ["field1"])
        assert result is data  # Same object reference
        assert data["field1"] is None

    def test_malformed_json_with_brackets(self):
        """Test extraction with malformed JSON that has brackets."""
        # Test case where brackets are found but JSON is invalid
        text = "Some text { invalid json: no quotes } more text"
        result = extract_json_from_text(text)
        assert result is None

    def test_json_object_at_boundaries(self):
        """Test JSON extraction using boundary search."""
        # JSON that would fail code block extraction but works with boundary search
        text = 'Random text before {"key": "value", "number": 42} random text after'
        result = extract_json_from_text(text)
        assert result == {"key": "value", "number": 42}

    def test_multiple_json_objects_uses_first(self):
        """Test that when multiple JSON objects exist, the first valid one is used."""
        text = 'First {"first": "value1"} some text {"second": "value2"}'
        result = extract_json_from_text(text)
        # Should get the first complete JSON object
        assert result == {"first": "value1"}

    def test_json_with_code_fence_invalid_json(self):
        """Test code fence with invalid JSON content."""
        text = """```json
{ this is not valid json }
```"""
        result = extract_json_from_text(text)
        assert result is None

    def test_nested_json_in_code_block(self):
        """Test extraction of nested JSON from code block."""
        text = """Here's the response:
```json
{
  "nested": {
    "data": [1, 2, 3],
    "flag": true
  },
  "status": "ok"
}
```"""
        result = extract_json_from_text(text)
        assert result == {"nested": {"data": [1, 2, 3], "flag": True}, "status": "ok"}
