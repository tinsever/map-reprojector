"""
Reprojection module for SVG maps.
Handles conversion between Plate Carrée and Equal Earth projections.
"""

from .plate_to_equal import reproject_svg as plate_to_equal_reproject
from .equal_to_plate import reproject_svg as equal_to_plate_reproject
from .plate_to_wagner import reproject_svg as plate_to_wagner_reproject
from .equal_to_wagner import reproject_svg as equal_to_wagner_reproject

__all__ = [
    'plate_to_equal_reproject',
    'equal_to_plate_reproject',
    'plate_to_wagner_reproject',
    'equal_to_wagner_reproject',
]

