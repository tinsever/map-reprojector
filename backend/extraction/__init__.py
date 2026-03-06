"""
Extraction module for SVG map sections.
Handles extraction of map regions with optional reprojection.
"""

from .extract_section import extract_map_section, get_map_section_centered

__all__ = ['extract_map_section', 'get_map_section_centered']

