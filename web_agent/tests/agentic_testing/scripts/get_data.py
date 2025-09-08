import csv
import json
import argparse
from datetime import datetime
from langfuse import get_client
from dotenv import load_dotenv

load_dotenv()

def parse_datetime_sgt(date_str):
    """Parse datetime string to datetime object (assuming SGT)."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M")
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD HH:MM")

def export_traces_to_csv(traces, filename, langfuse_client, detailed=False):
    """Export traces to CSV file with comprehensive data including observations."""
    if not traces.data:
        print("No traces found for the specified time range.")
        return
    
    csv_data = []
    
    for trace in traces.data:
        # Get observation details if available
        obs_summary = {
            'total_observations': len(trace.observations) if trace.observations else 0,
            'total_input_tokens': 0,
            'total_output_tokens': 0,
            'total_tokens': 0,
            'total_observation_cost': 0.0,
            'llm_calls': 0,
            'tool_calls': 0,
            'average_latency': 0.0
        }
        
        if trace.observations and detailed:
            print(f"  Processing {len(trace.observations)} observations for trace {trace.id}")
            latencies = []
            for obs_id in trace.observations:
                try:
                    obs = langfuse_client.api.observations.get(obs_id)
                    
                    # Aggregate token usage
                    if hasattr(obs, 'usage') and obs.usage:
                        obs_summary['total_input_tokens'] += getattr(obs.usage, 'input', 0) or 0
                        obs_summary['total_output_tokens'] += getattr(obs.usage, 'output', 0) or 0
                        obs_summary['total_tokens'] += getattr(obs.usage, 'total', 0) or 0
                        obs_summary['total_observation_cost'] += getattr(obs.usage, 'total_cost', 0) or 0
                    
                    # Count operation types
                    if hasattr(obs, 'type'):
                        if str(obs.type) == 'ObservationType.GENERATION':
                            obs_summary['llm_calls'] += 1
                        elif str(obs.type) == 'ObservationType.SPAN':
                            obs_summary['tool_calls'] += 1
                    
                    # Collect latency
                    if hasattr(obs, 'latency') and obs.latency:
                        latencies.append(obs.latency)
                        
                except Exception as e:
                    print(f"Warning: Could not fetch observation {obs_id}: {e}")
                    continue
            
            # Calculate average latency
            if latencies:
                obs_summary['average_latency'] = sum(latencies) / len(latencies)
        
        # Build comprehensive row
        row = {
            # Basic trace info
            'trace_id': trace.id,
            'trace_name': getattr(trace, 'name', ''),
            'user_id': getattr(trace, 'user_id', ''),
            'session_id': getattr(trace, 'session_id', ''),
            'timestamp': getattr(trace, 'timestamp', ''),
            'created_at': getattr(trace, 'createdAt', ''),
            'updated_at': getattr(trace, 'updatedAt', ''),
            
            # Performance metrics
            'latency_seconds': getattr(trace, 'latency', 0),
            'total_cost': getattr(trace, 'total_cost', 0),
            
            # Aggregated observation metrics
            'total_observations': obs_summary['total_observations'],
            'total_input_tokens': obs_summary['total_input_tokens'],
            'total_output_tokens': obs_summary['total_output_tokens'],
            'total_tokens': obs_summary['total_tokens'],
            'total_observation_cost': obs_summary['total_observation_cost'],
            'llm_calls': obs_summary['llm_calls'],
            'tool_calls': obs_summary['tool_calls'],
            'average_observation_latency': obs_summary['average_latency'],
            
            # Metadata
            'input': json.dumps(getattr(trace, 'input', {})) if hasattr(trace, 'input') else '',
            'output': str(getattr(trace, 'output', ''))[:500] + ('...' if len(str(getattr(trace, 'output', ''))) > 500 else ''),  # Truncate long outputs
            'metadata': json.dumps(getattr(trace, 'metadata', {})) if hasattr(trace, 'metadata') else '',
            'tags': json.dumps(getattr(trace, 'tags', [])) if hasattr(trace, 'tags') else '',
            'environment': getattr(trace, 'environment', ''),
            'version': getattr(trace, 'version', ''),
        }
        csv_data.append(row)
    
    # Write to CSV
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        if csv_data:
            fieldnames = csv_data[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_data)
    
    print(f"✅ Exported {len(csv_data)} traces to {filename}")
    print(f"   Columns: {', '.join(list(csv_data[0].keys()) if csv_data else [])}")

def main():
    """Main function to run the CLI."""
    parser = argparse.ArgumentParser(description="Export Langfuse traces to CSV")
    parser.add_argument("--start", required=True, help="Start date and time (SGT) in format: YYYY-MM-DD HH:MM")
    parser.add_argument("--end", required=True, help="End date and time (SGT) in format: YYYY-MM-DD HH:MM")
    parser.add_argument("--output", help="Output CSV filename (optional, auto-generated if not provided)")
    parser.add_argument("--detailed", action="store_true", help="Include detailed observation data (slower but more comprehensive)")
    
    args = parser.parse_args()
    
    langfuse = get_client()
    
    try:
        start_time = parse_datetime_sgt(args.start)
        end_time = parse_datetime_sgt(args.end)
        
        print(f"Fetching traces from {start_time} to {end_time} SGT...")
        
        # Fetch all traces with pagination
        all_traces = []
        page = 1
        limit = 50  # API default limit
        
        print("Fetching all traces (paginated)...")
        while True:
            traces = langfuse.api.trace.list(
                from_timestamp=start_time, 
                to_timestamp=end_time,
                limit=limit,
                page=page
            )
            
            if not traces.data:
                break
                
            all_traces.extend(traces.data)
            print(f"  Fetched page {page}: {len(traces.data)} traces (total: {len(all_traces)})")
            
            # If we got less than the limit, we've reached the end
            if len(traces.data) < limit:
                break
                
            page += 1
        
        # Generate filename if not provided
        if args.output:
            filename = args.output
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"langfuse_traces_{timestamp}.csv"
        
        # Create a mock traces object for the export function
        class MockTraces:
            def __init__(self, data):
                self.data = data
        
        export_traces_to_csv(MockTraces(all_traces), filename, langfuse, args.detailed)
        
    except ValueError as e:
        print(f"❌ {e}")
    except Exception as e:
        print(f"❌ Error fetching traces: {e}")

if __name__ == "__main__":
    main()