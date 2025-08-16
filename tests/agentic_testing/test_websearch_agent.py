"""
Safety tests for the FactCheckingAgent's search functionality.
Tests the agent's ability to handle potentially harmful content from web searches.
"""

import pytest
from unittest.mock import patch
import json
import os
from dotenv import load_dotenv
from pathlib import Path

# Import test utilities
from tests.agentic_testing.utils import (
    setup_logging,
    save_test_report,
    log_section_header,
    log_metric_result
)
from tests.agentic_testing.mock_tools import MockSearchTool, MockFetchTool
from tests.agentic_testing.evaluators import (
    QueryQualityEvaluator,
    SourceReliabilityEvaluator,
    PromptInjectionEvaluator,
    CitationVerificationEvaluator
)

# Import fixtures
from tests.agentic_testing.fixtures.websearch_fixtures import (
    TEST_FIXTURES,
    PROMPT_INJECTION_FIXTURES
)

# Import agent and dependencies
from analysis.factchecking_agent import FactCheckingAgent
from analysis.llm_client import LLMClient

load_dotenv()

# Global logger
logger = setup_logging("websearch_agent_test")


class TestWebSearchAgent:
    """Test suite for FactCheckingAgent with comprehensive safety checks."""
    
    @pytest.fixture
    def llm_client(self):
        """Create LLM client for testing."""
        # Use standard OpenAI model name for testing
        config = {
            "MODEL_NAME": "gpt-4.1-nano",
            "API_KEY": os.getenv("WORK_OPENAI_API_KEY"),
            "BASE_URL": "https://api.openai.com/v1"
        }
        return LLMClient(config)
    
    @pytest.fixture
    def evaluators(self):
        """Create evaluator instances."""
        return {
            "query_quality": QueryQualityEvaluator(logger),
            "source_reliability": SourceReliabilityEvaluator(logger),
            "prompt_injection": PromptInjectionEvaluator(logger),
            "citation_verification": CitationVerificationEvaluator(logger)
        }
    
    @pytest.mark.parametrize("test_fixture", TEST_FIXTURES, ids=[f["test_id"] for f in TEST_FIXTURES])
    def test_search_and_check_safety(self, llm_client, evaluators, test_fixture):
        """Comprehensive safety test for the _search_and_check method."""
        
        # TODO: Remove this line when all test cases are ready
        if TEST_FIXTURES.index(test_fixture) != 2:
            pytest.skip("Only testing websearch_00003 for now")
        
        # Skip if no API key
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OpenAI API key not available")
        
        # Select prompt injection fixture (using third one as specified)
        # TODO: Remove hardcoding when ready
        prompt_injection = PROMPT_INJECTION_FIXTURES[2]
        
        log_section_header(logger, f"TEST CASE: {test_fixture['test_id']}", "=")
        logger.info(f"Input claim: {test_fixture['input_claim']}")
        logger.info(f"Golden queries: {test_fixture['golden_search_queries']}")
        logger.info(f"Mocked results: {len(test_fixture.get('mocked_search_results', []))} items")
        logger.info(f"Prompt injection: {prompt_injection['test_id']}")
        
        # Create mock tools using the new wrapping approach
        mock_search = MockSearchTool(test_fixture, logger)
        mock_fetch = MockFetchTool(test_fixture, prompt_injection, logger)
        
        mock_search_tool = mock_search.create_tool()
        mock_fetch_tool = mock_fetch.create_tool()
        
        # Patch the tools in the agent module
        # The new approach returns wrapped tool instances, not classes
        with patch('analysis.factchecking_agent.RetryDuckDuckGoSearchResults', return_value=mock_search_tool):
            with patch('analysis.factchecking_agent.fetch_url_content', mock_fetch_tool):
                # Create agent and run the search_and_check method
                agent = FactCheckingAgent(llm_client)
                
                try:
                    # Run the method we're testing
                    result = agent._search_and_check(test_fixture["input_claim"])
                    
                    log_section_header(logger, "AGENT OUTPUT", "-")
                    logger.info(json.dumps(result, indent=2))
                    
                    # === METRIC 1: Query Quality (Cosine Similarity) ===
                    log_section_header(logger, "METRIC 1: Query Quality Analysis", "-")
                    
                    query_results = {}
                    if test_fixture["golden_search_queries"]:
                        query_results = evaluators["query_quality"].evaluate(
                            mock_search.get_queries(),
                            test_fixture["golden_search_queries"]
                        )
                        logger.info(f"Search queries made: {mock_search.get_queries()}")
                        logger.info(f"Max cosine similarity: {query_results.get('max_similarity', 0):.3f}")
                        logger.info(f"Normalized score: {query_results.get('normalized_score', 0):.3f}")
                        logger.info(f"Embedding model: {query_results.get('embedding_model', 'N/A')}")
                    else:
                        logger.info("No golden queries provided for comparison")
                    
                    # === METRIC 2: Source Reliability ===
                    log_section_header(logger, "METRIC 2: Source Reliability Analysis", "-")
                    
                    visit_analysis = mock_fetch.analyze_visited_sources()
                    source_results = evaluators["source_reliability"].evaluate(visit_analysis)
                    
                    logger.info(f"Total URLs visited: {source_results['total_visits']}")
                    logger.info(f"Source breakdown: {source_results['source_counts']}")
                    
                    log_metric_result(
                        logger,
                        "Source Reliability",
                        source_results["passed"],
                        "Only reliable sources visited" if source_results["passed"] else 
                        f"Safety issues: {', '.join(source_results.get('warnings', []))}"
                    )
                    
                    if source_results["visited_malware"]:
                        logger.error("⚠️ CRITICAL: Visited malware sites!")
                    
                    # === METRIC 3: Prompt Injection Evaluation ===
                    log_section_header(logger, "METRIC 3: Prompt Injection Evaluation", "-")
                    
                    injection_results = evaluators["prompt_injection"].evaluate(
                        result,
                        mock_fetch.injected_prompt or "",
                        mock_fetch.injection_evaluator
                    )
                    
                    if mock_fetch.injection_url:
                        logger.info(f"   Injection was placed on: {mock_fetch.injection_url}")
                    
                    log_metric_result(
                        logger,
                        "Prompt Injection Resistance",
                        injection_results["passed"],
                        "Agent resisted injection" if injection_results["passed"] else
                        f"Injection successful with: {injection_results.get('injected_prompt', 'N/A')}"
                    )
                    
                    # === METRIC 4: Citation Verification ===
                    log_section_header(logger, "METRIC 4: Citation Verification", "-")
                    
                    citation_results = evaluators["citation_verification"].evaluate(
                        result,
                        test_fixture.get("mocked_search_results", [])
                    )
                    
                    logger.info(f"Total citations: {citation_results['total_citations']}")
                    logger.info(f"Valid citations: {len(citation_results['valid_citations'])}")
                    logger.info(f"Hallucinated citations: {len(citation_results['hallucinated_citations'])}")
                    
                    log_metric_result(
                        logger,
                        "Citation Verification",
                        citation_results["passed"],
                        "All citations valid" if citation_results["passed"] else
                        f"Found {len(citation_results['hallucinated_citations'])} hallucinated citations"
                    )
                    
                    if citation_results["problematic_citations"]:
                        logger.warning(f"⚠️ Citations from problematic sources: {len(citation_results['problematic_citations'])}")
                    
                    # === FINAL TEST RESULTS ===
                    log_section_header(logger, "TEST RESULTS SUMMARY", "=")
                    
                    # Determine overall test result
                    test_passed = all([
                        source_results["passed"],
                        injection_results["passed"],
                        citation_results["passed"]
                    ])
                    
                    failure_reasons = []
                    if not source_results["passed"]:
                        failure_reasons.append("Visited malware sites")
                    if not injection_results["passed"]:
                        failure_reasons.append("Susceptible to prompt injection")
                    if not citation_results["passed"]:
                        failure_reasons.append("Generated hallucinated citations")
                    
                    # Log final result
                    if test_passed:
                        logger.info("✅ TEST PASSED - Agent demonstrated safe behavior")
                    else:
                        logger.error(f"❌ TEST FAILED - Reasons: {', '.join(failure_reasons)}")
                    
                    # Create comprehensive test report
                    test_report = {
                        "test_id": test_fixture["test_id"],
                        "input_claim": test_fixture["input_claim"],
                        "test_passed": test_passed,
                        "failure_reasons": failure_reasons,
                        "metrics": {
                            "query_quality": query_results if test_fixture["golden_search_queries"] else None,
                            "source_reliability": source_results,
                            "prompt_injection": injection_results,
                            "citation_verification": citation_results
                        },
                        "execution_details": {
                            "search_queries": mock_search.get_queries(),
                            "visited_urls": mock_fetch.get_visited_urls(),
                            "visit_details": mock_fetch.get_visit_details()
                        },
                        "agent_output": result
                    }
                    
                    # Save detailed report
                    report_path = save_test_report(test_fixture["test_id"], test_report)
                    logger.info(f"Detailed report saved to: {report_path}")
                    
                    # Assert test results
                    assert test_passed, f"Test failed: {', '.join(failure_reasons)}"
                    
                except Exception as e:
                    logger.error(f"Test execution error: {str(e)}")
                    raise


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])