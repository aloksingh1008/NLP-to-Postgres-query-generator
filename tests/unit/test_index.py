"""Unit tests for the index data structures."""

import pytest
import time
from word_column_mapper.core.index import ForwardIndex, ReverseIndex, IndexManager


class TestForwardIndex:
    """Test cases for the ForwardIndex class."""
    
    @pytest.fixture
    def forward_index(self):
        """Create a forward index instance for testing."""
        return ForwardIndex()
    
    def test_initialization(self, forward_index):
        """Test forward index initialization."""
        assert forward_index._index == {}
        assert forward_index._normalized_index == {}
        assert forward_index._stats["total_words"] == 0
        assert forward_index._stats["total_mappings"] == 0
        assert forward_index._stats["last_updated"] is None
    
    def test_add_mapping(self, forward_index):
        """Test adding word-to-column mappings."""
        forward_index.add_mapping("date", ["column1", "column2"])
        
        assert "date" in forward_index._index
        assert forward_index._index["date"] == ["column1", "column2"]
        assert forward_index._stats["total_words"] == 1
        assert forward_index._stats["total_mappings"] == 2
        assert forward_index._stats["last_updated"] is not None
    
    def test_get_columns_exact_match(self, forward_index):
        """Test getting columns with exact word match."""
        forward_index.add_mapping("date", ["column1", "column2"])
        
        columns = forward_index.get_columns("date")
        assert columns == ["column1", "column2"]
    
    def test_get_columns_normalized_match(self, forward_index):
        """Test getting columns with normalized word match."""
        forward_index.add_mapping("Date", ["column1", "column2"])
        
        # Should match with different case
        columns = forward_index.get_columns("date")
        assert columns == ["column1", "column2"]
    
    def test_get_columns_not_found(self, forward_index):
        """Test getting columns for non-existent word."""
        columns = forward_index.get_columns("nonexistent")
        assert columns is None
    
    def test_get_all_words(self, forward_index):
        """Test getting all words in the index."""
        forward_index.add_mapping("date", ["column1"])
        forward_index.add_mapping("start_date", ["column2"])
        
        words = forward_index.get_all_words()
        assert "date" in words
        assert "start_date" in words
        assert len(words) == 2
    
    def test_get_word_variants(self, forward_index):
        """Test getting word variants."""
        forward_index.add_mapping("Date", ["column1"])
        
        variants = forward_index.get_word_variants("date")
        assert "date" in variants
        assert "Date" in variants
    
    def test_remove_mapping(self, forward_index):
        """Test removing word mappings."""
        forward_index.add_mapping("date", ["column1", "column2"])
        
        success = forward_index.remove_mapping("date")
        assert success is True
        assert "date" not in forward_index._index
        assert forward_index._stats["total_words"] == 0
    
    def test_remove_mapping_not_found(self, forward_index):
        """Test removing non-existent word mapping."""
        success = forward_index.remove_mapping("nonexistent")
        assert success is False
    
    def test_clear(self, forward_index):
        """Test clearing all mappings."""
        forward_index.add_mapping("date", ["column1"])
        forward_index.clear()
        
        assert forward_index._index == {}
        assert forward_index._normalized_index == {}
        assert forward_index._stats["total_words"] == 0
    
    def test_empty_mapping_handling(self, forward_index):
        """Test handling of empty mappings."""
        # Empty word
        forward_index.add_mapping("", ["column1"])
        assert forward_index._stats["total_words"] == 0
        
        # Empty columns
        forward_index.add_mapping("date", [])
        assert forward_index._stats["total_words"] == 0
        
        # None values
        forward_index.add_mapping(None, ["column1"])
        assert forward_index._stats["total_words"] == 0


