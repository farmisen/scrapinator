"""Tests for the Task model."""

import pytest
from pydantic import ValidationError

from src.models.task import Task


class TestTaskModel:
    """Test cases for the Task model."""

    def test_task_creation_with_required_fields(self):
        """Test creating a Task with only required fields."""
        task = Task(
            description="Extract product prices from an e-commerce website",
            objectives=["Navigate to products page", "Extract all product prices"],
            success_criteria=["All visible product prices have been extracted"],
        )

        assert task.description == "Extract product prices from an e-commerce website"
        assert len(task.objectives) == 2
        assert len(task.success_criteria) == 1
        assert task.constraints == []  # Default empty list
        assert task.data_to_extract is None
        assert task.actions_to_perform is None
        assert task.context == {}  # Default empty dict

    def test_task_creation_with_all_fields(self):
        """Test creating a Task with all fields populated."""
        task = Task(
            description="Download all PDF reports from the dashboard",
            objectives=["Login to dashboard", "Navigate to reports section", "Download all PDFs"],
            constraints=["Only download reports from current year", "Skip encrypted files"],
            success_criteria=["All PDF files downloaded", "Files saved to specified directory"],
            data_to_extract=["Report titles", "Report dates", "File sizes"],
            actions_to_perform=[
                "Click login button",
                "Fill credentials",
                "Click each download link",
            ],
            context={"year": 2024, "file_types": [".pdf"], "max_files": 50},
        )

        assert len(task.objectives) == 3
        assert len(task.constraints) == 2
        assert len(task.data_to_extract) == 3
        assert len(task.actions_to_perform) == 3
        assert task.context["year"] == 2024

    def test_task_missing_required_fields(self):
        """Test that missing required fields raise validation errors."""
        # Missing description
        with pytest.raises(ValidationError) as exc_info:
            Task(objectives=["Extract data"], success_criteria=["Data extracted"])
        assert "description" in str(exc_info.value)

        # Missing objectives
        with pytest.raises(ValidationError) as exc_info:
            Task(description="Test task", success_criteria=["Task completed"])
        assert "objectives" in str(exc_info.value)

        # Missing success_criteria
        with pytest.raises(ValidationError) as exc_info:
            Task(description="Test task", objectives=["Do something"])
        assert "success_criteria" in str(exc_info.value)

    def test_task_empty_lists_validation(self):
        """Test that objectives and success_criteria cannot be empty lists."""
        # Empty objectives list
        with pytest.raises(ValidationError) as exc_info:
            Task(description="Test task", objectives=[], success_criteria=["Done"])
        assert "at least 1 item" in str(exc_info.value).lower()

        # Empty success_criteria list
        with pytest.raises(ValidationError) as exc_info:
            Task(description="Test task", objectives=["Do something"], success_criteria=[])
        assert "at least 1 item" in str(exc_info.value).lower()

    def test_task_type_validation(self):
        """Test that fields have correct types."""
        # Invalid type for objectives (string instead of list)
        with pytest.raises(ValidationError):
            Task(
                description="Test task",
                objectives="Navigate to page",  # Should be a list
                success_criteria=["Done"],
            )

        # Invalid type for context (list instead of dict)
        with pytest.raises(ValidationError):
            Task(
                description="Test task",
                objectives=["Do something"],
                success_criteria=["Done"],
                context=["invalid", "context"],  # Should be a dict
            )

    def test_task_extra_fields_forbidden(self):
        """Test that extra fields are not allowed."""
        with pytest.raises(ValidationError) as exc_info:
            Task(
                description="Test task",
                objectives=["Do something"],
                success_criteria=["Done"],
                extra_field="not allowed",
            )
        assert "extra" in str(exc_info.value).lower()

    def test_has_data_extraction_method(self):
        """Test the has_data_extraction helper method."""
        # Task without data extraction
        task1 = Task(
            description="Navigate to page",
            objectives=["Go to page"],
            success_criteria=["Page loaded"],
        )
        assert not task1.has_data_extraction()

        # Task with empty data_to_extract
        task2 = Task(
            description="Navigate to page",
            objectives=["Go to page"],
            success_criteria=["Page loaded"],
            data_to_extract=[],
        )
        assert not task2.has_data_extraction()

        # Task with data extraction
        task3 = Task(
            description="Extract prices",
            objectives=["Get prices"],
            success_criteria=["Prices extracted"],
            data_to_extract=["Product prices", "Product names"],
        )
        assert task3.has_data_extraction()

    def test_has_actions_method(self):
        """Test the has_actions helper method."""
        # Task without actions
        task1 = Task(
            description="Read page", objectives=["Read content"], success_criteria=["Content read"]
        )
        assert not task1.has_actions()

        # Task with actions
        task2 = Task(
            description="Fill form",
            objectives=["Submit form"],
            success_criteria=["Form submitted"],
            actions_to_perform=["Click submit button", "Fill email field"],
        )
        assert task2.has_actions()

    def test_is_complex_method(self):
        """Test the is_complex helper method."""
        # Simple task
        simple_task = Task(
            description="Click button",
            objectives=["Click the submit button"],
            success_criteria=["Button clicked"],
        )
        assert not simple_task.is_complex()

        # Complex task with many objectives
        complex_task1 = Task(
            description="Complete multi-step process",
            objectives=["Login", "Navigate to dashboard", "Download reports", "Analyze data"],
            success_criteria=["All steps completed"],
        )
        assert complex_task1.is_complex()

        # Complex task with many actions
        complex_task2 = Task(
            description="Fill complex form",
            objectives=["Submit application"],
            success_criteria=["Application submitted"],
            actions_to_perform=[
                "Fill name",
                "Fill email",
                "Upload document",
                "Select options",
                "Submit",
            ],
        )
        assert complex_task2.is_complex()

    def test_task_field_assignment_validation(self):
        """Test that field assignment is validated."""
        task = Task(description="Test task", objectives=["Do something"], success_criteria=["Done"])

        # Valid assignment
        task.constraints = ["New constraint"]
        assert task.constraints == ["New constraint"]

        # Invalid assignment should raise error
        with pytest.raises(ValidationError):
            task.objectives = []  # Empty list not allowed

        with pytest.raises(ValidationError):
            task.objectives = "not a list"  # Wrong type
