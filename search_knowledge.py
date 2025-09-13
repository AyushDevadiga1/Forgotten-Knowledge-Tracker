#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.search_engine import knowledge_search
from datetime import datetime

def format_timestamp(timestamp):
    """Format timestamp for display"""
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return timestamp

def search_cli():
    """Command-line search interface"""
    print("🔍 Forgotten Knowledge Search")
    print("=============================")
    
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = input("Enter search query: ").strip()
    
    if not query:
        print("Please provide a search query.")
        return
    
    print(f"\nSearching for: '{query}'")
    print("=" * 50)
    
    results = knowledge_search.search_all(query, limit=15)
    
    if not results:
        print("❌ No results found.")
        return
    
    print(f"✅ Found {len(results)} results:\n")
    
    for i, result in enumerate(results, 1):
        print(f"{i}. [{result['type'].upper()}] {result['source']}")
        print(f"   ⏰ {format_timestamp(result['timestamp'])}")
        print(f"   📝 {result['snippet']}")
        print(f"   ⭐ Relevance: {result['relevance']}/100")
        
        if 'app' in result:
            print(f"   🖥️  App: {result['app']}")
        if 'duration' in result and result['duration']:
            print(f"   ⏱️  Duration: {result['duration']}s")
        if 'confidence' in result and result['confidence']:
            print(f"   🎯 Confidence: {result['confidence']:.2f}")
            
        print()

if __name__ == "__main__":
    search_cli()