"""
Word to Column Mapper - High-performance search engine for mapping words to column identifiers.

This package provides a comprehensive search engine that maps input words to arrays of 
column identifiers, supporting many-to-many relationships with intelligent typo correction 
and fuzzy matching capabilities.
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .core.engine import SearchEngine
from .models.response import SearchResult, SearchResponse

__all__ = [
    "SearchEngine",
    "SearchResult", 
    "SearchResponse",
]