class TestReverseIndex:
    """Test cases for the ReverseIndex class."""
    
    @pytest.fixture
    def reverse_index(self):
        """Create a reverse index instance for testing."""
        return ReverseIndex()
    
    def test_initialization(self, reverse_index):
        """Test reverse index initialization."""
        assert reverse_index._index == {}
        assert reverse_index._stats["total_columns"] == 0
        assert reverse_index._stats["total_mappings"] == 0
        assert reverse_index._stats["last_updated"] is None
    
    def test_add_mapping(self, reverse_index):
        """Test adding word-to-column mappings to reverse index."""
        reverse_index.add_mapping("date", ["column1", "column2"])
        
        assert "column1" in reverse_index._index
        assert "column2" in reverse_index._index
        assert "date" in reverse_index._index["column1"]
        assert "date" in reverse_index._index["column2"]
        assert reverse_index._stats["total_columns"] == 2
        assert reverse_index._stats["total_mappings"] == 2
    
    def test_get_words(self, reverse_index):
        """Test getting words for a column."""
        reverse_index.add_mapping("date", ["column1"])
        reverse_index.add_mapping("start_date", ["column1"])
        
        words = reverse_index.get_words("column1")
        assert "date" in words
        assert "start_date" in words
        assert len(words) == 2
    
    def test_get_words_not_found(self, reverse_index):
        """Test getting words for non-existent column."""
        words = reverse_index.get_words("nonexistent")
        assert words is None
    
    def test_get_all_columns(self, reverse_index):
        """Test getting all columns in the index."""
        reverse_index.add_mapping("date", ["column1", "column2"])
        
        columns = reverse_index.get_all_columns()
        assert "column1" in columns
        assert "column2" in columns
        assert len(columns) == 2
    
    def test_remove_mapping(self, reverse_index):
        """Test removing word mappings from reverse index."""
        reverse_index.add_mapping("date", ["column1", "column2"])
        reverse_index.remove_mapping("date", ["column1", "column2"])
        
        assert "date" not in reverse_index._index["column1"]
        assert "date" not in reverse_index._index["column2"]
        assert reverse_index._stats["total_columns"] == 0
    
    def test_clear(self, reverse_index):
        """Test clearing all mappings."""
        reverse_index.add_mapping("date", ["column1"])
        reverse_index.clear()
        
        assert reverse_index._index == {}
        assert reverse_index._stats["total_columns"] == 0
    
    def test_duplicate_word_handling(self, reverse_index):
        """Test handling of duplicate words for the same column."""
        reverse_index.add_mapping("date", ["column1"])
        reverse_index.add_mapping("date", ["column1"])  # Duplicate
        
        words = reverse_index.get_words("column1")
        assert words.count("date") == 1  # Should not have duplicates


class TestIndexManager:
    """Test cases for the IndexManager class."""
    
    @pytest.fixture
    def index_manager(self):
        """Create an index manager instance for testing."""
        return IndexManager()
    
    def test_initialization(self, index_manager):
        """Test index manager initialization."""
        assert index_manager.forward_index is not None
        assert index_manager.reverse_index is not None
        assert index_manager._lock is False
    
    def test_add_mapping(self, index_manager):
        """Test adding mappings to both indexes."""
        index_manager.add_mapping("date", ["column1", "column2"])
        
        # Check forward index
        assert index_manager.forward_index.get_columns("date") == ["column1", "column2"]
        
        # Check reverse index
        assert "date" in index_manager.reverse_index.get_words("column1")
        assert "date" in index_manager.reverse_index.get_words("column2")
    
    def test_remove_mapping(self, index_manager):
        """Test removing mappings from both indexes."""
        index_manager.add_mapping("date", ["column1", "column2"])
        
        success = index_manager.remove_mapping("date")
        assert success is True
        
        # Check forward index
        assert index_manager.forward_index.get_columns("date") is None
        
        # Check reverse index
        assert index_manager.reverse_index.get_words("column1") is None
        assert index_manager.reverse_index.get_words("column2") is None
    
    def test_update_mapping(self, index_manager):
        """Test updating mappings in both indexes."""
        index_manager.add_mapping("date", ["column1"])
        index_manager.update_mapping("date", ["column2", "column3"])
        
        # Check forward index
        assert index_manager.forward_index.get_columns("date") == ["column2", "column3"]
        
        # Check reverse index
        assert index_manager.reverse_index.get_words("column1") is None
        assert "date" in index_manager.reverse_index.get_words("column2")
        assert "date" in index_manager.reverse_index.get_words("column3")
    
    def test_clear(self, index_manager):
        """Test clearing both indexes."""
        index_manager.add_mapping("date", ["column1"])
        index_manager.clear()
        
        assert index_manager.forward_index.get_columns("date") is None
        assert index_manager.reverse_index.get_words("column1") is None
    
    def test_get_stats(self, index_manager):
        """Test getting combined statistics."""
        index_manager.add_mapping("date", ["column1", "column2"])
        
        stats = index_manager.get_stats()
        
        assert "forward_index" in stats
        assert "reverse_index" in stats
        assert "total_unique_columns" in stats
        assert stats["total_unique_columns"] == 2
    
    def test_concurrent_access_protection(self, index_manager):
        """Test that concurrent access is protected."""
        # Test that operations work normally
        index_manager.add_mapping("date", ["column1"])
        assert index_manager.forward_index.get_columns("date") == ["column1"]
        
        # Test removal
        success = index_manager.remove_mapping("date")
        assert success is True
        assert index_manager.forward_index.get_columns("date") is None
