"""Optimized table frequency ranker for identifying most relevant tables in query results."""

from typing import List, Dict, Set, Any, Optional
from collections import Counter, defaultdict
from dataclasses import dataclass


@dataclass
class TableRanking:
    """Data class for table ranking information."""
    table: str
    frequency: int
    percentage: float
    keyword_count: int
    contributing_keywords: List[str]


class TableFrequencyRanker:
    """Analyzes and ranks tables by frequency and cross-keyword relevance."""
    
    def __init__(self):
        """Initialize the table frequency ranker."""
        pass    
    def rank_by_frequency(
        self, 
        all_tables: List[str], 
        min_frequency: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Rank tables by their frequency of occurrence.
        
        Args:
            all_tables: List of all table names (may contain duplicates)
            min_frequency: Minimum frequency for inclusion
            
        Returns:
            List of dicts sorted by frequency (descending):
            {
                "table": str,
                "frequency": int,
                "percentage": float
            }
        """
        if not all_tables:
            return []
        
        table_counts = Counter(all_tables)
        total = len(all_tables)
        
        return [
            {
                "table": table,
                "frequency": count,
                "percentage": round((count / total) * 100, 2)
            }
            for table, count in table_counts.most_common()
            if count >= min_frequency
        ]
    
    def rank_by_cross_keyword_relevance(
        self,
        search_results: List[Dict[str, Any]],
        min_keywords: int = 1
    ) -> List[TableRanking]:
        """
        Rank tables by their total frequency of occurrence.
        Tables appearing more times are ranked higher regardless of keywords.
        
        Args:
            search_results: List of dicts with "keyword" and "tables" fields
            min_keywords: Minimum number of keywords for inclusion (kept for compatibility)
            
        Returns:
            List of TableRanking objects sorted by frequency (descending)
        """
        if not search_results:
            return []
        
        # Build keyword-to-table mapping efficiently
        table_keywords: Dict[str, Set[str]] = defaultdict(set)
        table_frequency: Counter = Counter()
        
        for result in search_results:
            keyword = result.get("keyword") or result.get("word", "")
            tables = result.get("tables", [])
            
            for table in tables:
                table_keywords[table].add(keyword)
                table_frequency[table] += 1
        
        total_occurrences = sum(table_frequency.values())
        
        # Create rankings
        rankings = []
        for table, keywords in table_keywords.items():
            keyword_count = len(keywords)
            if keyword_count >= min_keywords:
                freq = table_frequency[table]
                rankings.append(
                    TableRanking(
                        table=table,
                        frequency=freq,
                        percentage=round((freq / total_occurrences) * 100, 2) if total_occurrences > 0 else 0.0,
                        keyword_count=keyword_count,
                        contributing_keywords=sorted(keywords)
                    )
                )
        
        # Sort by frequency only (descending)
        rankings.sort(key=lambda x: x.frequency, reverse=True)
        
        return rankings
    
    def get_top_tables(
        self, 
        all_tables: List[str], 
        top_n: int = 5
    ) -> List[str]:
        """
        Get the N most frequent tables.
        
        Args:
            all_tables: List of all table names (may contain duplicates)
            top_n: Number of top tables to return
            
        Returns:
            List of table names sorted by frequency
        """
        if not all_tables:
            return []
        
        return [table for table, _ in Counter(all_tables).most_common(top_n)]
    
    def filter_by_threshold(
        self, 
        all_tables: List[str], 
        threshold_percentage: float = 20.0
    ) -> List[str]:
        """
        Filter tables appearing above a percentage threshold.
        
        Args:
            all_tables: List of all table names (may contain duplicates)
            threshold_percentage: Minimum percentage (0-100) for inclusion
            
        Returns:
            List of unique table names meeting the threshold
        """
        if not all_tables:
            return []
        
        ranked = self.rank_by_frequency(all_tables)
        return [item["table"] for item in ranked if item["percentage"] >= threshold_percentage]
   
    def analyze_distribution(
        self, 
        search_results: List[Dict[str, Any]],
        top_n: int = 2,
        use_fast_sort: bool = True
    ) -> Dict[str, Any]:
        """
        Comprehensive analysis of table distribution across search results.
        Ranks tables by total frequency only.
        
        Args:
            search_results: List of dicts with "keyword"/"word" and "tables" fields
            top_n: Number of top tables to return
            use_fast_sort: If True, use heap-based partial sort for top_n << total tables
            
        Returns:
            Dictionary with:
            - total_unique_tables: Count of unique tables
            - total_occurrences: Total table occurrences
            - top_tables: Top N tables by frequency
            - all_rankings: Complete ranking list
            - summary: Quick summary statistics
        """
        if not search_results:
            return self._empty_analysis()
        
        # Get cross-keyword rankings
        rankings = self.rank_by_cross_keyword_relevance(search_results)
        
        if not rankings:
            return self._empty_analysis()
        
        # Extract all tables for statistics
        all_tables = [
            table
            for result in search_results
            for table in result.get("tables", [])
        ]
        
        # Get top N tables using optimized algorithm
        if use_fast_sort and top_n < len(rankings):
            # Use heap-based partial sort - O(U + n log U) instead of O(U log U)
            # Much faster when n << U (e.g., n=2, U=1000)
            import heapq
            top_rankings = heapq.nlargest(
                top_n,
                rankings,
                key=lambda x: x.frequency
            )
        else:
            # Use full sort for small lists or when n >= U
            top_rankings = rankings[:top_n]
        
        top_tables = [
            {
                "table": r.table,
                "keyword_count": r.keyword_count,
                "frequency": r.frequency,
                "percentage": r.percentage,
                "contributing_keywords": r.contributing_keywords
            }
            for r in top_rankings
        ]
        
        # Calculate summary statistics
        avg_keywords_per_table = sum(r.keyword_count for r in rankings) / len(rankings)
        tables_multiple_keywords = sum(1 for r in rankings if r.keyword_count > 1)
        
        return {
            "total_unique_tables": len(set(all_tables)),
            "total_occurrences": len(all_tables),
            "top_tables": top_tables,
            "all_rankings": [
                {
                    "table": r.table,
                    "keyword_count": r.keyword_count,
                    "frequency": r.frequency,
                    "percentage": r.percentage,
                    "contributing_keywords": r.contributing_keywords
                }
                for r in rankings
            ],
            "summary": {
                "average_keywords_per_table": round(avg_keywords_per_table, 2),
                "tables_across_multiple_keywords": tables_multiple_keywords,
                "multi_keyword_percentage": round(
                    (tables_multiple_keywords / len(rankings)) * 100, 2
                )
            }
        }
    
    def get_keyword_coverage(
        self,
        search_results: List[Dict[str, Any]],
        table_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed coverage information for a specific table.
        
        Args:
            search_results: List of search result dicts
            table_name: Name of the table to analyze
            
        Returns:
            Dict with coverage details or None if table not found
        """
        keywords = set()
        total_occurrences = 0
        
        for result in search_results:
            keyword = result.get("keyword") or result.get("word", "")
            tables = result.get("tables", [])
            
            if table_name in tables:
                keywords.add(keyword)
                total_occurrences += tables.count(table_name)
        
        if not keywords:
            return None
        
        return {
            "table": table_name,
            "keyword_count": len(keywords),
            "keywords": sorted(keywords),
            "total_occurrences": total_occurrences
        }
    
    def _empty_analysis(self) -> Dict[str, Any]:
        """Return empty analysis structure."""
        return {
            "total_unique_tables": 0,
            "total_occurrences": 0,
            "top_tables": [],
            "all_rankings": [],
            "summary": {
                "average_keywords_per_table": 0.0,
                "tables_across_multiple_keywords": 0,
                "multi_keyword_percentage": 0.0
            }
        }


# Example usage
if __name__ == "__main__":
    # Sample data
    search_results = [
        {"keyword": "customer", "tables": ["customers", "orders", "customers"]},
        {"keyword": "order", "tables": ["orders", "order_items", "customers"]},
        {"keyword": "product", "tables": ["products", "order_items"]},
        {"keyword": "sales", "tables": ["orders", "customers"]}
    ]
    
    ranker = TableFrequencyRanker()
    
    # Get comprehensive analysis
    analysis = ranker.analyze_distribution(search_results, top_n=3)
    
    print("Top Tables by Frequency:")
    for table in analysis["top_tables"]:
        print(f"  {table['table']}: {table['frequency']} times ({table['percentage']}%)")
        print(f"    Appears in {table['keyword_count']} keywords: {', '.join(table['contributing_keywords'])}")
    
    print(f"\nSummary:")
    print(f"  Total unique tables: {analysis['total_unique_tables']}")
    print(f"  Tables across multiple keywords: {analysis['summary']['tables_across_multiple_keywords']}")
    
    # Get specific table coverage
    coverage = ranker.get_keyword_coverage(search_results, "customers")
    if coverage:
        print(f"\nCustomers table coverage:")
        print(f"  Appears in {coverage['keyword_count']} keywords: {', '.join(coverage['keywords'])}")