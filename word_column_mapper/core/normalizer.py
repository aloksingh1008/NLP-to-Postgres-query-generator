"""Text normalization utilities for consistent word processing."""

import re
import unicodedata
from typing import List, Set


class TextNormalizer:
    """Handles text normalization for consistent word processing."""
    
    def __init__(self) -> None:
        """Initialize the normalizer."""
        # Common delimiter patterns
        self.delimiter_patterns = [
            r'[-_]',  # hyphens and underscores
            r'\s+',   # whitespace
        ]
        
        # Compile regex patterns for performance
        self.delimiter_regex = re.compile('|'.join(self.delimiter_patterns))
        
    def normalize(self, text: str) -> str:
        """
        Normalize text for consistent processing.
        
        Args:
            text: Input text to normalize
            
        Returns:
            Normalized text
        """
        if not text:
            return ""
        
        # Convert to lowercase
        normalized = text.lower()
        
        # Normalize Unicode characters
        normalized = unicodedata.normalize('NFKD', normalized)
        
        # Replace delimiters with underscores
        normalized = self.delimiter_regex.sub('_', normalized)
        
        # Remove extra underscores
        normalized = re.sub(r'_+', '_', normalized)
        
        # Strip leading/trailing underscores
        normalized = normalized.strip('_')
        
        return normalized
    
    def generate_variants(self, text: str) -> Set[str]:
        """
        Generate common variants of a word for better matching.
        
        Args:
            text: Input text
            
        Returns:
            Set of normalized variants
        """
        variants = set()
        
        # Original normalized form
        normalized = self.normalize(text)
        variants.add(normalized)
        
        # Without delimiters
        no_delimiters = re.sub(r'[-_\s]+', '', text.lower())
        if no_delimiters:
            variants.add(no_delimiters)
        
        # With spaces instead of underscores
        with_spaces = re.sub(r'[-_]+', ' ', text.lower()).strip()
        if with_spaces:
            variants.add(with_spaces)
        
        # With hyphens instead of underscores
        with_hyphens = re.sub(r'[_]+', '-', text.lower()).strip()
        if with_hyphens:
            variants.add(with_hyphens)
        
        return variants
    
    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into words.
        
        Args:
            text: Input text
            
        Returns:
            List of tokens
        """
        if not text:
            return []
        
        # Normalize first
        normalized = self.normalize(text)
        
        # Split on delimiters
        tokens = [token for token in normalized.split('_') if token]
        
        return tokens
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two texts after normalization.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0 and 1
        """
        norm1 = self.normalize(text1)
        norm2 = self.normalize(text2)
        
        if norm1 == norm2:
            return 1.0
        
        # Simple character-based similarity
        if not norm1 or not norm2:
            return 0.0
        
        # Calculate Jaccard similarity of character sets
        set1 = set(norm1)
        set2 = set(norm2)
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
