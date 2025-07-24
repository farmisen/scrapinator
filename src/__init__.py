"""Scrapinator - Web Task Automation System."""

from .analyzer import WebTaskAnalyzer
from .models.task import Task

__all__ = ["Task", "WebTaskAnalyzer"]
