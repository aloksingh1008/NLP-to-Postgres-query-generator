"""Performance benchmarks for the Word Column Mapper."""

import pytest
import time
import random
import string
from word_column_mapper.core.engine import SearchEngine


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""
    
    @pytest.fixture
    def large_engine(self):
        """Create a search engine with a large dataset for performance testing."""
        engine = SearchEngine(fuzzy_threshold=0.6)
        
        # Generate a large dataset
        mappings = {}
        for i in range(1000):
            word = f"word_{i}"
            columns = [f"column_{j}" for j in range(random.randint(1, 5))]
            mappings[word] = columns
        
        # Add some realistic mappings
        realistic_mappings = {
            "date": ["column3423", "column5738", "column3846", "column4632"],
            "start_date": ["column5738", "column4632"], 
            "end_date": ["column3423", "column3846"],
            "user_id": ["column1001", "column1002", "column1003"],
            "customer_id": ["column1001", "column2001"],
            "order_id": ["column2001", "column2002", "column2003"],
            "product_id": ["column3001", "column3002"],
            "created_at": ["column5738", "column7891"],
            "updated_at": ["column3846", "column7891"], 
            "timestamp": ["column3423", "column5738", "column7891"],
            "email": ["column4001", "column4002"],
            "phone": ["column5001", "column5002"],
            "address": ["column6001", "column6002", "column6003"],
            "name": ["column7001", "column7002"],
            "description": ["column8001", "column8002", "column8003"]
        }
        
        mappings.update(realistic_mappings)
        engine.load_mappings(mappings)
        
        return engine
    
    def test_exact_match_performance(self, large_engine, benchmark):
        """Benchmark exact match performance."""
        def exact_search():
            return large_engine.search("date")
        
        result = benchmark(exact_search)
        assert result.exact_match is True
        assert result.execution_time_ms < 1.0  # Should be under 1ms
    
    def test_fuzzy_match_performance(self, large_engine, benchmark):
        """Benchmark fuzzy match performance."""
        def fuzzy_search():
            return large_engine.search("dat")  # Single typo
        
        result = benchmark(fuzzy_search)
        assert result.total_results > 0
        assert result.execution_time_ms < 10.0  # Should be under 10ms
    
    def test_multiple_typo_performance(self, large_engine, benchmark):
        """Benchmark multiple typo performance."""
        def multiple_typo_search():
            return large_engine.search("strt_dte")  # Multiple typos
        
        result = benchmark(multiple_typo_search)
        assert result.total_results > 0
        assert result.execution_time_ms < 50.0  # Should be under 50ms
    
    def test_reverse_lookup_performance(self, large_engine, benchmark):
        """Benchmark reverse lookup performance."""
        def reverse_lookup():
            return large_engine.reverse_search("column5738")
        
        result = benchmark(reverse_lookup)
        assert result is not None
        assert result["execution_time_ms"] < 5.0  # Should be under 5ms
    
    def test_intersection_performance(self, large_engine, benchmark):
        """Benchmark intersection operation performance."""
        def intersection_search():
            return large_engine.intersection_search(["date", "start_date"])
        
        result = benchmark(intersection_search)
        assert result is not None
        assert result["execution_time_ms"] < 10.0  # Should be under 10ms
    
    def test_union_performance(self, large_engine, benchmark):
        """Benchmark union operation performance."""
        def union_search():
            return large_engine.union_search(["start_date", "end_date", "user_id"])
        
        result = benchmark(union_search)
        assert result is not None
        assert result["execution_time_ms"] < 15.0  # Should be under 15ms
    
    def test_bulk_search_performance(self, large_engine):
        """Test performance of multiple searches in sequence."""
        queries = [
            "date", "dat", "start_date", "start_dat", "end_date", "end_dat",
            "user_id", "user", "customer_id", "customer", "order_id", "order",
            "product_id", "product", "created_at", "created", "updated_at", "updated"
        ]
        
        start_time = time.time()
        results = []
        
        for query in queries:
            result = large_engine.search(query)
            results.append(result)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should handle 18 queries in under 1 second
        assert total_time < 1.0
        assert len(results) == 18
        
        # Check that most queries returned results
        successful_queries = sum(1 for r in results if r.total_results > 0)
        assert successful_queries >= 15  # At least 15 out of 18 should succeed
    
    def test_memory_usage(self, large_engine):
        """Test memory usage with large dataset."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform some operations
        for i in range(100):
            large_engine.search(f"word_{i}")
        
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = memory_after - memory_before
        
        # Memory increase should be reasonable (< 100MB for 100 operations)
        assert memory_increase < 100
    
    def test_concurrent_access_simulation(self, large_engine):
        """Simulate concurrent access patterns."""
        import threading
        import queue
        
        results_queue = queue.Queue()
        errors_queue = queue.Queue()
        
        def search_worker(queries):
            """Worker function for concurrent searches."""
            for query in queries:
                try:
                    result = large_engine.search(query)
                    results_queue.put((query, result))
                except Exception as e:
                    errors_queue.put((query, str(e)))
        
        # Create multiple threads with different query sets
        threads = []
        query_sets = [
            ["date", "start_date", "end_date"],
            ["user_id", "customer_id", "order_id"],
            ["product_id", "created_at", "updated_at"],
            ["email", "phone", "address"],
            ["name", "description", "timestamp"]
        ]
        
        start_time = time.time()
        
        for queries in query_sets:
            thread = threading.Thread(target=search_worker, args=(queries,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete in reasonable time
        assert total_time < 2.0
        
        # Check results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())
        
        errors = []
        while not errors_queue.empty():
            errors.append(errors_queue.get())
        
        # Should have results and no errors
        assert len(results) == 15  # 5 threads * 3 queries each
        assert len(errors) == 0
    
    def test_large_query_performance(self, large_engine):
        """Test performance with large queries."""
        # Test with very long query
        long_query = "very_long_word_" + "x" * 50
        
        start_time = time.time()
        result = large_engine.search(long_query)
        end_time = time.time()
        
        # Should handle long queries gracefully
        assert (end_time - start_time) < 1.0
        assert result.total_results == 0  # No match expected
    
    def test_special_characters_performance(self, large_engine):
        """Test performance with special characters."""
        special_queries = [
            "date-with-dashes",
            "date_with_underscores", 
            "date with spaces",
            "date.with.dots",
            "date@with@symbols"
        ]
        
        start_time = time.time()
        results = []
        
        for query in special_queries:
            result = large_engine.search(query)
            results.append(result)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should handle special characters efficiently
        assert total_time < 0.5
        assert len(results) == 5
    
    def test_no_match_performance(self, large_engine, benchmark):
        """Benchmark no-match queries performance."""
        def no_match_search():
            return large_engine.search("nonexistent_word_12345")
        
        result = benchmark(no_match_search)
        assert result.total_results == 0
        assert result.execution_time_ms < 5.0  # Should be fast even for no matches
    
    def test_case_variations_performance(self, large_engine):
        """Test performance with various case combinations."""
        case_variations = [
            "DATE", "Date", "date", "DaTe", "dAtE",
            "START_DATE", "Start_Date", "start_date", "StArT_dAtE"
        ]
        
        start_time = time.time()
        results = []
        
        for query in case_variations:
            result = large_engine.search(query)
            results.append(result)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should handle case variations efficiently
        assert total_time < 0.3
        assert len(results) == 8
        
        # Most should be exact matches
        exact_matches = sum(1 for r in results if r.exact_match)
        assert exact_matches >= 6  # At least 6 should be exact matches
    
    def test_statistics_accuracy(self, large_engine):
        """Test that performance statistics are accurate."""
        # Perform various types of searches
        large_engine.search("date")  # Exact match
        large_engine.search("dat")   # Fuzzy match
        large_engine.search("xyz")   # No match
        large_engine.search("start_date")  # Exact match
        large_engine.search("start_dat")   # Fuzzy match
        
        stats = large_engine.get_stats()
        
        assert stats["total_queries"] == 5
        assert stats["exact_matches"] == 2
        assert stats["fuzzy_matches"] == 2
        assert stats["no_matches"] == 1
        assert stats["exact_match_rate"] == 0.4
        assert stats["fuzzy_match_rate"] == 0.4
        assert stats["no_match_rate"] == 0.2
        assert stats["average_execution_time_ms"] > 0
