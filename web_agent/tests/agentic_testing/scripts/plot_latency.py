#!/usr/bin/env python3
"""
Latency Analysis Tool for Langfuse Traces

Creates 4-panel boxplot visualization comparing latency distributions by model:
- All traces
- Passed tests only  
- Failed tests only
- Infrastructure/timeout errors

Author: Agentic Testing POC
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
import sys
from pathlib import Path


def extract_model_from_trace_id(trace_id):
    """Extract model name from trace ID pattern: websearch_XXXXX-MODEL-uuid"""
    try:
        parts = trace_id.split('-')
        if len(parts) >= 6:
            model_parts = parts[1:-5]  # Everything except websearch_XXXXX and UUID
            return ' '.join(model_parts)
        return 'Unknown'
    except:
        return 'Unknown'


def load_and_merge_data(traces_file, results_file):
    """Load and merge traces with test results."""
    # Validate file paths
    if not Path(traces_file).exists():
        raise FileNotFoundError(f"Traces file not found: {traces_file}")
    if not Path(results_file).exists():
        raise FileNotFoundError(f"Results file not found: {results_file}")
    
    print(f"Loading traces from: {traces_file}")
    df_traces = pd.read_csv(traces_file)
    
    print(f"Loading results from: {results_file}")
    df_results = pd.read_csv(results_file)
    
    # Add model column to traces
    df_traces['model'] = df_traces['trace_id'].apply(extract_model_from_trace_id)
    
    # Merge on trace_id - include infra/timeout columns
    merge_columns = ['trace_id', 'test_passed', 'is_timeout', 'is_infrastructure_error']
    df = pd.merge(df_traces, df_results[merge_columns], on='trace_id', how='inner')
    
    # Remove Unknown models
    df = df[df['model'] != 'Unknown'].copy()
    
    return df


def create_latency_plots(df, output_file='latency_by_model.png'):
    """Create 4-panel latency boxplot visualization."""
    
    # Split data into categories
    df_passed = df[df['test_passed'] == True].copy()
    df_failed = df[(df['test_passed'] == False) & (df['is_timeout'] == False) & (df['is_infrastructure_error'] == False)].copy()
    df_infra = df[(df['is_timeout'] == True) | (df['is_infrastructure_error'] == True)].copy()
    
    # Print summary
    print(f"\nData Summary:")
    print(f"  Total traces: {len(df)}")
    print(f"  Passed: {len(df_passed)} ({len(df_passed)/len(df)*100:.1f}%)")
    print(f"  Failed: {len(df_failed)} ({len(df_failed)/len(df)*100:.1f}%)")
    print(f"  Infrastructure/Timeout: {len(df_infra)} ({len(df_infra)/len(df)*100:.1f}%)")
    print(f"  Models: {df['model'].nunique()}")
    
    # Get global x-axis limits for log scale
    x_min = max(df['latency_seconds'].min() * 0.8, 1)  # Avoid log(0)
    x_max = df['latency_seconds'].max() * 1.2
    x_range = (x_min, x_max)
    
    # Sort models by overall median latency (longest at top)
    median_latencies = df.groupby('model')['latency_seconds'].median().sort_values(ascending=False)
    model_order = median_latencies.index.tolist()
    
    # Create 4-panel plot
    fig, axes = plt.subplots(1, 4, figsize=(24, 10), sharey=True)
    
    # Panel 1: All traces
    sns.boxplot(data=df, y='model', x='latency_seconds', order=model_order, ax=axes[0])
    axes[0].set_title(f'All Traces (n={len(df)})', fontsize=14, fontweight='bold')
    axes[0].set_ylabel('Model', fontsize=12)
    axes[0].set_xlabel('Latency (seconds, log scale)', fontsize=12)
    axes[0].grid(True, alpha=0.3, axis='x')
    axes[0].set_xscale('log')
    axes[0].set_xlim(x_range)
    
    # Panel 2: Passed tests
    if len(df_passed) > 0:
        # Use same model order for consistency
        models_with_passed = df_passed['model'].unique()
        model_order_passed = [m for m in model_order if m in models_with_passed]
        sns.boxplot(data=df_passed, y='model', x='latency_seconds', order=model_order_passed, ax=axes[1])
    else:
        axes[1].text(0.5, 0.5, 'No passed tests', transform=axes[1].transAxes, 
                    ha='center', va='center', fontsize=12)
    axes[1].set_title(f'Passed Tests (n={len(df_passed)})', fontsize=14, fontweight='bold')
    axes[1].set_ylabel('')
    axes[1].set_xlabel('Latency (seconds, log scale)', fontsize=12)
    axes[1].grid(True, alpha=0.3, axis='x')
    axes[1].set_xscale('log')
    axes[1].set_xlim(x_range)
    
    # Panel 3: Failed tests
    if len(df_failed) > 0:
        # Use same model order for consistency
        models_with_failed = df_failed['model'].unique()
        model_order_failed = [m for m in model_order if m in models_with_failed]
        sns.boxplot(data=df_failed, y='model', x='latency_seconds', order=model_order_failed, ax=axes[2])
    else:
        axes[2].text(0.5, 0.5, 'No failed tests', transform=axes[2].transAxes, 
                    ha='center', va='center', fontsize=12)
    axes[2].set_title(f'Failed Tests (n={len(df_failed)})', fontsize=14, fontweight='bold')
    axes[2].set_ylabel('')
    axes[2].set_xlabel('Latency (seconds, log scale)', fontsize=12)
    axes[2].grid(True, alpha=0.3, axis='x')
    axes[2].set_xscale('log')
    axes[2].set_xlim(x_range)
    
    # Panel 4: Infrastructure/Timeout errors
    if len(df_infra) > 0:
        # Use same model order for consistency
        models_with_infra = df_infra['model'].unique()
        model_order_infra = [m for m in model_order if m in models_with_infra]
        sns.boxplot(data=df_infra, y='model', x='latency_seconds', order=model_order_infra, ax=axes[3])
    else:
        axes[3].text(0.5, 0.5, 'No infra/timeout errors', transform=axes[3].transAxes, 
                    ha='center', va='center', fontsize=12)
    axes[3].set_title(f'Infra/Timeout Errors (n={len(df_infra)})', fontsize=14, fontweight='bold')
    axes[3].set_ylabel('')
    axes[3].set_xlabel('Latency (seconds, log scale)', fontsize=12)
    axes[3].grid(True, alpha=0.3, axis='x')
    axes[3].set_xscale('log')
    axes[3].set_xlim(x_range)
    
    plt.suptitle('Latency Distribution by Model and Test Result', fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✅ Plot saved as: {output_file}")
    plt.show()


def print_statistics(df):
    """Print comprehensive statistics."""
    print(f"\nLatency Statistics by Model (sorted by median):")
    print("=" * 80)
    stats = df.groupby('model')['latency_seconds'].agg(['count', 'mean', 'median', 'std', 'min', 'max'])
    stats_sorted = stats.sort_values('median', ascending=False)
    
    # Format for better readability
    stats_formatted = stats_sorted.copy()
    for col in ['mean', 'median', 'std', 'min', 'max']:
        stats_formatted[col] = stats_formatted[col].round(1)
    
    print(stats_formatted)
    
    # Pass/fail rates by model
    print(f"\nPass Rate by Model:")
    print("=" * 40)
    pass_rates = df.groupby('model')['test_passed'].agg(['count', 'sum', 'mean'])
    pass_rates['pass_rate_pct'] = (pass_rates['mean'] * 100).round(1)
    pass_rates_sorted = pass_rates.sort_values('pass_rate_pct', ascending=False)
    
    print(pass_rates_sorted[['count', 'sum', 'pass_rate_pct']].rename(columns={
        'count': 'total', 'sum': 'passed', 'pass_rate_pct': 'pass_rate_%'
    }))


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Generate latency analysis plots for Langfuse traces",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python plot_latency.py --traces traces.csv --results results.csv
  python plot_latency.py --traces filtered_langfuse_traces_20250903.csv --results tests/agentic_testing/results/combined_json_results_20250903_101133.csv
        """
    )
    
    parser.add_argument("--traces", required=True, 
                       help="Path to CSV file containing Langfuse traces")
    parser.add_argument("--results", required=True,
                       help="Path to CSV file containing test results with trace_id and test_passed columns")
    parser.add_argument("--output", default="latency_by_model.png",
                       help="Output filename for the plot (default: latency_by_model.png)")
    
    args = parser.parse_args()
    
    try:
        # Load and process data
        df = load_and_merge_data(args.traces, args.results)
        
        if df.empty:
            print("❌ No data found after merging traces and results")
            sys.exit(1)
        
        # Create plots
        create_latency_plots(df, args.output)
        
        # Print statistics
        print_statistics(df)
        
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
