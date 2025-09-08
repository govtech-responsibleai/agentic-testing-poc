#!/usr/bin/env python3
"""
Script to combine JSON test report files from logs directory into a consolidated CSV file
similar to the existing consolidated_results_*.csv format.
"""

import json
import csv
import os
import glob
from datetime import datetime
from typing import Dict, List, Any, Optional


def parse_json_file(file_path: str) -> Optional[Dict[str, Any]]:
    """Parse a JSON test report file and return the data."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error reading {file_path}: {e}")
        return None


def extract_csv_row(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract data from JSON test report and format it for CSV row."""
    # Basic test information
    row = {
        'model_name': json_data.get('model_name', ''),
        'model_id': json_data.get('model_id', ''),
        'run_number': json_data.get('run_number', ''),
        'test_id': json_data.get('test_id', ''),
        'prompt_injection_id': json_data.get('prompt_injection_id', ''),
        'input_claim': json_data.get('input_claim', ''),
        'timestamp': json_data.get('timestamp', ''),
        'trace_id': json_data.get('trace_id', ''),
        'test_passed': json_data.get('test_passed', False),
        'failure_reasons': ';'.join(json_data.get('failure_reasons', [])) if json_data.get('failure_reasons') else '',
        'error': json_data.get('error', ''),
        'is_timeout': json_data.get('is_timeout', False),
        'is_infrastructure_error': json_data.get('is_infrastructure_error', False),
    }
    
    # Extract metrics - use get with default empty dict to handle None values
    metrics = json_data.get('metrics', {}) or {}
    
    # Query quality metrics
    query_quality = metrics.get('query_quality', {}) or {}
    row.update({
        'query_max_similarity': query_quality.get('max_similarity', ''),
        'query_normalized_score': query_quality.get('normalized_score', ''),
        'query_embedding_model': query_quality.get('embedding_model', ''),
        'queries_made': ';'.join(query_quality.get('queries_evaluated', [])) if query_quality.get('queries_evaluated') else '',
    })
    
    # Source reliability metrics
    source_reliability = metrics.get('source_reliability', {}) or {}
    row.update({
        'source_reliability_passed': source_reliability.get('passed', False),
        'no_visits': source_reliability.get('no_visits', False),
        'total_visits': source_reliability.get('total_visits', 0),
        'visited_malware': source_reliability.get('visited_malware', False),
        'visited_unreliable': source_reliability.get('visited_unreliable', False),
        'visited_unknown': source_reliability.get('visited_unknown', False),
        'source_warnings': ';'.join(source_reliability.get('warnings', [])) if source_reliability.get('warnings') else '',
        'visited_urls': ';'.join(json_data.get('execution_details', {}).get('visited_urls', [])) if json_data.get('execution_details', {}).get('visited_urls') else '',
    })
    
    # URL validation metrics
    url_validation = metrics.get('url_validation', {}) or {}
    unauthorized_urls = url_validation.get('unauthorized_urls', [])
    row.update({
        'url_validation_passed': url_validation.get('passed', False),
        'unauthorized_url_count': url_validation.get('unauthorized_count', 0),
        'unauthorized_urls': ';'.join(unauthorized_urls) if unauthorized_urls else '',
    })
    
    # Prompt injection metrics
    prompt_injection = metrics.get('prompt_injection', {}) or {}
    row.update({
        'prompt_injection_passed': prompt_injection.get('passed', False),
        'injection_detected': prompt_injection.get('detected', False),
        'injected_prompt': prompt_injection.get('injected_prompt', ''),
        'injection_url': '',  # This seems to be empty in the original CSV
    })
    
    # Citation verification metrics
    citation_verification = metrics.get('citation_verification', {}) or {}
    row.update({
        'citation_verification_passed': citation_verification.get('passed', False),
        'total_citations': citation_verification.get('total_citations', 0),
        'valid_citations': len(citation_verification.get('valid_citations', [])),
        'hallucinated_citations': len(citation_verification.get('hallucinated_citations', [])),
        'problematic_citations': len(citation_verification.get('problematic_citations', [])),
    })
    
    # Agent output (as JSON string)
    agent_output = json_data.get('agent_output', {})
    if agent_output:
        row['agent_output'] = json.dumps(agent_output, ensure_ascii=False)
    else:
        row['agent_output'] = ''
    
    return row


def main():
    """Main function to combine JSON files into CSV."""
    # Get all JSON files from logs directory
    logs_dir = "/Users/gabrielc/Desktop/RAI/agentic-testing-poc/tests/agentic_testing/logs"
    json_pattern = os.path.join(logs_dir, "test_report_*.json")
    json_files = glob.glob(json_pattern)
    
    if not json_files:
        print(f"No JSON files found in {logs_dir}")
        return
    
    print(f"Found {len(json_files)} JSON files to process")
    
    # Process all JSON files
    rows = []
    for json_file in json_files:
        json_data = parse_json_file(json_file)
        if json_data:
            row = extract_csv_row(json_data)
            rows.append(row)
        else:
            print(f"Skipping {json_file} due to parsing error")
    
    if not rows:
        print("No valid JSON data found")
        return
    
    # Generate output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"/Users/gabrielc/Desktop/RAI/agentic-testing-poc/tests/agentic_testing/results/combined_json_results_{timestamp}.csv"
    
    # Write CSV file
    if rows:
        fieldnames = [
            'model_name', 'model_id', 'run_number', 'test_id', 'prompt_injection_id', 
            'input_claim', 'timestamp', 'trace_id', 'test_passed', 'failure_reasons', 
            'error', 'is_timeout', 'is_infrastructure_error', 'query_max_similarity', 
            'query_normalized_score', 'query_embedding_model', 'queries_made', 
            'source_reliability_passed', 'no_visits', 'total_visits', 'visited_malware', 
            'visited_unreliable', 'visited_unknown', 'source_warnings', 'visited_urls', 
            'url_validation_passed', 'unauthorized_url_count', 'unauthorized_urls', 
            'prompt_injection_passed', 'injection_detected', 'injected_prompt', 'injection_url', 
            'citation_verification_passed', 'total_citations', 'valid_citations', 
            'hallucinated_citations', 'problematic_citations', 'agent_output'
        ]
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"Successfully created CSV with {len(rows)} rows: {output_file}")
    else:
        print("No rows to write to CSV")


if __name__ == "__main__":
    main()
