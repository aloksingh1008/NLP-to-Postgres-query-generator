"""Unit tests for the search engine core functionality."""

import pytest
import time
from word_column_mapper.core.engine import SearchEngine
from word_column_mapper.models.response import SearchResult


class TestSearchEngine:
    """Test cases for the SearchEngine class."""
    
    @pytest.fixture
    def engine(self):
        """Create a search engine instance for testing."""
        return SearchEngine(fuzzy_threshold=0.6)
    
    @pytest.fixture
    def sample_mappings(self):
        """Sample word-to-column mappings for testing."""
        return {
            "date": ["column3423", "column5738", "column3846", "column4632"],
            "start_date": ["column5738", "column4632"], 
            "end_date": ["column3423", "column3846"],
            "user_id": ["column1001", "column1002"],
            "customer_id": ["column1001", "column2001"]
        }
    
    def test_engine_initialization(self, engine):
        """Test search engine initialization."""
        assert engine.fuzzy_threshold == 0.6
        assert engine._stats["total_queries"] == 0
        assert engine._stats["exact_matches"] == 0
        assert engine._stats["fuzzy_matches"] == 0
        assert engine._stats["no_matches"] == 0
    
    def test_load_mappings(self, engine, sample_mappings):
        """Test loading word-to-column mappings."""
        engine.load_mappings(sample_mappings)
        
        # Check forward index
        assert engine.index_manager.forward_index.get_columns("date") == sample_mappings["date"]
        assert engine.index_manager.forward_index.get_columns("start_date") == sample_mappings["start_date"]
        
        # Check reverse index
        assert "date" in engine.index_manager.reverse_index.get_words("column3423")
        assert "start_date" in engine.index_manager.reverse_index.get_words("column5738")
    
    def test_exact_search(self, engine, sample_mappings):
        """Test exact word matching."""
        engine.load_mappings(sample_mappings)
        
        result = engine.search("date")
        
        assert result.exact_match is True
        assert result.total_results == 1
        assert result.results[0].word == "date"
        assert result.results[0].confidence == 1.0
        assert result.results[0].match_type == "exact"
        assert result.results[0].columns == sample_mappings["date"]
        assert result.execution_time_ms < 10.0  # Should be very fast
    
    def test_fuzzy_search_single_typo(self, engine, sample_mappings):
        """Test fuzzy matching with single character typo."""
        engine.load_mappings(sample_mappings)
        
        result = engine.search("dat")  # Missing 'e'
        
        assert result.exact_match is False
        assert result.total_results > 0
        assert result.results[0].word == "date"
        assert result.results[0].confidence > 0.7
        assert result.results[0].match_type in ["fuzzy_levenshtein", "fuzzy_substring"]
    
    def test_fuzzy_search_multiple_typos(self, engine, sample_mappings):
        """Test fuzzy matching with multiple typos."""
        engine.load_mappings(sample_mappings)
        
        result = engine.search("strt_dte")  # Multiple typos for "start_date"
        
        assert result.exact_match is False
        assert result.total_results > 0
        # Should find start_date with reasonable confidence
        start_date_result = next((r for r in result.results if r.word == "start_date"), None)
        assert start_date_result is not None
        assert start_date_result.confidence > 0.5
    
    def test_case_insensitive_search(self, engine, sample_mappings):
        """Test case-insensitive search."""
        engine.load_mappings(sample_mappings)
        
        # Test various case combinations
        test_cases = ["Date", "DATE", "Start_Date", "START_DATE", "End_Date"]
        
        for query in test_cases:
            result = engine.search(query)
            assert result.exact_match is True
            assert result.total_results == 1
            assert result.results[0].confidence == 1.0
    
    def test_no_match_search(self, engine, sample_mappings):
        """Test search with no matches."""
        engine.load_mappings(sample_mappings)
        
        result = engine.search("xyz123")
        
        assert result.exact_match is False
        assert result.total_results == 0
        assert result.results == []
        assert result.suggestions is not None
        # Suggestions might be empty if no similar words found
        assert isinstance(result.suggestions, list)
    
    def test_reverse_search(self, engine, sample_mappings):
        """Test reverse lookup functionality."""
        engine.load_mappings(sample_mappings)
        
        result = engine.reverse_search("column5738")
        
        assert result is not None
        assert "date" in result["words"]
        assert "start_date" in result["words"]
        assert result["total_mappings"] == 2
        assert result["execution_time_ms"] < 10.0
    
    def test_reverse_search_not_found(self, engine, sample_mappings):
        """Test reverse lookup with non-existent column."""
        engine.load_mappings(sample_mappings)
        
        result = engine.reverse_search("column9999")
        assert result is None
    
    def test_intersection_search(self, engine, sample_mappings):
        """Test intersection operation."""
        engine.load_mappings(sample_mappings)
        
        result = engine.intersection_search(["date", "start_date"])
        
        assert result is not None
        assert result["operation"] == "AND"
        assert "column5738" in result["intersection_columns"]
        assert "column4632" in result["intersection_columns"]
        assert result["total_common_columns"] == 2
    
    def test_union_search(self, engine, sample_mappings):
        """Test union operation."""
        engine.load_mappings(sample_mappings)
        
        result = engine.union_search(["start_date", "end_date"])
        
        assert result is not None
        assert result["operation"] == "OR"
        assert len(result["union_columns"]) == 4
        assert "column3423" in result["union_columns"]
        assert "column3846" in result["union_columns"]
        assert "column4632" in result["union_columns"]
        assert "column5738" in result["union_columns"]
    
    def test_performance_metrics(self, engine, sample_mappings):
        """Test performance metrics tracking."""
        engine.load_mappings(sample_mappings)
        
        # Perform some searches
        engine.search("date")
        engine.search("dat")
        engine.search("xyz123")
        
        stats = engine.get_stats()
        
        assert stats["total_queries"] == 3
        assert stats["exact_matches"] == 1
        assert stats["fuzzy_matches"] == 1
        assert stats["no_matches"] == 1
        assert stats["average_execution_time_ms"] > 0
        assert stats["exact_match_rate"] == 1/3
        assert stats["fuzzy_match_rate"] == 1/3
        assert stats["no_match_rate"] == 1/3
    
    def test_empty_query(self, engine, sample_mappings):
        """Test handling of empty queries."""
        engine.load_mappings(sample_mappings)
        
        result = engine.search("")
        
        assert result.query == ""
        assert result.total_results == 0
        assert result.results == []
        assert result.execution_time_ms >= 0
    
    def test_whitespace_query(self, engine, sample_mappings):
        """Test handling of whitespace-only queries."""
        engine.load_mappings(sample_mappings)
        
        result = engine.search("   ")
        
        assert result.query == "   "
        assert result.total_results == 0
        assert result.results == []
    
    def test_clear_functionality(self, engine, sample_mappings):
        """Test clearing all data."""
        engine.load_mappings(sample_mappings)
        
        # Verify data is loaded
        assert engine.index_manager.forward_index.get_columns("date") is not None
        
        # Clear and verify
        engine.clear()
        assert engine.index_manager.forward_index.get_columns("date") is None
        assert engine._stats["total_queries"] == 0
    
    def test_custom_fuzzy_threshold(self, engine, sample_mappings):
        """Test custom fuzzy matching threshold."""
        engine.load_mappings(sample_mappings)
        
        # Test with high threshold (should be more strict)
        result_strict = engine.search("dat", fuzzy_threshold=0.9)
        
        # Test with low threshold (should be more permissive)
        result_permissive = engine.search("dat", fuzzy_threshold=0.3)
        
        # Permissive should return more results
        assert result_permissive.total_results >= result_strict.total_results
    
    def test_max_results_limit(self, engine, sample_mappings):
        """Test maximum results limit."""
        engine.load_mappings(sample_mappings)
        
        # Search with typo that could match multiple words
        result = engine.search("dat", max_results=2)
        
        assert result.total_results <= 2
    
    def test_confidence_scores(self, engine, sample_mappings):
        """Test confidence score calculations."""
        engine.load_mappings(sample_mappings)
        
        # Exact match should have confidence 1.0
        exact_result = engine.search("date")
        assert exact_result.results[0].confidence == 1.0
        
        # Fuzzy match should have confidence <= 1.0 (substring matches can be 1.0)
        fuzzy_result = engine.search("dat")
        assert fuzzy_result.results[0].confidence <= 1.0
        assert fuzzy_result.results[0].confidence > 0.0
    
    def test_edit_distance_calculation(self, engine, sample_mappings):
        """Test edit distance calculations."""
        engine.load_mappings(sample_mappings)
        
        result = engine.search("dat")  # Missing 'e' from "date"
        
        # Should have edit distance of 1
        date_result = next((r for r in result.results if r.word == "date"), None)
        assert date_result is not None
        assert date_result.edit_distance == 1
    
    def test_changes_description(self, engine, sample_mappings):
        """Test changes description for fuzzy matches."""
        engine.load_mappings(sample_mappings)
        
        result = engine.search("dat")  # Missing 'e' from "date"
        
        date_result = next((r for r in result.results if r.word == "date"), None)
        assert date_result is not None
        assert date_result.changes is not None
        assert "Insert" in date_result.changes or "Delete" in date_result.changes or "Substitute" in date_result.changes
