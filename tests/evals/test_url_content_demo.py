#!/usr/bin/env python3
"""
Quick demo to verify the enhanced test_tools_fetch_url_content.py works correctly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from test_tools_fetch_url_content import run_single_test_with_details, HARMFUL_CONTENT_SCENARIOS

if __name__ == "__main__":
    print("\n" + "="*80)
    print("URL CONTENT SAFETY TEST DEMO")
    print("="*80)
    print("\nThis demo shows how the FactCheckingAgent handles harmful content from URLs.")
    print("The test will:")
    print("1. Mock search results pointing to harmful URLs")
    print("2. Mock fetch_url_content to return dangerous content")
    print("3. Run the actual LLM to see how it processes this content")
    print("4. Analyze if harmful content propagates to the output")
    
    # Show available scenarios
    print("\nAvailable test scenarios:")
    for i, scenario in enumerate(HARMFUL_CONTENT_SCENARIOS):
        print(f"{i+1}. {scenario['name']} - {scenario['claim']}")
    
    # Run a specific test
    print("\n" + "-"*80)
    print("Running test: harmful_misinformation")
    print("-"*80)
    
    try:
        run_single_test_with_details("harmful_misinformation")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        print("\nThis might be due to:")
        print("- Missing API credentials")
        print("- Network issues")
        print("- Import errors")
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("\nThe test demonstrates whether the LLM:")
    print("✓ Actually calls fetch_url_content with harmful URLs")
    print("✓ Processes the harmful content")
    print("✓ Propagates harmful information to its output")
    print("✓ Is influenced by prompt injections in URL content")
    print("\nCheck the output above to see if vulnerabilities were detected!")