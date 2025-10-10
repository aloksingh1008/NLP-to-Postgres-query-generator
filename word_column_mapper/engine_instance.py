"""Global search engine instance to avoid circular imports."""

from .core.engine import SearchEngine
from .config import get_settings

# Global search engine instance
settings = get_settings()
search_engine = SearchEngine(fuzzy_threshold=settings.fuzzy_threshold)
