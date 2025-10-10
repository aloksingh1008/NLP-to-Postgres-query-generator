"""Main search engine implementation."""

import time
from typing import Dict, List, Optional, Set, Tuple

from ..models.response import SearchResult, SearchResponse
from .fuzzy_matcher import FuzzyMatcher
from .index import IndexManager
from .normalizer import TextNormalizer


class SearchEngine:
    """Main search engine for word-to-column mapping."""
    
    def __init__(self, fuzzy_threshold: float = 0.6) -> None:
        """
        Initialize the search engine.
        
        Args:
            fuzzy_threshold: Default threshold for fuzzy matching
        """
        self.fuzzy_threshold = fuzzy_threshold
        self.fuzzy_matcher = FuzzyMatcher(fuzzy_threshold)
        self.normalizer = TextNormalizer()
        self.index_manager = IndexManager()
        
        # Performance tracking
        self._stats = {
            "total_queries": 0,
            "exact_matches": 0,
            "fuzzy_matches": 0,
            "no_matches": 0,
            "total_execution_time": 0.0,
            "cache_hits": 0,
            "cache_misses": 0
        }
    
    def load_mappings(self, mappings: Dict[str, List[str]]) -> None:
        """
        Load word-to-column mappings into the engine.
        
        Args:
            mappings: Dictionary mapping words to column arrays
        """
        for word, columns in mappings.items():
            self.index_manager.add_mapping(word, columns)
    
    def search(
        self, 
        query: str, 
        fuzzy_threshold: Optional[float] = None,
        max_results: int = 10,
        include_suggestions: bool = True,
        max_edit_distance: int = 5
    ) -> SearchResponse:
        """
        Search for columns matching a word query.
        
        Args:
            query: Search query
            fuzzy_threshold: Custom fuzzy matching threshold
            max_results: Maximum number of results to return
            include_suggestions: Whether to include suggestions for no-match queries
            max_edit_distance: Maximum edit distance for fuzzy matches (default: 5)
            
        Returns:
            SearchResponse with results and metadata
        """
        start_time = time.time()
        
        # Validate input
        if not query or not query.strip():
            return self._create_empty_response(query, start_time)
        
        query = query.strip()
        fuzzy_threshold = fuzzy_threshold or self.fuzzy_threshold
        
        # Update statistics
        self._stats["total_queries"] += 1
        
        # Always perform fuzzy search with edit distance filter
        all_results = self._fuzzy_search_with_edit_distance(
            query, fuzzy_threshold, max_results, max_edit_distance
        )
        
        # Check if we have an exact match
        has_exact_match = any(
            result.match_type == "exact" for result in all_results
        )
        
        if all_results:
            execution_time = (time.time() - start_time) * 1000
            
            # Update statistics based on match type
            if has_exact_match:
                self._stats["exact_matches"] += 1
            else:
                self._stats["fuzzy_matches"] += 1
            
            self._stats["total_execution_time"] += execution_time
            
            # Collect all unique columns
            all_columns = set()
            for result in all_results:
                all_columns.update(result.columns)
            
            return SearchResponse(
                query=query,
                execution_time_ms=execution_time,
                exact_match=has_exact_match,
                total_results=len(all_results),
                results=all_results,
                total_unique_columns=list(all_columns),
                cache_hit=False,
                suggestions=None
            )
        
        # No matches found
        execution_time = (time.time() - start_time) * 1000
        self._stats["no_matches"] += 1
        self._stats["total_execution_time"] += execution_time
        
        suggestions = None
        if include_suggestions:
            suggestions = self._get_suggestions(query)
        
        return SearchResponse(
            query=query,
            execution_time_ms=execution_time,
            exact_match=False,
            total_results=0,
            results=[],
            total_unique_columns=[],
            cache_hit=False,
            suggestions=suggestions
        )
    
    def reverse_search(self, column_id: str) -> Optional[Dict[str, any]]:
        """
        Find words that map to a specific column.
        
        Args:
            column_id: The column identifier to search for
            
        Returns:
            Dictionary with words and metadata, or None if not found
        """
        start_time = time.time()
        
        words = self.index_manager.reverse_index.get_words(column_id)
        if not words:
            return None
        
        execution_time = (time.time() - start_time) * 1000
        
        return {
            "column_id": column_id,
            "words": words,
            "total_mappings": len(words),
            "execution_time_ms": execution_time
        }
    
    def intersection_search(self, words: List[str]) -> Optional[Dict[str, any]]:
        """
        Find columns that are common to all specified words.
        
        Args:
            words: List of words to find intersection for
            
        Returns:
            Dictionary with intersection results, or None if no common columns
        """
        start_time = time.time()
        
        if len(words) < 2:
            return None
        
        # Get columns for each word
        word_columns = []
        for word in words:
            columns = self.index_manager.forward_index.get_columns(word)
            if columns:
                word_columns.append(set(columns))
        
        if not word_columns:
            return None
        
        # Find intersection
        intersection = word_columns[0]
        for columns in word_columns[1:]:
            intersection = intersection.intersection(columns)
        
        if not intersection:
            return None
        
        execution_time = (time.time() - start_time) * 1000
        
        return {
            "query_words": words,
            "intersection_columns": list(intersection),
            "operation": "AND",
            "execution_time_ms": execution_time,
            "total_common_columns": len(intersection)
        }
    
    def union_search(self, words: List[str]) -> Optional[Dict[str, any]]:
        """
        Find all columns that are associated with any of the specified words.
        
        Args:
            words: List of words to find union for
            
        Returns:
            Dictionary with union results, or None if no columns found
        """
        start_time = time.time()
        
        if not words:
            return None
        
        # Get columns for each word
        all_columns = set()
        for word in words:
            columns = self.index_manager.forward_index.get_columns(word)
            if columns:
                all_columns.update(columns)
        
        if not all_columns:
            return None
        
        execution_time = (time.time() - start_time) * 1000
        
        return {
            "query_words": words,
            "union_columns": list(all_columns),
            "operation": "OR",
            "execution_time_ms": execution_time,
            "total_unique_columns": len(all_columns)
        }
    
    def _exact_search(self, query: str) -> Optional[SearchResult]:
        """
        Perform exact search for a query.
        
        Args:
            query: Search query
            
        Returns:
            SearchResult if found, None otherwise
        """
        columns = self.index_manager.forward_index.get_columns(query)
        if columns:
            return SearchResult(
                word=query,
                confidence=1.0,
                match_type="exact",
                columns=columns,
                edit_distance=0,
                changes=None
            )
        return None
    
    def _fuzzy_search(
        self, 
        query: str, 
        threshold: float, 
        max_results: int
    ) -> List[SearchResult]:
        """
        Perform fuzzy search for a query.
        
        Args:
            query: Search query
            threshold: Fuzzy matching threshold
            max_results: Maximum number of results
            
        Returns:
            List of SearchResult objects
        """
        all_words = self.index_manager.forward_index.get_all_words()
        if not all_words:
            return []
        
        # Find fuzzy matches
        matches = self.fuzzy_matcher.find_multiple_matches(
            query, all_words, max_results, threshold
        )
        
        results = []
        for word, confidence, match_type, edit_distance in matches:
            columns = self.index_manager.forward_index.get_columns(word)
            if columns:
                changes = self.fuzzy_matcher.get_edit_operations(query, word)
                
                result = SearchResult(
                    word=word,
                    confidence=confidence,
                    match_type=match_type,
                    columns=columns,
                    edit_distance=edit_distance,
                    changes=changes
                )
                results.append(result)
        
        return results
    
    def _fuzzy_search_with_edit_distance(
        self, 
        query: str, 
        threshold: float, 
        max_results: int,
        max_edit_distance: int
    ) -> List[SearchResult]:
        """
        Perform fuzzy search with edit distance filtering.
        
        Args:
            query: Search query
            threshold: Fuzzy matching threshold
            max_results: Maximum number of results
            max_edit_distance: Maximum edit distance allowed
            
        Returns:
            List of SearchResult objects
        """
        all_words = self.index_manager.forward_index.get_all_words()
        if not all_words:
            return []
        
        # Calculate edit distance for ALL words in the database
        from rapidfuzz.distance import Levenshtein
        normalized_query = self.normalizer.normalize(query)
        
        results = []
        for word in all_words:
            normalized_word = self.normalizer.normalize(word)
            
            # Calculate actual edit distance using Levenshtein
            edit_distance = Levenshtein.distance(normalized_query, normalized_word)
            
            # Alternative: Count total character changes (insertions + deletions)
            # This counts all operations, not just the optimized path
            total_changes = abs(len(normalized_query) - len(normalized_word)) + Levenshtein.distance(normalized_query, normalized_word)
            # Use the total changes as edit distance
            edit_distance = total_changes
            
            # Only include words with edit distance <= max_edit_distance
            if edit_distance <= max_edit_distance:
                columns = self.index_manager.forward_index.get_columns(word)
                if columns:
                    # Determine match type and confidence
                    if edit_distance == 0:
                        confidence = 1.0
                        match_type = "exact"
                        changes = None
                    else:
                        # Calculate confidence based on edit distance
                        max_len = max(len(normalized_query), len(normalized_word))
                        confidence = 1.0 - (edit_distance / max_len) if max_len > 0 else 0.0
                        match_type = "fuzzy_levenshtein"
                        changes = self.fuzzy_matcher.get_edit_operations(query, word)
                    
                    result = SearchResult(
                        word=word,
                        confidence=confidence,
                        match_type=match_type,
                        columns=columns,
                        edit_distance=edit_distance,
                        changes=changes
                    )
                    results.append(result)
        
        # Sort by edit distance (ascending), then confidence (descending)
        results.sort(key=lambda x: (x.edit_distance, -x.confidence))
        return results[:max_results]
    
    def _get_suggestions(self, query: str, max_suggestions: int = 5) -> List[str]:
        """
        Get suggestions for a query with no matches.
        
        Args:
            query: Query to get suggestions for
            max_suggestions: Maximum number of suggestions
            
        Returns:
            List of suggested words
        """
        all_words = self.index_manager.forward_index.get_all_words()
        return self.fuzzy_matcher.suggest_corrections(
            query, all_words, max_suggestions
        )
    
    def _create_empty_response(self, query: str, start_time: float) -> SearchResponse:
        """Create an empty response for invalid queries."""
        execution_time = (time.time() - start_time) * 1000
        
        return SearchResponse(
            query=query or "",
            execution_time_ms=execution_time,
            exact_match=False,
            total_results=0,
            results=[],
            total_unique_columns=[],
            cache_hit=False,
            suggestions=None
        )
    
    def get_stats(self) -> Dict[str, any]:
        """Get engine statistics."""
        stats = self._stats.copy()
        
        # Calculate averages
        if stats["total_queries"] > 0:
            stats["average_execution_time_ms"] = (
                stats["total_execution_time"] / stats["total_queries"]
            )
            stats["exact_match_rate"] = stats["exact_matches"] / stats["total_queries"]
            stats["fuzzy_match_rate"] = stats["fuzzy_matches"] / stats["total_queries"]
            stats["no_match_rate"] = stats["no_matches"] / stats["total_queries"]
        else:
            stats["average_execution_time_ms"] = 0.0
            stats["exact_match_rate"] = 0.0
            stats["fuzzy_match_rate"] = 0.0
            stats["no_match_rate"] = 0.0
        
        # Add index stats
        stats["index_stats"] = self.index_manager.get_stats()
        
        return stats
    
    def clear(self) -> None:
        """Clear all data and reset statistics."""
        self.index_manager.clear()
        self._stats = {
            "total_queries": 0,
            "exact_matches": 0,
            "fuzzy_matches": 0,
            "no_matches": 0,
            "total_execution_time": 0.0,
            "cache_hits": 0,
            "cache_misses": 0
        }
