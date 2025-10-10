"""Unit tests for the fuzzy matcher functionality."""

import pytest
from word_column_mapper.core.fuzzy_matcher import FuzzyMatcher


class TestFuzzyMatcher:
    """Test cases for the FuzzyMatcher class."""
    
    @pytest.fixture
    def matcher(self):
        """Create a fuzzy matcher instance for testing."""
        return FuzzyMatcher(threshold=0.6)
    
    @pytest.fixture
    def sample_candidates(self):
        """Sample candidate words for testing."""
        return [
            "date", "start_date", "end_date", "user_id", "customer_id",
            "created_at", "updated_at", "timestamp", "order_id", "product_id"
        ]
    
    def test_matcher_initialization(self, matcher):
        """Test fuzzy matcher initialization."""
        assert matcher.threshold == 0.6
        assert matcher.normalizer is not None
    
    def test_exact_match(self, matcher, sample_candidates):
        """Test exact matching."""
        result = matcher.find_best_match("date", sample_candidates)
        
        assert result is not None
        word, confidence, match_type, edit_distance = result
        assert word == "date"
        assert confidence == 1.0
        assert match_type == "exact"
        assert edit_distance == 0
    
    def test_single_character_typo(self, matcher, sample_candidates):
        """Test single character typo correction."""
        result = matcher.find_best_match("dat", sample_candidates)
        
        assert result is not None
        word, confidence, match_type, edit_distance = result
        assert word == "date"
        assert confidence > 0.7
        assert match_type in ["fuzzy_levenshtein", "fuzzy_substring"]
        assert edit_distance == 1
    
    def test_multiple_character_typos(self, matcher, sample_candidates):
        """Test multiple character typo correction."""
        result = matcher.find_best_match("strt_dte", sample_candidates)
        
        assert result is not None
        word, confidence, match_type, edit_distance = result
        assert word == "start_date"
        assert confidence > 0.5
        assert edit_distance > 1
    
    def test_transposition_error(self, matcher, sample_candidates):
        """Test transposition error correction."""
        result = matcher.find_best_match("dtae", sample_candidates)
        
        assert result is not None
        word, confidence, match_type, edit_distance = result
        assert word == "date"
        assert confidence > 0.6
        assert edit_distance == 2  # Transposition
    
    def test_insertion_error(self, matcher, sample_candidates):
        """Test insertion error correction."""
        result = matcher.find_best_match("datte", sample_candidates)
        
        assert result is not None
        word, confidence, match_type, edit_distance = result
        assert word == "date"
        assert confidence > 0.6
        assert edit_distance == 1
    
    def test_deletion_error(self, matcher, sample_candidates):
        """Test deletion error correction."""
        result = matcher.find_best_match("dt", sample_candidates)
        
        assert result is not None
        word, confidence, match_type, edit_distance = result
        assert word == "date"
        assert confidence > 0.5
        assert edit_distance == 2
    
    def test_no_match_below_threshold(self, matcher, sample_candidates):
        """Test no match when confidence is below threshold."""
        result = matcher.find_best_match("xyz123", sample_candidates)
        
        assert result is None
    
    def test_custom_threshold(self, matcher, sample_candidates):
        """Test custom threshold parameter."""
        # High threshold should be more strict
        result_strict = matcher.find_best_match("dat", sample_candidates, threshold=0.9)
        
        # Low threshold should be more permissive
        result_permissive = matcher.find_best_match("dat", sample_candidates, threshold=0.3)
        
        # Both should find matches, but with different confidence requirements
        assert result_strict is not None or result_permissive is not None
    
    def test_multiple_matches(self, matcher, sample_candidates):
        """Test finding multiple matches."""
        results = matcher.find_multiple_matches("dat", sample_candidates, max_results=5)
        
        assert len(results) > 0
        assert len(results) <= 5
        
        # Results should be sorted by confidence (descending)
        for i in range(len(results) - 1):
            assert results[i][1] >= results[i + 1][1]
    
    def test_empty_query(self, matcher, sample_candidates):
        """Test handling of empty query."""
        result = matcher.find_best_match("", sample_candidates)
        assert result is None
    
    def test_empty_candidates(self, matcher):
        """Test handling of empty candidates list."""
        result = matcher.find_best_match("date", [])
        assert result is None
    
    def test_edit_operations_description(self, matcher):
        """Test edit operations description."""
        # Test insertion
        desc = matcher.get_edit_operations("cat", "cats")
        assert "Insert" in desc
        
        # Test deletion
        desc = matcher.get_edit_operations("cats", "cat")
        assert "Delete" in desc
        
        # Test substitution
        desc = matcher.get_edit_operations("cat", "bat")
        assert "Substitute" in desc
        
        # Test no changes
        desc = matcher.get_edit_operations("cat", "cat")
        assert desc == "No changes"
    
    def test_suggestions(self, matcher, sample_candidates):
        """Test suggestion generation."""
        suggestions = matcher.suggest_corrections("dat", sample_candidates, max_suggestions=3)
        
        assert len(suggestions) <= 3
        assert "date" in suggestions
    
    def test_case_insensitive_matching(self, matcher, sample_candidates):
        """Test case-insensitive matching."""
        result = matcher.find_best_match("DATE", sample_candidates)
        
        assert result is not None
        word, confidence, match_type, edit_distance = result
        assert word == "date"
        assert confidence == 1.0
        assert match_type == "exact"
    
    def test_delimiter_handling(self, matcher, sample_candidates):
        """Test delimiter handling in matching."""
        # Test with different delimiters
        test_cases = [
            ("start-date", "start_date"),
            ("start date", "start_date"),
            ("startdate", "start_date")
        ]
        
        for query, expected in test_cases:
            result = matcher.find_best_match(query, sample_candidates)
            if result:
                word, confidence, match_type, edit_distance = result
                # Should find start_date or a reasonable match
                assert word in sample_candidates
                assert confidence > 0.5
    
    def test_confidence_score_range(self, matcher, sample_candidates):
        """Test that confidence scores are in valid range."""
        results = matcher.find_multiple_matches("dat", sample_candidates, max_results=10)
        
        for word, confidence, match_type, edit_distance in results:
            assert 0.0 <= confidence <= 1.0
    
    def test_match_type_variety(self, matcher, sample_candidates):
        """Test that different match types are returned."""
        results = matcher.find_multiple_matches("dat", sample_candidates, max_results=10)
        
        match_types = set(result[2] for result in results)
        assert len(match_types) > 1  # Should have multiple match types
    
    def test_performance_with_large_candidate_set(self, matcher):
        """Test performance with a large set of candidates."""
        # Generate a large set of candidates
        large_candidates = [f"word_{i}" for i in range(1000)]
        large_candidates.extend(["date", "start_date", "end_date"])
        
        import time
        start_time = time.time()
        result = matcher.find_best_match("dat", large_candidates)
        end_time = time.time()
        
        # Should complete in reasonable time (< 100ms)
        assert (end_time - start_time) < 0.1
        assert result is not None
