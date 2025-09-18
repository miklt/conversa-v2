#!/usr/bin/env python3
"""
Test script specifically for intent analysis improvements
"""
import asyncio
import os
import sys
sys.path.append('/Users/m/dev/conversa-v2')

from backend.app.agents.chat_agent import analyze_query_intent

async def test_intent_analysis():
    """Test the enhanced intent analysis"""
    
    # Test cases with expected results
    test_cases = [
        {
            "query": "Quais são as linguagens mais usadas no btg?",
            "expected": {
                "main_topic": "technology",
                "technology_type": "LINGUAGEM",
                "company_filter": "BTG"
            }
        },
        {
            "query": "Quais empresas usam Python?",
            "expected": {
                "main_topic": "reverse_technology",
                "specific_technology": "Python"
            }
        },
        {
            "query": "Quais são as empresas com mais estagiários?",
            "expected": {
                "main_topic": "company",
                "company_filter": None
            }
        },
        {
            "query": "O que fazem os estagiários na CIP?",
            "expected": {
                "main_topic": "activities",
                "company_filter": "CIP"
            }
        },
        {
            "query": "Frameworks menos utilizados em 2023",
            "expected": {
                "main_topic": "technology",
                "technology_type": "FRAMEWORK",
                "order_by_usage": "asc",
                "year_filter": 2023
            }
        }
    ]
    
    print("🧪 Testing Enhanced Intent Analysis")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        query = test_case["query"]
        expected = test_case["expected"]
        
        print(f"\n📝 Test {i}: '{query}'")
        
        try:
            intent = await analyze_query_intent(query)
            
            print(f"   📊 Results:")
            print(f"      main_topic: {intent.main_topic}")
            print(f"      technology_type: {intent.technology_type}")
            print(f"      company_filter: {intent.company_filter}")
            print(f"      specific_technology: {intent.specific_technology}")
            print(f"      order_by_usage: {intent.order_by_usage}")
            print(f"      year_filter: {intent.year_filter}")
            
            # Check key expectations
            success = True
            for key, expected_value in expected.items():
                actual_value = getattr(intent, key)
                if actual_value != expected_value:
                    print(f"   ❌ {key}: expected '{expected_value}', got '{actual_value}'")
                    success = False
                else:
                    print(f"   ✅ {key}: {actual_value}")
            
            if success:
                print(f"   🎯 Test {i} PASSED")
            else:
                print(f"   💥 Test {i} FAILED")
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Intent Analysis Testing Complete!")

if __name__ == "__main__":
    asyncio.run(test_intent_analysis())