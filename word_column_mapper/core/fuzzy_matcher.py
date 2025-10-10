"""Fuzzy matching algorithms for typo correction and approximate matching."""

import time
from typing import List, Optional, Tuple

from rapidfuzz import fuzz, process
from rapidfuzz.distance import Levenshtein

from .normalizer import TextNormalizer


class FuzzyMatcher:
    """Handles fuzzy matching with multiple algorithms and strategies."""
    
    def __init__(self, threshold: float = 0.6) -> None:
        """
        Initialize the fuzzy matcher.
        
        Args:
            threshold: Minimum confidence threshold for matches
        """
        self.threshold = threshold
        self.normalizer = TextNormalizer()
        
    def find_best_match(
        self, 
        query: str, 
        candidates: List[str], 
        threshold: Optional[float] = None
    ) -> Optional[Tuple[str, float, str, int]]:
        """
        Find the best fuzzy match for a query among candidates.
        
        Args:
            query: Search query
            candidates: List of candidate words to match against
            threshold: Custom threshold (uses instance threshold if None)
            
        Returns:
            Tuple of (matched_word, confidence, match_type, edit_distance) or None
        """
        if not query or not candidates:
            return None
        
        threshold = threshold or self.threshold
        normalized_query = self.normalizer.normalize(query)
        
        best_match = None
        best_confidence = 0.0
        best_type = "no_match"
        best_distance = 0
        
        for candidate in candidates:
            normalized_candidate = self.normalizer.normalize(candidate)
            
            # Try exact match first
            if normalized_query == normalized_candidate:
                return candidate, 1.0, "exact", 0
            
            # Try fuzzy matching
            confidence, match_type, distance = self._calculate_fuzzy_match(
                normalized_query, normalized_candidate, candidate
            )
            
            if confidence > best_confidence and confidence >= threshold:
                best_match = candidate
                best_confidence = confidence
                best_type = match_type
                best_distance = distance
        
        if best_match:
            return best_match, best_confidence, best_type, best_distance
        
        return None
    
    def find_multiple_matches(
        self, 
        query: str, 
        candidates: List[str], 
        max_results: int = 10,
        threshold: Optional[float] = None
    ) -> List[Tuple[str, float, str, int]]:
        """
        Find multiple fuzzy matches for a query.
        
        Args:
            query: Search query
            candidates: List of candidate words
            max_results: Maximum number of results to return
            threshold: Custom threshold
            
        Returns:
            List of tuples (word, confidence, match_type, edit_distance)
        """
        if not query or not candidates:
            return []
        
        threshold = threshold or self.threshold
        normalized_query = self.normalizer.normalize(query)
        
        matches = []
        
        for candidate in candidates:
            normalized_candidate = self.normalizer.normalize(candidate)
            
            # Try exact match first
            if normalized_query == normalized_candidate:
                matches.append((candidate, 1.0, "exact", 0))
                # Don't continue - we want to also check for fuzzy matches
            
            # Try fuzzy matching for all candidates
            confidence, match_type, distance = self._calculate_fuzzy_match(
                normalized_query, normalized_candidate, candidate
            )
            
            if confidence >= threshold:
                # Only add if it's not already added as exact match
                if not (normalized_query == normalized_candidate):
                    matches.append((candidate, confidence, match_type, distance))
        
        # Sort by confidence (descending) and return top results
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:max_results]
    
    def _calculate_fuzzy_match(
        self, 
        query: str, 
        candidate: str, 
        original_candidate: str
    ) -> Tuple[float, str, int]:
        """
        Calculate fuzzy match between query and candidate.
        
        Args:
            query: Normalized query
            candidate: Normalized candidate
            original_candidate: Original candidate (for partial matching)
            
        Returns:
            Tuple of (confidence, match_type, edit_distance)
        """
        # Levenshtein distance
        distance = Levenshtein.distance(query, candidate)
        max_len = max(len(query), len(candidate))
        levenshtein_ratio = 1.0 - (distance / max_len) if max_len > 0 else 0.0
        
        # Partial ratio (for substring matches)
        partial_ratio = fuzz.partial_ratio(query, candidate) / 100.0
        
        # Token sort ratio (for word order independence)
        token_sort_ratio = fuzz.token_sort_ratio(query, candidate) / 100.0
        
        # Token set ratio (for word set matching)
        token_set_ratio = fuzz.token_set_ratio(query, candidate) / 100.0
        
        # Choose the best match type and confidence
        ratios = [
            (levenshtein_ratio, "fuzzy_levenshtein", distance),
            (partial_ratio, "fuzzy_partial", distance),
            (token_sort_ratio, "fuzzy_token_sort", distance),
            (token_set_ratio, "fuzzy_token_set", distance),
        ]
        
        # Find the best ratio
        best_ratio, best_type, best_distance = max(ratios, key=lambda x: x[0])
        
        # Boost confidence for exact substring matches and adjust edit distance
        if query in candidate or candidate in query:
            best_ratio = min(1.0, best_ratio + 0.1)
            best_type = "fuzzy_substring"
            # For substring matches, use the minimum edit distance
            if query in candidate:
                # Query is substring of candidate - edit distance is length difference
                best_distance = len(candidate) - len(query)
            else:
                # Candidate is substring of query - edit distance is length difference
                best_distance = len(query) - len(candidate)
        
        return best_ratio, best_type, best_distance
    
    def get_edit_operations(self, query: str, target: str) -> str:
        """
        Get a description of edit operations needed to transform query to target.
        
        Args:
            query: Source string
            target: Target string
            
        Returns:
            Description of changes
        """
        if query == target:
            return "No changes"
        
        # Simple edit distance analysis
        distance = Levenshtein.distance(query, target)
        
        if len(query) < len(target):
            return f"Insert {len(target) - len(query)} character(s)"
        elif len(query) > len(target):
            return f"Delete {len(query) - len(target)} character(s)"
        else:
            return f"Substitute {distance} character(s)"
    
    def suggest_corrections(
        self, 
        query: str, 
        candidates: List[str], 
        max_suggestions: int = 5
    ) -> List[str]:
        """
        Suggest corrections for a query.
        
        Args:
            query: Query to get suggestions for
            candidates: List of candidate words
            max_suggestions: Maximum number of suggestions
            
        Returns:
            List of suggested corrections
        """
        if not query or not candidates:
            return []
        
        # Use rapidfuzz's extract function for suggestions
        suggestions = process.extract(
            query, 
            candidates, 
            limit=max_suggestions,
            scorer=fuzz.ratio
        )
        
        # Filter by threshold and return just the words
        return [suggestion[0] for suggestion in suggestions 
                if suggestion[1] >= self.threshold * 100]
