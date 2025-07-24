"""Task model for representing web automation tasks."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Task(BaseModel):
    """
    Represents a structured web automation task.

    This model captures the essential components of a task that has been analyzed
    from a natural language description. It provides a structured representation
    that can be used to generate an executable automation plan.
    """

    description: str = Field(
        ..., description="The original natural language task description provided by the user"
    )

    objectives: List[str] = Field(
        ..., min_length=1, description="List of main objectives to accomplish in the task"
    )

    constraints: List[str] = Field(
        default_factory=list,
        description="List of constraints or limitations that must be respected during execution",
    )

    success_criteria: List[str] = Field(
        ...,
        min_length=1,
        description="List of criteria that determine if the task has been completed successfully",
    )

    data_to_extract: Optional[List[str]] = Field(
        None, description="Optional list of specific data items to extract from web pages"
    )

    actions_to_perform: Optional[List[str]] = Field(
        None, description="Optional list of specific actions to perform (click, fill, submit, etc.)"
    )

    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context information that might be useful for task execution",
    )

    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    def has_data_extraction(self) -> bool:
        """Check if the task involves data extraction."""
        return self.data_to_extract is not None and len(self.data_to_extract) > 0

    def has_actions(self) -> bool:
        """Check if the task involves performing specific actions."""
        return self.actions_to_perform is not None and len(self.actions_to_perform) > 0

    def is_complex(self) -> bool:
        """
        Determine if this is a complex task based on the number of objectives and actions.

        A task is considered complex if it has multiple objectives or many actions to perform.
        """
        complexity_threshold_objectives = 2
        complexity_threshold_actions = 3
        return len(self.objectives) > complexity_threshold_objectives or (
            self.has_actions()
            and self.actions_to_perform is not None
            and len(self.actions_to_perform) > complexity_threshold_actions
        )
