#!/usr/bin/env python3
"""Basic test script to verify the search engine functionality."""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from word_column_mapper.core.engine import SearchEngine


def test_basic_functionality():
    """Test basic search engine functionality."""
    print("🚀 Testing Word Column Mapper Search Engine")
    print("=" * 50)
    
    # Initialize search engine
    engine = SearchEngine(fuzzy_threshold=0.6)
    
    # Load sample data
    sample_mappings = {
        "date": ["column3423", "column5738", "column3846", "column4632"],
        "start_date": ["column5738", "column4632"], 
        "end_date": ["column3423", "column3846"]
    }
    
    print("📊 Loading sample mappings...")
    engine.load_mappings(sample_mappings)
    print(f"✅ Loaded {len(sample_mappings)} word mappings")
    
    # Test cases
    test_cases = [
        ("date", "Exact match"),
        ("dat", "Single typo - missing 'e'"),
        ("start_dat", "Typo in compound word"),
        ("strt_dte", "Multiple typos"),
        ("xyz123", "No match"),
        ("Date", "Case insensitive"),
        ("START_DATE", "Case insensitive compound"),
    ]
    
    print("\n🔍 Running test cases...")
    print("-" * 50)
    
    for query, description in test_cases:
        print(f"\nQuery: '{query}' ({description})")
        result = engine.search(query)
        
        print(f"  ⏱️  Execution time: {result.execution_time_ms:.2f}ms")
        print(f"  🎯 Exact match: {result.exact_match}")
        print(f"  📊 Total results: {result.total_results}")
        
        if result.results:
            for i, res in enumerate(result.results, 1):
                print(f"  📋 Result {i}:")
                print(f"     Word: {res.word}")
                print(f"     Confidence: {res.confidence:.2f}")
                print(f"     Match type: {res.match_type}")
                print(f"     Columns: {res.columns}")
                if res.changes:
                    print(f"     Changes: {res.changes}")
        else:
            print("  ❌ No results found")
            if result.suggestions:
                print(f"  💡 Suggestions: {result.suggestions}")
    
    # Test reverse lookup
    print("\n🔄 Testing reverse lookup...")
    print("-" * 50)
    
    reverse_tests = ["column5738", "column3423", "column9999"]
    
    for column_id in reverse_tests:
        result = engine.reverse_search(column_id)
        if result:
            print(f"Column '{column_id}' maps to: {result['words']}")
        else:
            print(f"Column '{column_id}' not found")
    
    # Test set operations
    print("\n🔗 Testing set operations...")
    print("-" * 50)
    
    # Intersection test
    intersection_result = engine.intersection_search(["date", "start_date"])
    if intersection_result:
        print(f"Intersection of ['date', 'start_date']: {intersection_result['intersection_columns']}")
    
    # Union test
    union_result = engine.union_search(["start_date", "end_date"])
    if union_result:
        print(f"Union of ['start_date', 'end_date']: {union_result['union_columns']}")
    
    # Get statistics
    print("\n📈 Engine Statistics...")
    print("-" * 50)
    stats = engine.get_stats()
    print(f"Total queries: {stats['total_queries']}")
    print(f"Exact matches: {stats['exact_matches']}")
    print(f"Fuzzy matches: {stats['fuzzy_matches']}")
    print(f"No matches: {stats['no_matches']}")
    print(f"Average execution time: {stats['average_execution_time_ms']:.2f}ms")
    
    print("\n✅ All tests completed successfully!")
    return True


if __name__ == "__main__":
    try:
        test_basic_functionality()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
