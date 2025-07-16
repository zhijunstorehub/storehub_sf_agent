#!/usr/bin/env python3
"""
Query Statistics Analyzer for Salesforce Flow RAG System

Analyzes the query statistics logged by the Streamlit app to provide insights
about system performance, user behavior, and optimization opportunities.
"""

import json
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import argparse
from typing import Dict, List, Any
import statistics

class QueryStatsAnalyzer:
    """Analyzer for RAG system query statistics."""
    
    def __init__(self, log_file: str = "query_statistics.jsonl"):
        """Initialize the analyzer with the log file path."""
        self.log_file = Path(log_file)
        self.stats_data = []
        self.df = None
        
    def load_data(self) -> bool:
        """Load and parse the JSONL log file."""
        if not self.log_file.exists():
            print(f"Log file {self.log_file} not found!")
            return False
        
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self.stats_data.append(json.loads(line))
            
            self.df = pd.DataFrame(self.stats_data)
            self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
            
            print(f"Loaded {len(self.stats_data)} query records")
            return True
            
        except Exception as e:
            print(f"Error loading data: {e}")
            return False
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate a comprehensive summary report."""
        if self.df is None or self.df.empty:
            return {"error": "No data available"}
        
        report = {
            "overview": {
                "total_queries": len(self.df),
                "unique_sessions": self.df['session_id'].nunique(),
                "date_range": {
                    "start": self.df['timestamp'].min().isoformat(),
                    "end": self.df['timestamp'].max().isoformat()
                },
                "success_rate": (self.df['success'].sum() / len(self.df)) * 100,
                "cache_hit_rate": (self.df['cached'].sum() / len(self.df)) * 100
            },
            
            "performance": {
                "avg_response_time": self.df['total_response_time'].mean(),
                "median_response_time": self.df['total_response_time'].median(),
                "95th_percentile_response_time": self.df['total_response_time'].quantile(0.95),
                "avg_search_time": self.df['vector_search_time'].mean(),
                "avg_generation_time": self.df['generation_time'].mean(),
                "fastest_query": self.df['total_response_time'].min(),
                "slowest_query": self.df['total_response_time'].max()
            },
            
            "content_analysis": {
                "avg_query_length": self.df['query_length'].mean(),
                "avg_answer_length": self.df['answer_length'].mean(),
                "avg_documents_retrieved": self.df['documents_retrieved'].mean(),
                "avg_unique_sources": self.df['unique_sources'].mean(),
                "most_common_doc_counts": self.df['documents_retrieved'].value_counts().head().to_dict()
            },
            
            "user_behavior": {
                "avg_session_duration": self.df.groupby('session_id')['session_duration_seconds'].max().mean(),
                "avg_queries_per_session": self.df.groupby('session_id').size().mean(),
                "avg_query_similarity": self.df['query_similarity_to_previous'].mean(),
                "avg_time_between_queries": self.df['time_since_last_query'].mean()
            },
            
            "error_analysis": {
                "error_rate": ((~self.df['success']).sum() / len(self.df)) * 100,
                "error_types": self.df[~self.df['success']]['error_type'].value_counts().to_dict() if 'error_type' in self.df.columns else {}
            }
        }
        
        return report
    
    def print_summary_report(self):
        """Print a formatted summary report."""
        report = self.generate_summary_report()
        
        if "error" in report:
            print(f"Error: {report['error']}")
            return
        
        print("=" * 60)
        print("SALESFORCE FLOW RAG SYSTEM - QUERY STATISTICS REPORT")
        print("=" * 60)
        
        # Overview
        print("\n📊 OVERVIEW")
        print("-" * 30)
        print(f"Total Queries: {report['overview']['total_queries']:,}")
        print(f"Unique Sessions: {report['overview']['unique_sessions']:,}")
        print(f"Date Range: {report['overview']['date_range']['start'][:10]} to {report['overview']['date_range']['end'][:10]}")
        print(f"Success Rate: {report['overview']['success_rate']:.1f}%")
        print(f"Cache Hit Rate: {report['overview']['cache_hit_rate']:.1f}%")
        
        # Performance
        print("\n⚡ PERFORMANCE METRICS")
        print("-" * 30)
        print(f"Average Response Time: {report['performance']['avg_response_time']:.2f}s")
        print(f"Median Response Time: {report['performance']['median_response_time']:.2f}s")
        print(f"95th Percentile: {report['performance']['95th_percentile_response_time']:.2f}s")
        print(f"Average Search Time: {report['performance']['avg_search_time']:.2f}s")
        print(f"Average Generation Time: {report['performance']['avg_generation_time']:.2f}s")
        print(f"Fastest Query: {report['performance']['fastest_query']:.2f}s")
        print(f"Slowest Query: {report['performance']['slowest_query']:.2f}s")
        
        # Content Analysis
        print("\n📝 CONTENT ANALYSIS")
        print("-" * 30)
        print(f"Average Query Length: {report['content_analysis']['avg_query_length']:.0f} characters")
        print(f"Average Answer Length: {report['content_analysis']['avg_answer_length']:.0f} characters")
        print(f"Average Documents Retrieved: {report['content_analysis']['avg_documents_retrieved']:.1f}")
        print(f"Average Unique Sources: {report['content_analysis']['avg_unique_sources']:.1f}")
        
        # User Behavior
        print("\n👤 USER BEHAVIOR")
        print("-" * 30)
        print(f"Average Session Duration: {report['user_behavior']['avg_session_duration']:.0f} seconds")
        print(f"Average Queries per Session: {report['user_behavior']['avg_queries_per_session']:.1f}")
        print(f"Average Query Similarity: {report['user_behavior']['avg_query_similarity']:.2f}")
        print(f"Average Time Between Queries: {report['user_behavior']['avg_time_between_queries']:.0f} seconds")
        
        # Error Analysis
        print("\n❌ ERROR ANALYSIS")
        print("-" * 30)
        print(f"Error Rate: {report['error_analysis']['error_rate']:.1f}%")
        if report['error_analysis']['error_types']:
            print("Error Types:")
            for error_type, count in report['error_analysis']['error_types'].items():
                print(f"  - {error_type}: {count}")
        
        print("\n" + "=" * 60)
    
    def analyze_performance_trends(self):
        """Analyze performance trends over time."""
        if self.df is None or self.df.empty:
            print("No data available for trend analysis")
            return
        
        # Group by hour for trend analysis
        self.df['hour'] = self.df['timestamp'].dt.floor('H')
        hourly_stats = self.df.groupby('hour').agg({
            'total_response_time': ['mean', 'count'],
            'success': 'mean',
            'cached': 'mean'
        }).round(3)
        
        print("\n📈 HOURLY PERFORMANCE TRENDS")
        print("-" * 50)
        print(hourly_stats.tail(10))  # Show last 10 hours
    
    def find_optimization_opportunities(self):
        """Identify potential optimization opportunities."""
        if self.df is None or self.df.empty:
            print("No data available for optimization analysis")
            return
        
        print("\n🎯 OPTIMIZATION OPPORTUNITIES")
        print("-" * 40)
        
        # Slow queries
        slow_queries = self.df[self.df['total_response_time'] > self.df['total_response_time'].quantile(0.9)]
        if not slow_queries.empty:
            print(f"• {len(slow_queries)} queries ({len(slow_queries)/len(self.df)*100:.1f}%) took longer than 90th percentile")
            print(f"  Average slow query time: {slow_queries['total_response_time'].mean():.2f}s")
        
        # Cache opportunities
        uncached_queries = self.df[~self.df['cached']]
        if not uncached_queries.empty:
            repeated_queries = uncached_queries['query_hash'].value_counts()
            repeated_queries = repeated_queries[repeated_queries > 1]
            if not repeated_queries.empty:
                print(f"• {len(repeated_queries)} query patterns repeated multiple times (cache opportunities)")
        
        # Low document retrieval
        low_doc_queries = self.df[self.df['documents_retrieved'] == 0]
        if not low_doc_queries.empty:
            print(f"• {len(low_doc_queries)} queries ({len(low_doc_queries)/len(self.df)*100:.1f}%) found no relevant documents")
        
        # High generation time
        high_gen_time = self.df[self.df['generation_time'] > self.df['generation_time'].quantile(0.9)]
        if not high_gen_time.empty:
            print(f"• {len(high_gen_time)} queries had high generation times (avg: {high_gen_time['generation_time'].mean():.2f}s)")

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Analyze RAG system query statistics")
    parser.add_argument("--log-file", default="query_statistics.jsonl", 
                       help="Path to the query statistics log file")
    parser.add_argument("--summary", action="store_true", 
                       help="Generate summary report")
    parser.add_argument("--trends", action="store_true", 
                       help="Analyze performance trends")
    parser.add_argument("--optimize", action="store_true", 
                       help="Find optimization opportunities")
    parser.add_argument("--all", action="store_true", 
                       help="Run all analyses")
    
    args = parser.parse_args()
    
    analyzer = QueryStatsAnalyzer(args.log_file)
    
    if not analyzer.load_data():
        return
    
    if args.all or args.summary:
        analyzer.print_summary_report()
    
    if args.all or args.trends:
        analyzer.analyze_performance_trends()
    
    if args.all or args.optimize:
        analyzer.find_optimization_opportunities()
    
    if not any([args.summary, args.trends, args.optimize, args.all]):
        # Default: show summary
        analyzer.print_summary_report()

if __name__ == "__main__":
    main() 