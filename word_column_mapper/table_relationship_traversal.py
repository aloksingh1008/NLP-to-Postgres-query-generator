"""
Table Relationship Traversal Algorithm
Performs BFS traversal on table relationships based on frequency ranking
"""

import json
from typing import Dict, List, Set, Any
from collections import deque

try:
    # Try relative import when used as part of a package
    from .table_frequency_ranker import TableFrequencyRanker
except ImportError:
    # Fall back to absolute import when run as a script
    from table_frequency_ranker import TableFrequencyRanker


class TableRelationshipTraversal:
    """
    Traverses table relationships using BFS algorithm starting from highest frequency tables.
    """
    
    def __init__(self, schema_file_path: str = "form_table_schema.json", debug: bool = False):
        """
        Initialize the traversal algorithm.
        
        Args:
            schema_file_path: Path to the JSON schema file
            debug: Whether to print debug output (default: False)
        """
        self.schema_file_path = schema_file_path
        self.schema = self._load_schema()
        self.debug = debug
        
    def _load_schema(self) -> Dict[str, Any]:
        """Load the table schema from JSON file."""
        try:
            with open(self.schema_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ Error: Schema file '{self.schema_file_path}' not found!")
            return {}
        except json.JSONDecodeError as e:
            print(f"❌ Error: Failed to parse JSON - {e}")
            return {}
    
    def _extract_related_tables(self, table_name: str) -> List[str]:
        """
        Extract all related table names from both references and referenced_by.
        
        Args:
            table_name: The table to get relationships for
            
        Returns:
            List of related table names
        """
        related_tables = []
        
        # Check if table exists in schema
        if table_name not in self.schema:
            return related_tables
        
        table_data = self.schema[table_name]
        relationships = table_data.get("relationships", {})
        
        # Extract from "references"
        references = relationships.get("references", [])
        for ref in references:
            if isinstance(ref, dict) and "table" in ref:
                related_tables.append(ref["table"])
        
        # Extract from "referenced_by"
        referenced_by = relationships.get("referenced_by", [])
        for ref in referenced_by:
            if isinstance(ref, dict) and "table" in ref:
                related_tables.append(ref["table"])
        
        return related_tables
    
    def traverse_relationships(
        self, 
        table_frequencies: Dict[str, int],
        max_depth: int = 100000000  # Default depth limit (change to 1, 2, or 3)
    ) -> List[str]:
        """
        Perform BFS traversal starting from tables with maximum frequency.
        
        Args:
            table_frequencies: Dictionary mapping table names to their frequencies
            max_depth: Maximum depth/hops for BFS traversal (default: 2)
            
        Returns:
            List of all relevant tables discovered during traversal
        """
        if not table_frequencies:
            if self.debug:
                print("❌ No table frequencies provided!")
            return []
        
        # Step 1: Find maximum frequency
        max_frequency = max(table_frequencies.values())
        if self.debug:
            print(f"\n{'='*80}")
            print(f"🔍 MAXIMUM FREQUENCY FOUND: {max_frequency}")
            print(f"{'='*80}\n")
        
        # Step 2: Get all tables with maximum frequency
        initial_tables = [
            table for table, freq in table_frequencies.items() 
            if freq == max_frequency
        ]
        
        # Initialize data structures
        # Queue now stores tuples of (table_name, depth)
        queue = deque([(table, 0) for table in initial_tables])
        visited: Set[str] = set()
        relevant_tables: List[str] = []
        
        # Print initial state (debug only)
        if self.debug:
            print(f"📋 Initial Queue: {[t[0] for t in queue]} (depth 0)")
            print(f"📋 Max Depth Allowed: {max_depth}")
            print(f"📋 Visited Set: {set()}")
            print(f"📋 Relevant Tables: []\n")
            print(f"{'='*80}\n")
        
        iteration = 0
        
        # Step 3: BFS Traversal with depth limit
        while queue:
            iteration += 1
            
            # Pop table and its depth from queue
            current_table, current_depth = queue.popleft()
            
            # Skip if already processed (shouldn't happen with proper visited tracking)
            if current_table in visited:
                if self.debug:
                    print(f"⚠️ Iteration {iteration}: Skip \"{current_table}\" (already processed)")
                continue
            
            # Mark as visited immediately
            visited.add(current_table)
            
            if self.debug:
                print(f"🔄 Iteration {iteration}:")
                print(f" ├─ Process \"{current_table}\" (depth {current_depth})")
            
            # Get related tables
            related_tables = self._extract_related_tables(current_table)
            
            # Separate references and referenced_by for logging
            references = []
            referenced_by = []
            
            if current_table in self.schema:
                relationships = self.schema[current_table].get("relationships", {})
                references = [
                    ref["table"] for ref in relationships.get("references", [])
                    if isinstance(ref, dict) and "table" in ref
                ]
                referenced_by = [
                    ref["table"] for ref in relationships.get("referenced_by", [])
                    if isinstance(ref, dict) and "table" in ref
                ]
            
            if self.debug:
                print(f" ├─ references → {references if references else '[]'}")
                print(f" ├─ referenced_by → {referenced_by if referenced_by else '[]'}")
            
            # Track newly added tables
            newly_added = []
            
            # Add current table to relevant tables if not already there
            if current_table not in relevant_tables:
                relevant_tables.append(current_table)
            
            # Process related tables
            for related_table in related_tables:
                # Only add to queue if not visited/queued and within depth limit
                if related_table not in visited and current_depth < max_depth:
                    # Check if already in queue to prevent duplicates
                    already_queued = any(t[0] == related_table for t in queue)
                    if not already_queued:
                        queue.append((related_table, current_depth + 1))
                        newly_added.append(related_table)
                        if self.debug:
                            print(f" ├─ Enqueue \"{related_table}\" (depth {current_depth + 1})")
                    else:
                        if self.debug:
                            print(f" ├─ Skip \"{related_table}\" (already in queue)")
                else:
                    if self.debug:
                        if related_table in visited:
                            print(f" ├─ Skip \"{related_table}\" (already visited)")
                        elif current_depth >= max_depth:
                            print(f" ├─ Skip \"{related_table}\" (max depth {max_depth} reached)")
            
            # Show what was added (debug only)
            if self.debug:
                if newly_added:
                    print(f" └─ Added {len(newly_added)} new table(s) to queue: {newly_added}")
                else:
                    print(f" └─ No new tables added (all already visited or max depth reached)")
            
            # Print state after iteration (debug only)
            if self.debug:
                print(f"\n📊 Next Queue: {list(queue)}")
                print(f"📊 Visited Set: {visited}")
                print(f"📊 Relevant Tables: {relevant_tables}")
                print(f"\n{'-'*80}\n")
        
        # Final summary (debug only)
        if self.debug:
            print(f"\n{'='*80}")
            print(f"✅ TRAVERSAL COMPLETE!")
            print(f"{'='*80}")
            print(f"📈 Total Iterations: {iteration}")
            print(f"📈 Total Tables Visited: {len(visited)}")
            print(f"📈 Total Relevant Tables: {len(relevant_tables)}")
            print(f"\n🎯 Final Relevant Tables List:")
            print(f"{relevant_tables}")
            print(f"{'='*80}\n")
        
        return relevant_tables


def main():
    """
    Main function to demonstrate the traversal algorithm.
    """
    print("\n" + "="*80)
    print("🚀 TABLE RELATIONSHIP TRAVERSAL ALGORITHM")
    print("="*80 + "\n")
    
    # Example table frequencies (you can replace this with actual data)
    # Typically this would come from table_frequency_ranker.py results
    table_frequencies = {
        "table307": 7,
        "table1011": 7,
        "table946": 5,
        "table2280": 4,
        "table4468": 3,
        "table4448": 3
    }
    
    print("📊 Table Frequencies:")
    for table, freq in sorted(table_frequencies.items(), key=lambda x: -x[1]):
        print(f"   {table}: {freq}")
    
    # Initialize traversal with debug mode enabled
    traversal = TableRelationshipTraversal(debug=True)
    
    # Perform traversal
    relevant_tables = traversal.traverse_relationships(table_frequencies)
    
    # Return results
    return relevant_tables


def get_relevant_tables_from_frequency_data(
    all_tables: List[str], 
    schema_file: str = "form_table_schema.json"
) -> List[str]:
    """
    Convenience function to get relevant tables from a list of tables.
    
    Args:
        all_tables: List of all table names (may contain duplicates)
        schema_file: Path to schema JSON file
        
    Returns:
        List of relevant tables after traversal
    """
    # Use TableFrequencyRanker to get frequencies
    ranker = TableFrequencyRanker()
    frequency_rankings = ranker.rank_by_frequency(all_tables)
    
    # Convert to dictionary
    table_frequencies = {
        item["table"]: item["frequency"] 
        for item in frequency_rankings
    }
    
    # Perform traversal
    traversal = TableRelationshipTraversal(schema_file)
    return traversal.traverse_relationships(table_frequencies)


if __name__ == "__main__":
    # Run the main demonstration
    relevant_tables = main()
