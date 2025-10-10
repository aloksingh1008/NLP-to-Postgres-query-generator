# Word to Column Mapper

A high-performance search engine that maps input words to arrays of column identifiers, supporting many-to-many relationships with intelligent typo correction and fuzzy matching capabilities.

## Features

- **Exact Matching**: Sub-millisecond performance for exact word matches
- **Fuzzy Matching**: Intelligent typo correction using Levenshtein distance
- **Case Insensitive**: Handles mixed case inputs seamlessly
- **Delimiter Handling**: Normalizes underscores, hyphens, and spaces
- **Reverse Lookup**: Find words that map to specific columns
- **Set Operations**: Union and intersection queries across multiple words
- **Real-time Caching**: Redis-based caching for optimal performance
- **Developer Dashboard**: Web interface for testing and debugging

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd word-column-mapper

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
# Start the API server
uvicorn word_column_mapper.main:app --reload --host 0.0.0.0 --port 8000

# Access the developer dashboard
open http://localhost:8000/dashboard
```

### Basic Usage

```python
# Load sample data
from word_column_mapper.core.engine import SearchEngine

engine = SearchEngine()
engine.load_mappings({
    "date": ["column3423", "column5738", "column3846", "column4632"],
    "start_date": ["column5738", "column4632"], 
    "end_date": ["column3423", "column3846"]
})

# Search for exact match
result = engine.search("date")
print(result.columns)  # ["column3423", "column5738", "column3846", "column4632"]

# Search with typo
result = engine.search("start_dat")  # Missing 'e'
print(result.matched_word)  # "start_date"
print(result.confidence)    # 0.82
```

## API Endpoints

### Search
```http
GET /api/v1/search/{query}
```

### Reverse Lookup
```http
GET /api/v1/reverse/{column_id}
```

### Set Operations
```http
GET /api/v1/intersection?words=date,start_date
GET /api/v1/union?words=date,start_date
```

## Performance

- **Exact Match**: < 1ms (99th percentile)
- **Single Typo**: < 10ms (95th percentile)
- **Multiple Typos**: < 50ms (90th percentile)
- **Throughput**: 1000+ queries/second

## Development

### Running Tests
```bash
pytest
pytest --benchmark-only  # Performance tests
```

### Code Quality
```bash
black .
isort .
flake8 .
mypy .
```

## Architecture

The application follows a layered architecture:

- **Presentation Layer**: FastAPI REST endpoints
- **Business Logic Layer**: Core search algorithms
- **Data Access Layer**: Index management and caching
- **Infrastructure Layer**: Configuration and monitoring

## License

MIT License - see LICENSE file for details.
