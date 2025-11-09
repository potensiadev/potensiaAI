# potensia_ai/ai_tools/media/__init__.py
"""
Media Generation Module for PotensiaAI

This module provides AI-powered media generation functionality,
including automatic thumbnail image creation using OpenAI DALL-E.
"""

from .thumbnail import generate_thumbnail

__all__ = ["generate_thumbnail"]
