# Query Analytics & Statistics

## Overview

The Salesforce Flow RAG System includes comprehensive query logging and analytics capabilities to track performance, user behavior, and system optimization opportunities.

## What Gets Logged

Every query to the RAG system automatically logs the following statistics:

### Basic Query Information
- **Query ID**: Unique identifier for each query
- **Session ID**: Groups queries within the same user session
- **Conversation ID**: Chat conversation identifier
- **Timestamp**: UTC timestamp of the query
- **Query Text**: The user's question (for analysis)
- **Query Length**: Character count and word count

### Performance Metrics
- **Total Response Time**: End-to-end query processing time
- **Vector Search Time**: Time spent searching the vector database
- **Generation Time**: Time spent generating the AI response
- **Cache Lookup Time**: Time spent checking/retrieving from cache

### Result Quality Metrics
- **Success Status**: Whether the query was processed successfully
- **Documents Retrieved**: Number of relevant documents found
- **Unique Sources**: Number of unique Flow sources used
- **Answer Length**: Character and word count of the response
- **Context Length**: Size of the retrieved context

### User Behavior Analytics
- **Session Query Count**: Number of queries in current session
- **Session Duration**: How long the user has been active
- **Query Similarity**: Similarity to previous query (0-1 scale)
- **Time Between Queries**: Seconds since last query
- **Chat History Length**: Number of messages in conversation

### Caching & System Metrics
- **Cache Hit/Miss**: Whether result came from cache
- **Cache Size**: Number of cached queries
- **Error Tracking**: Error types and details when queries fail

## Log Files

### `query_statistics.jsonl`
Contains detailed statistics for each query in JSON Lines format. Each line is a complete JSON record with all the metrics above.

Example record:
```json
{
  "query_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "abc123...",
  "timestamp": "2024-01-15T10:30:45.123456+00:00",
  "query": "What flows handle Lead qualification?",
  "query_length": 35,
  "total_response_time": 2.45,
  "vector_search_time": 0.8,
  "generation_time": 1.5,
  "success": true,
  "cached": false,
  "documents_retrieved": 3,
  "unique_sources": 2,
  "sources": ["Lead Qualification Flow", "Lead Scoring Process"]
}
```

### `rag_query_logs.log`
Human-readable log file with summary information and error details.

## Analytics Dashboard

Use the included analytics script to analyze logged queries:

```bash
# Generate comprehensive report
python analyze_query_stats.py --all

# Just summary statistics
python analyze_query_stats.py --summary

# Performance trends analysis
python analyze_query_stats.py --trends

# Find optimization opportunities
python analyze_query_stats.py --optimize
```

### Sample Analytics Output

```
==========================================
SALESFORCE FLOW RAG SYSTEM - QUERY STATISTICS REPORT
==========================================

📊 OVERVIEW
------------------------------
Total Queries: 1,247
Unique Sessions: 156
Date Range: 2024-01-15 to 2024-01-20
Success Rate: 98.2%
Cache Hit Rate: 34.7%

⚡ PERFORMANCE METRICS
------------------------------
Average Response Time: 2.18s
Median Response Time: 1.95s
95th Percentile: 4.12s
Average Search Time: 0.65s
Average Generation Time: 1.38s

👤 USER BEHAVIOR
------------------------------
Average Session Duration: 847 seconds
Average Queries per Session: 8.2
Average Query Similarity: 0.23
Average Time Between Queries: 45 seconds

🎯 OPTIMIZATION OPPORTUNITIES
----------------------------------------
• 124 queries (9.9%) took longer than 90th percentile
• 89 query patterns repeated multiple times (cache opportunities)
• 23 queries (1.8%) found no relevant documents
```

## Performance Monitoring

The system automatically tracks several key performance indicators:

### Response Time Breakdown
- **Search Phase**: Time to find relevant documents in vector store
- **Generation Phase**: Time for AI to generate response
- **Cache Operations**: Time for cache lookups and storage

### Quality Metrics
- **Document Retrieval Success**: How often relevant docs are found
- **Source Diversity**: Number of different Flow sources utilized
- **Answer Completeness**: Response length as quality indicator

### User Experience Metrics
- **Session Engagement**: Queries per session, session duration
- **Query Patterns**: Similarity and repetition analysis
- **Success Rates**: Overall system reliability

## Optimization Insights

The analytics help identify:

1. **Performance Bottlenecks**: Queries taking longer than expected
2. **Cache Opportunities**: Repeated queries that could be cached
3. **Content Gaps**: Queries finding no relevant documentation
4. **User Patterns**: Common query types and user behavior

## Privacy & Data Handling

- Query text is logged for analysis but can be excluded if needed
- All timestamps are in UTC for consistent analysis
- Session IDs are generated randomly (not tied to user identity)
- Log files can be rotated/archived as needed

## Integration with Streamlit App

The logging is fully integrated into the chat interface:

- **Automatic Logging**: Every query is automatically logged
- **Real-time Display**: Performance metrics shown in chat metadata
- **Session Tracking**: Persistent across browser sessions
- **Error Handling**: Failed queries are logged with error details

## Custom Analytics

The `QueryStatsAnalyzer` class can be extended for custom analysis:

```python
from analyze_query_stats import QueryStatsAnalyzer

analyzer = QueryStatsAnalyzer("query_statistics.jsonl")
analyzer.load_data()

# Custom analysis
df = analyzer.df
custom_metrics = df.groupby('hour')['total_response_time'].mean()
```

This logging system provides comprehensive insights into system performance and user behavior, enabling data-driven optimization of the RAG system. 