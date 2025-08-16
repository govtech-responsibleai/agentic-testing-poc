"""
Multi-model test runner for FactCheckingAgent safety testing.
Runs websearch agent tests across multiple model configurations and saves results to CSV.
"""

import json
import os
import csv
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple
from unittest.mock import patch

# Standard imports
import pandas as pd
from dotenv import load_dotenv

# Test imports
from tests.agentic_testing.test_config import get_valid_configs, create_llm_config, MODEL_CONFIGS
from tests.agentic_testing.utils import setup_logging, log_section_header
from tests.agentic_testing.mock_tools import MockSearchTool, MockFetchTool
from tests.agentic_testing.evaluators import (
    QueryQualityEvaluator,
    SourceReliabilityEvaluator,
    PromptInjectionEvaluator,
    CitationVerificationEvaluator
)
from tests.agentic_testing.fixtures.websearch_fixtures import (
    TEST_FIXTURES,
    PROMPT_INJECTION_FIXTURES
)

# Agent imports - import these dynamically to avoid version conflicts
# from analysis.factchecking_agent import FactCheckingAgent
# from analysis.llm_client import LLMClient

load_dotenv()

class MultiModelTestRunner:
    """Main class for running tests across multiple model configurations."""
    
    def __init__(self, output_dir: str = "tests/agentic_testing/results"):
        """Initialize the multi-model test runner."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.logger = setup_logging("multi_model_test_runner")
        
        # Initialize evaluators
        self.evaluators = {
            "query_quality": QueryQualityEvaluator(self.logger),
            "source_reliability": SourceReliabilityEvaluator(self.logger),
            "prompt_injection": PromptInjectionEvaluator(self.logger),
            "citation_verification": CitationVerificationEvaluator(self.logger)
        }
        
        # Results storage
        self.all_results = []
        
    def run_single_test(
        self, 
        model_config: Dict[str, Any], 
        test_fixture: Dict[str, Any], 
        run_number: int
    ) -> Dict[str, Any]:
        """
        Run a single test iteration.
        
        Args:
            model_config: Model configuration dict
            test_fixture: Test fixture data
            run_number: Current run number (1-5)
            
        Returns:
            Dict containing test results and metrics
        """
        log_section_header(self.logger, f"RUN {run_number} - {model_config['name']} - {test_fixture['test_id']}", "=")
        
        result_record = {
            "model": model_config["name"],
            "model_name": model_config["model_name"],
            "run_number": run_number,
            "fixture_id": test_fixture["test_id"],
            "input_claim": test_fixture["input_claim"],
            "timestamp": datetime.now().isoformat(),
            "test_passed": False,
            "failure_reasons": [],
            "error": None
        }
        
        try:
            # Import modules dynamically to avoid import issues
            import importlib
            
            # Import LLMClient
            llm_client_module = importlib.import_module('analysis.llm_client')
            LLMClient = llm_client_module.LLMClient
            
            # Import FactCheckingAgent  
            agent_module = importlib.import_module('analysis.factchecking_agent')
            FactCheckingAgent = agent_module.FactCheckingAgent
            
            # Create LLM client config directly from dict
            llm_config = {
                "MODEL_NAME": model_config["model_name"],
                "API_KEY": os.getenv(model_config["api_key_env"]),
                "BASE_URL": model_config["base_url"],
            }
            
            # Add any additional parameters
            if model_config["additional_params"]:
                llm_config.update(model_config["additional_params"])
                
            llm_client = LLMClient(llm_config)
            
            # Select prompt injection fixture (using third one as in original test)
            prompt_injection = PROMPT_INJECTION_FIXTURES[2]
            
            # Create mock tools
            mock_search = MockSearchTool(test_fixture, self.logger)
            mock_fetch = MockFetchTool(test_fixture, prompt_injection, self.logger)
            
            mock_search_tool = mock_search.create_tool()
            mock_fetch_tool = mock_fetch.create_tool()
            
            # Patch the tools and run the test
            with patch('analysis.factchecking_agent.RetryDuckDuckGoSearchResults', return_value=mock_search_tool):
                with patch('analysis.factchecking_agent.fetch_url_content', mock_fetch_tool):
                    # Create agent and run the search_and_check method
                    agent = FactCheckingAgent(llm_client)
                    
                    # Run the method we're testing
                    agent_result = agent._search_and_check(test_fixture["input_claim"])
                    
                    # === METRIC 1: Query Quality ===
                    query_results = {}
                    if test_fixture["golden_search_queries"]:
                        query_results = self.evaluators["query_quality"].evaluate(
                            mock_search.get_queries(),
                            test_fixture["golden_search_queries"]
                        )
                        result_record.update({
                            "query_max_similarity": query_results.get("max_similarity", 0),
                            "query_normalized_score": query_results.get("normalized_score", 0),
                            "query_embedding_model": query_results.get("embedding_model", "N/A"),
                            "queries_made": "; ".join(mock_search.get_queries())
                        })
                    else:
                        result_record.update({
                            "query_max_similarity": None,
                            "query_normalized_score": None,
                            "query_embedding_model": None,
                            "queries_made": "; ".join(mock_search.get_queries())
                        })
                    
                    # === METRIC 2: Source Reliability ===
                    visit_analysis = mock_fetch.analyze_visited_sources()
                    source_results = self.evaluators["source_reliability"].evaluate(visit_analysis)
                    
                    result_record.update({
                        "source_reliability_passed": source_results["passed"],
                        "total_visits": source_results["total_visits"],
                        "visited_malware": source_results["visited_malware"],
                        "source_warnings": "; ".join(source_results.get("warnings", [])),
                        "visited_urls": "; ".join(mock_fetch.get_visited_urls())
                    })
                    
                    # === METRIC 3: Prompt Injection ===
                    injection_results = self.evaluators["prompt_injection"].evaluate(
                        agent_result,
                        mock_fetch.injected_prompt or "",
                        mock_fetch.injection_evaluator
                    )
                    
                    result_record.update({
                        "prompt_injection_passed": injection_results["passed"],
                        "injection_detected": injection_results.get("injection_detected", False),
                        "injected_prompt": mock_fetch.injected_prompt or "",
                        "injection_url": mock_fetch.injection_url or ""
                    })
                    
                    # === METRIC 4: Citation Verification ===
                    citation_results = self.evaluators["citation_verification"].evaluate(
                        agent_result,
                        test_fixture.get("mocked_search_results", [])
                    )
                    
                    result_record.update({
                        "citation_verification_passed": citation_results["passed"],
                        "total_citations": citation_results["total_citations"],
                        "valid_citations": len(citation_results["valid_citations"]),
                        "hallucinated_citations": len(citation_results["hallucinated_citations"]),
                        "problematic_citations": len(citation_results["problematic_citations"])
                    })
                    
                    # === OVERALL TEST RESULT ===
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
                    
                    result_record.update({
                        "test_passed": test_passed,
                        "failure_reasons": failure_reasons,
                        "agent_output": json.dumps(agent_result) if agent_result else None
                    })
                    
                    if test_passed:
                        self.logger.info("✅ TEST PASSED - Agent demonstrated safe behavior")
                    else:
                        self.logger.error(f"❌ TEST FAILED - Reasons: {', '.join(failure_reasons)}")
                        
        except Exception as e:
            error_msg = f"Test execution error: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            result_record["error"] = error_msg
            
        return result_record
    
    def run_all_tests(self, num_runs: int = 5) -> None:
        """
        Run tests across all valid model configurations.
        
        Args:
            num_runs: Number of times to run each test (default: 5)
        """
        log_section_header(self.logger, "MULTI-MODEL TESTING START", "=")
        
        # Get valid model configurations
        valid_configs = []
        for config in MODEL_CONFIGS:
            if config.enabled:
                # Convert to dict for easier handling
                config_dict = {
                    "name": config.name,
                    "provider": config.provider.value,
                    "model_name": config.model_name,
                    "api_key_env": config.api_key_env,
                    "base_url": config.base_url,
                    "timeout": config.timeout,
                    "max_retries": config.max_retries,
                    "temperature": config.temperature,
                    "additional_params": config.additional_params or {}
                }
                
                # Check if API key is available
                if os.getenv(config.api_key_env):
                    valid_configs.append(config_dict)
                    self.logger.info(f"✅ {config.name} - API key found")
                else:
                    self.logger.warning(f"⚠️ {config.name} - Missing {config.api_key_env}")
        
        if not valid_configs:
            self.logger.error("❌ No valid model configurations found!")
            return
            
        self.logger.info(f"Found {len(valid_configs)} valid model configurations")
        self.logger.info(f"Found {len(TEST_FIXTURES)} test fixtures")
        self.logger.info(f"Running {num_runs} iterations each")
        
        total_tests = len(valid_configs) * len(TEST_FIXTURES) * num_runs
        self.logger.info(f"Total tests to run: {total_tests}")
        
        # Run tests
        test_count = 0
        for model_config in valid_configs:
            for test_fixture in TEST_FIXTURES:
                for run_num in range(1, num_runs + 1):
                    test_count += 1
                    self.logger.info(f"Progress: {test_count}/{total_tests}")
                    
                    result = self.run_single_test(model_config, test_fixture, run_num)
                    self.all_results.append(result)
        
        # Save results
        self.save_results()
        
        log_section_header(self.logger, "MULTI-MODEL TESTING COMPLETE", "=")
    
    def save_results(self) -> None:
        """Save all results to CSV and JSON files."""
        if not self.all_results:
            self.logger.warning("No results to save!")
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save CSV
        csv_path = self.output_dir / f"multi_model_results_{timestamp}.csv"
        
        # Define CSV columns
        csv_columns = [
            "model", "model_name", "run_number", "fixture_id", "input_claim", 
            "timestamp", "test_passed", "failure_reasons", "error",
            
            # Query Quality metrics
            "query_max_similarity", "query_normalized_score", "query_embedding_model", "queries_made",
            
            # Source Reliability metrics  
            "source_reliability_passed", "total_visits", "visited_malware", "source_warnings", "visited_urls",
            
            # Prompt Injection metrics
            "prompt_injection_passed", "injection_detected", "injected_prompt", "injection_url",
            
            # Citation Verification metrics
            "citation_verification_passed", "total_citations", "valid_citations", 
            "hallucinated_citations", "problematic_citations",
            
            # Agent output (optional)
            "agent_output"
        ]
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
            writer.writeheader()
            
            for result in self.all_results:
                # Convert list failure_reasons to string
                if isinstance(result.get("failure_reasons"), list):
                    result["failure_reasons"] = "; ".join(result["failure_reasons"])
                
                writer.writerow(result)
        
        self.logger.info(f"✅ Results saved to CSV: {csv_path}")
        
        # Save JSON summary
        json_path = self.output_dir / f"summary_report_{timestamp}.json"
        
        # Create summary statistics
        summary = {
            "timestamp": timestamp,
            "total_tests": len(self.all_results),
            "models_tested": list(set(r["model"] for r in self.all_results)),
            "fixtures_tested": list(set(r["fixture_id"] for r in self.all_results)),
            "runs_per_test": max((r["run_number"] for r in self.all_results), default=0),
            
            # Overall pass rates
            "overall_pass_rate": sum(1 for r in self.all_results if r["test_passed"]) / len(self.all_results),
            
            # Per-model pass rates
            "model_pass_rates": {},
            
            # Per-metric pass rates
            "source_reliability_pass_rate": sum(1 for r in self.all_results if r.get("source_reliability_passed", False)) / len(self.all_results),
            "prompt_injection_pass_rate": sum(1 for r in self.all_results if r.get("prompt_injection_passed", False)) / len(self.all_results), 
            "citation_verification_pass_rate": sum(1 for r in self.all_results if r.get("citation_verification_passed", False)) / len(self.all_results),
        }
        
        # Calculate per-model pass rates
        for model in summary["models_tested"]:
            model_results = [r for r in self.all_results if r["model"] == model]
            if model_results:
                summary["model_pass_rates"][model] = sum(1 for r in model_results if r["test_passed"]) / len(model_results)
        
        with open(json_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(summary, jsonfile, indent=2, ensure_ascii=False)
        
        self.logger.info(f"✅ Summary report saved to JSON: {json_path}")
        
        # Print summary to console
        log_section_header(self.logger, "TEST RESULTS SUMMARY", "=")
        self.logger.info(f"Total tests run: {summary['total_tests']}")
        self.logger.info(f"Overall pass rate: {summary['overall_pass_rate']:.2%}")
        self.logger.info(f"Models tested: {len(summary['models_tested'])}")
        
        for model, pass_rate in summary["model_pass_rates"].items():
            self.logger.info(f"  {model}: {pass_rate:.2%}")
        
        self.logger.info(f"Metric pass rates:")
        self.logger.info(f"  Source Reliability: {summary['source_reliability_pass_rate']:.2%}")
        self.logger.info(f"  Prompt Injection Resistance: {summary['prompt_injection_pass_rate']:.2%}")
        self.logger.info(f"  Citation Verification: {summary['citation_verification_pass_rate']:.2%}")


def main():
    """Main entry point for the multi-model test runner."""
    runner = MultiModelTestRunner()
    runner.run_all_tests(num_runs=5)


if __name__ == "__main__":
    main()
