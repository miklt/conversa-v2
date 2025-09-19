#!/usr/bin/env python3
"""
Test script for reverse search functionality
"""
import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.agents.chat_agent import process_chat_message, analyze_query_intent
from backend.app.db.database import get_db

async def test_reverse_search():
    """Test reverse search queries"""
    print("🧪 Testing reverse search functionality...")

    # Test queries
    test_queries = [
        "Quais são as empresas que trabalham com a linguagem Java?",
        "Quais empresas usam Python?",
        "Empresas que utilizam React",
        "Onde se usa JavaScript?",
        "Quais empresas trabalham com Docker?"
    ]

    db = next(get_db())

    for query in test_queries:
        print(f"\n🔍 Testing query: '{query}'")

        try:
            # Analyze intent
            intent = await analyze_query_intent(query)
            print(f"   Intent: main_topic='{intent.main_topic}', specific_technology='{intent.specific_technology}', company_filter='{intent.company_filter}'")

            # Process the message
            response = await process_chat_message(query, db)
            print(f"   Response confidence: {response.confidence}")
            print(f"   Response preview: {response.response[:200]}...")

        except Exception as e:
            print(f"   ❌ Error: {e}")

    print("\n✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(test_reverse_search())