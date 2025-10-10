"""Integration tests for the API endpoints."""

import pytest
import httpx
from fastapi.testclient import TestClient
from word_column_mapper.main import app


class TestAPI:
    """Integration tests for API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)
    
    @pytest.fixture
    def sample_mappings(self):
        """Sample mappings for testing."""
        return {
            "date": ["column3423", "column5738", "column3846", "column4632"],
            "start_date": ["column5738", "column4632"], 
            "end_date": ["column3423", "column3846"],
            "user_id": ["column1001", "column1002"],
            "customer_id": ["column1001", "column2001"]
        }
    
    def test_root_endpoint(self, client):
        """Test the root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "Word Column Mapper"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"
    
    def test_api_info_endpoint(self, client):
        """Test the API info endpoint."""
        response = client.get("/api")
        assert response.status_code == 200
        
        data = response.json()
        assert "endpoints" in data
        assert "features" in data
        assert "performance" in data
    
    def test_search_exact_match(self, client):
        """Test exact search functionality."""
        response = client.get("/api/v1/search/date")
        assert response.status_code == 200
        
        data = response.json()
        assert data["exact_match"] is True
        assert data["total_results"] == 1
        assert data["results"][0]["word"] == "date"
        assert data["results"][0]["confidence"] == 1.0
        assert data["results"][0]["match_type"] == "exact"
    
    def test_search_fuzzy_match(self, client):
        """Test fuzzy search functionality."""
        response = client.get("/api/v1/search/dat")
        assert response.status_code == 200
        
        data = response.json()
        assert data["exact_match"] is False
        assert data["total_results"] > 0
        assert data["results"][0]["confidence"] > 0.0
    
    def test_search_with_parameters(self, client):
        """Test search with query parameters."""
        response = client.get("/api/v1/search/dat?fuzzy_threshold=0.8&max_results=5")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_results"] <= 5
    
    def test_search_no_match(self, client):
        """Test search with no matches."""
        response = client.get("/api/v1/search/xyz123")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_results"] == 0
        assert data["results"] == []
        assert data["suggestions"] is not None
    
    def test_search_with_body(self, client):
        """Test search with request body."""
        request_data = {
            "query": "dat",
            "fuzzy_threshold": 0.7,
            "max_results": 3,
            "include_suggestions": True
        }
        
        response = client.post("/api/v1/search", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_results"] <= 3
    
    def test_batch_search(self, client):
        """Test batch search functionality."""
        request_data = {
            "queries": ["date", "dat", "start_date"],
            "fuzzy_threshold": 0.6,
            "max_results": 5
        }
        
        response = client.post("/api/v1/search/batch", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 3
        assert all("query" in result for result in data)
    
    def test_suggestions_endpoint(self, client):
        """Test suggestions endpoint."""
        response = client.get("/api/v1/suggestions/dat")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert "date" in data
    
    def test_get_all_words(self, client):
        """Test getting all indexed words."""
        response = client.get("/api/v1/words")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert "date" in data
        assert "start_date" in data
    
    def test_reverse_lookup(self, client):
        """Test reverse lookup functionality."""
        response = client.get("/api/v1/reverse/column5738")
        assert response.status_code == 200
        
        data = response.json()
        assert data["column_id"] == "column5738"
        assert "date" in data["words"]
        assert "start_date" in data["words"]
        assert data["total_mappings"] == 2
    
    def test_reverse_lookup_not_found(self, client):
        """Test reverse lookup with non-existent column."""
        response = client.get("/api/v1/reverse/column9999")
        assert response.status_code == 404
    
    def test_get_all_columns(self, client):
        """Test getting all column IDs."""
        response = client.get("/api/v1/columns")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert "column3423" in data
        assert "column5738" in data
    
    def test_intersection_operation(self, client):
        """Test intersection operation."""
        response = client.get("/api/v1/intersection?words=date&words=start_date")
        assert response.status_code == 200
        
        data = response.json()
        assert data["operation"] == "AND"
        assert "column5738" in data["intersection_columns"]
        assert "column4632" in data["intersection_columns"]
        assert data["total_common_columns"] == 2
    
    def test_union_operation(self, client):
        """Test union operation."""
        response = client.get("/api/v1/union?words=start_date&words=end_date")
        assert response.status_code == 200
        
        data = response.json()
        assert data["operation"] == "OR"
        assert len(data["union_columns"]) == 4
        assert "column3423" in data["union_columns"]
        assert "column3846" in data["union_columns"]
    
    def test_set_operation_with_body(self, client):
        """Test set operation with request body."""
        request_data = {
            "words": ["date", "start_date"],
            "operation": "intersection"
        }
        
        response = client.post("/api/v1/operations", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["operation"] == "AND"
        assert data["total_common_columns"] == 2
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert "dependencies" in data
    
    def test_metrics_endpoint(self, client):
        """Test metrics endpoint."""
        response = client.get("/api/v1/metrics")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_queries" in data
        assert "average_response_time_ms" in data
        assert "memory_usage_mb" in data
    
    def test_detailed_metrics(self, client):
        """Test detailed metrics endpoint."""
        response = client.get("/api/v1/metrics/detailed")
        assert response.status_code == 200
        
        data = response.json()
        assert "query_metrics" in data
        assert "index_metrics" in data
        assert "system_metrics" in data
    
    def test_performance_benchmarks(self, client):
        """Test performance benchmarks endpoint."""
        response = client.get("/api/v1/metrics/performance")
        assert response.status_code == 200
        
        data = response.json()
        assert "current_performance" in data
        assert "performance_targets" in data
        assert "performance_status" in data
    
    def test_load_mappings(self, client):
        """Test loading mappings endpoint."""
        mappings = {
            "test_word": ["test_column1", "test_column2"]
        }
        
        response = client.post("/api/v1/mappings", json=mappings)
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "Mappings loaded successfully"
        assert data["total_words"] == 1
        assert data["total_mappings"] == 2
    
    def test_remove_mapping(self, client):
        """Test removing mapping endpoint."""
        # First add a mapping
        mappings = {"test_word": ["test_column"]}
        client.post("/api/v1/mappings", json=mappings)
        
        # Then remove it
        response = client.delete("/api/v1/mappings/test_word")
        assert response.status_code == 200
        
        data = response.json()
        assert "removed successfully" in data["message"]
    
    def test_remove_mapping_not_found(self, client):
        """Test removing non-existent mapping."""
        response = client.delete("/api/v1/mappings/nonexistent")
        assert response.status_code == 404
    
    def test_error_handling_invalid_query(self, client):
        """Test error handling for invalid queries."""
        # Query too long
        long_query = "x" * 101
        response = client.get(f"/api/v1/search/{long_query}")
        assert response.status_code == 400
    
    def test_error_handling_invalid_parameters(self, client):
        """Test error handling for invalid parameters."""
        # Invalid fuzzy threshold
        response = client.get("/api/v1/search/date?fuzzy_threshold=1.5")
        assert response.status_code == 422  # Validation error
    
    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options("/api/v1/search/date")
        # CORS headers should be present (handled by middleware)
        assert response.status_code in [200, 204]
    
    def test_content_type_headers(self, client):
        """Test content type headers."""
        response = client.get("/api/v1/search/date")
        assert response.headers["content-type"] == "application/json"
    
    def test_response_time_performance(self, client):
        """Test that response times are within acceptable limits."""
        import time
        
        start_time = time.time()
        response = client.get("/api/v1/search/date")
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # Should be very fast
        
        # Check that the API reports reasonable execution time
        data = response.json()
        assert data["execution_time_ms"] < 100  # Should be under 100ms
