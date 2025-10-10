"""Index data structures for efficient word-to-column mapping."""

import time
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict

from .normalizer import TextNormalizer


class ForwardIndex:
    """Forward index mapping words to column arrays."""
    
    def __init__(self) -> None:
        """Initialize the forward index."""
        self._index: Dict[str, List[str]] = {}
        self._normalized_index: Dict[str, str] = {}  # normalized -> original
        self.normalizer = TextNormalizer()
        self._stats = {
            "total_words": 0,
            "total_mappings": 0,
            "last_updated": None
        }
    
    def add_mapping(self, word: str, columns: List[str]) -> None:
        """
        Add a word-to-columns mapping.
        
        Args:
            word: The word to map
            columns: List of column identifiers
        """
        if not word or not columns:
            return
        
        # Normalize the word
        normalized = self.normalizer.normalize(word)
        
        # Store the mapping
        self._index[word] = columns.copy()
        self._normalized_index[normalized] = word
        
        # Update statistics
        self._stats["total_words"] = len(self._index)
        self._stats["total_mappings"] += len(columns)
        self._stats["last_updated"] = time.time()
    
    def get_columns(self, word: str) -> Optional[List[str]]:
        """
        Get columns for a word.
        
        Args:
            word: The word to look up
            
        Returns:
            List of columns or None if not found
        """
        # Try exact match first
        if word in self._index:
            return self._index[word].copy()
        
        # Try normalized match
        normalized = self.normalizer.normalize(word)
        if normalized in self._normalized_index:
            original_word = self._normalized_index[normalized]
            return self._index[original_word].copy()
        
        return None
    
    def get_all_words(self) -> List[str]:
        """Get all words in the index."""
        return list(self._index.keys())
    
    def get_word_variants(self, word: str) -> Set[str]:
        """
        Get all variants of a word (including normalized forms).
        
        Args:
            word: The word to get variants for
            
        Returns:
            Set of word variants
        """
        variants = set()
        
        # Add original word
        variants.add(word)
        
        # Add normalized form
        normalized = self.normalizer.normalize(word)
        variants.add(normalized)
        
        # Add all words that normalize to the same form
        for norm_word, original_word in self._normalized_index.items():
            if norm_word == normalized:
                variants.add(original_word)
        
        return variants
    
    def remove_mapping(self, word: str) -> bool:
        """
        Remove a word mapping.
        
        Args:
            word: The word to remove
            
        Returns:
            True if removed, False if not found
        """
        if word in self._index:
            del self._index[word]
            
            # Remove from normalized index
            normalized = self.normalizer.normalize(word)
            if normalized in self._normalized_index:
                del self._normalized_index[normalized]
            
            # Update statistics
            self._stats["total_words"] = len(self._index)
            self._stats["last_updated"] = time.time()
            
            return True
        
        return False
    
    def clear(self) -> None:
        """Clear all mappings."""
        self._index.clear()
        self._normalized_index.clear()
        self._stats = {
            "total_words": 0,
            "total_mappings": 0,
            "last_updated": None
        }
    
    def get_stats(self) -> Dict[str, any]:
        """Get index statistics."""
        return self._stats.copy()


class ReverseIndex:
    """Reverse index mapping columns to word arrays."""
    
    def __init__(self) -> None:
        """Initialize the reverse index."""
        self._index: Dict[str, List[str]] = defaultdict(list)
        self._stats = {
            "total_columns": 0,
            "total_mappings": 0,
            "last_updated": None
        }
    
    def add_mapping(self, word: str, columns: List[str]) -> None:
        """
        Add word-to-columns mapping to reverse index.
        
        Args:
            word: The word
            columns: List of column identifiers
        """
        if not word or not columns:
            return
        
        for column in columns:
            if word not in self._index[column]:
                self._index[column].append(word)
        
        # Update statistics
        self._stats["total_columns"] = len(self._index)
        self._stats["total_mappings"] = sum(len(words) for words in self._index.values())
        self._stats["last_updated"] = time.time()
    
    def get_words(self, column: str) -> Optional[List[str]]:
        """
        Get words for a column.
        
        Args:
            column: The column identifier
            
        Returns:
            List of words or None if not found
        """
        if column in self._index:
            return self._index[column].copy()
        return None
    
    def get_all_columns(self) -> List[str]:
        """Get all columns in the index."""
        return list(self._index.keys())
    
    def remove_mapping(self, word: str, columns: List[str]) -> None:
        """
        Remove word-to-columns mapping from reverse index.
        
        Args:
            word: The word to remove
            columns: List of column identifiers
        """
        for column in columns:
            if column in self._index and word in self._index[column]:
                self._index[column].remove(word)
                
                # Remove column if no words left
                if not self._index[column]:
                    del self._index[column]
        
        # Update statistics
        self._stats["total_columns"] = len(self._index)
        self._stats["total_mappings"] = sum(len(words) for words in self._index.values())
        self._stats["last_updated"] = time.time()
    
    def clear(self) -> None:
        """Clear all mappings."""
        self._index.clear()
        self._stats = {
            "total_columns": 0,
            "total_mappings": 0,
            "last_updated": None
        }
    
    def get_stats(self) -> Dict[str, any]:
        """Get index statistics."""
        return self._stats.copy()


class IndexManager:
    """Manages both forward and reverse indexes with consistency."""
    
    def __init__(self) -> None:
        """Initialize the index manager."""
        self.forward_index = ForwardIndex()
        self.reverse_index = ReverseIndex()
        self._lock = False  # Simple lock for consistency
    
    def add_mapping(self, word: str, columns: List[str]) -> None:
        """
        Add a word-to-columns mapping to both indexes.
        
        Args:
            word: The word to map
            columns: List of column identifiers
        """
        if self._lock:
            return
        
        self._lock = True
        try:
            # Add to forward index
            self.forward_index.add_mapping(word, columns)
            
            # Add to reverse index
            self.reverse_index.add_mapping(word, columns)
        finally:
            self._lock = False
    
    def remove_mapping(self, word: str) -> bool:
        """
        Remove a word mapping from both indexes.
        
        Args:
            word: The word to remove
            
        Returns:
            True if removed, False if not found
        """
        if self._lock:
            return False
        
        # Get columns before removing
        columns = self.forward_index.get_columns(word)
        if not columns:
            return False
        
        self._lock = True
        try:
            # Remove from forward index
            self.forward_index.remove_mapping(word)
            
            # Remove from reverse index
            self.reverse_index.remove_mapping(word, columns)
            
            return True
        finally:
            self._lock = False
    
    def update_mapping(self, word: str, columns: List[str]) -> None:
        """
        Update a word mapping in both indexes.
        
        Args:
            word: The word to update
            columns: New list of column identifiers
        """
        # Remove old mapping
        self.remove_mapping(word)
        
        # Add new mapping
        self.add_mapping(word, columns)
    
    def clear(self) -> None:
        """Clear all indexes."""
        self.forward_index.clear()
        self.reverse_index.clear()
    
    def get_stats(self) -> Dict[str, any]:
        """Get combined statistics from both indexes."""
        forward_stats = self.forward_index.get_stats()
        reverse_stats = self.reverse_index.get_stats()
        
        return {
            "forward_index": forward_stats,
            "reverse_index": reverse_stats,
            "total_unique_columns": len(self.reverse_index.get_all_columns())
        }
