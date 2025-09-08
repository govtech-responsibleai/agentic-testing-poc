"""
Pytest configuration for websearch agent tests.
Handles model-based test grouping to prevent concurrent API calls to same model.
"""
import json
import csv
import os
from datetime import datetime
from pathlib import Path

def pytest_xdist_make_scheduler(config, log):
    """Custom scheduler that allows work stealing while preventing model conflicts."""
    from xdist.scheduler import LoadScheduling
    import threading
    
    class ModelAwareWorkStealingScheduling(LoadScheduling):
        """
        Load-balanced scheduler that prevents concurrent API calls to the same model.
        Allows workers to help with other models when done, improving load balancing.
        """
        
        def __init__(self, config, log):
            super().__init__(config, log)
            # Track which models are currently being worked on by any worker
            self.active_models = set()
            self.model_lock = threading.Lock()
            self.worker_current_model = {}  # worker_id -> current_model
            
        def _get_model_from_nodeid(self, nodeid):
            """Extract model name from test nodeid."""
            # Format: test_search_and_check_safety[websearch_prompt_injection_00001-websearch_00001-GLM 4.5-run_1]
            parts = nodeid.split('[')
            if len(parts) > 1:
                param_str = parts[1].rstrip(']')
                params = param_str.split('-')
                if len(params) >= 4:
                    # Model name is everything between the second and the last parameter
                    # Join back the model name parts that were split by '-'
                    model_name = '-'.join(params[2:-1])
                    return model_name
            return "default"
        
        def _can_assign_test_to_node(self, node, test_item):
            """Check if we can assign this test to the node without model conflicts."""
            model = self._get_model_from_nodeid(test_item.nodeid)
            
            with self.model_lock:
                # If model is not currently being worked on, we can assign it
                if model not in self.active_models:
                    return True
                    
                # If this worker is already working on this model, allow it
                current_model = self.worker_current_model.get(node)
                if current_model == model:
                    return True
                    
                return False
        
        def schedule(self):
            """Override schedule to implement model-aware work distribution."""
            # First, let workers finish their current work
            super().schedule()
            
            # Then handle model-aware distribution for remaining tests
            while self.pending and self.node2pending:
                assigned_any = False
                
                for node in list(self.node2pending.keys()):
                    if not self.pending:
                        break
                    
                    if len(self.node2pending[node]) >= 1:
                        # Worker already has work, skip for now
                        continue
                        
                    # Find a test this worker can take without model conflicts
                    for i, item in enumerate(self.pending):
                        if self._can_assign_test_to_node(node, item):
                            model = self._get_model_from_nodeid(item.nodeid)
                            
                            with self.model_lock:
                                # Mark this model as active and assign to worker
                                self.active_models.add(model)
                                self.worker_current_model[node] = model
                            
                            # Remove from pending and assign
                            test_item = self.pending.pop(i)
                            self.node2pending[node].append(test_item)
                            assigned_any = True
                            
                            # Log assignment for debugging (disabled for cleaner output)
                            # if hasattr(self, 'log'):
                            #     self.log(f"Assigned {model} test to worker {node}")
                            break
                
                # If no assignments were possible, break to avoid infinite loop
                if not assigned_any:
                    break
    
    # Create scheduler instance and store globally for hooks
    scheduler = ModelAwareWorkStealingScheduling(config, log)
    global _scheduler
    _scheduler = scheduler
    return scheduler

# Global scheduler instance to track model state across hooks
_scheduler = None

def pytest_runtest_logstart(nodeid, location):
    """Hook called when a test starts."""
    pass

def pytest_runtest_logfinish(nodeid, location):
    """Hook called when a test finishes - free up the model."""
    global _scheduler
    if _scheduler and hasattr(_scheduler, '_get_model_from_nodeid'):
        model = _scheduler._get_model_from_nodeid(nodeid)
        
        # Find which worker was running this test and free the model
        with _scheduler.model_lock:
            # Free the model so other workers can pick it up
            _scheduler.active_models.discard(model)
            
            # Remove worker-model mapping for completed tests
            for worker, worker_model in list(_scheduler.worker_current_model.items()):
                if worker_model == model:
                    del _scheduler.worker_current_model[worker]
                    break

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "model_based: mark test to run with model-based scheduling"
    )

def pytest_sessionfinish(session, exitstatus):
    """Generate CSV summary when test session finishes."""
    try:
        # Import the function from the test module
        from tests.agentic_testing.test_websearch_agent import save_multi_model_results
        
        # Check if this is a worker process or main process
        is_worker = hasattr(session.config, 'workerinput')
        
        if is_worker:
            # Worker process - generate individual CSV
            worker_suffix = session.config.workerinput.get('workerid', 'worker')
            save_multi_model_results(worker_suffix=worker_suffix)
        else:
            # Main process - generate individual CSV then merge all worker CSVs
            save_multi_model_results()
            
            # Wait a moment for workers to finish writing their files
            import time
            time.sleep(1)
            
            # Merge all worker CSV files
            merge_worker_csv_files()
            
    except Exception as e:
        print(f"Error generating CSV summary: {e}")


def merge_worker_csv_files():
    """Merge all worker CSV files into a single consolidated file."""
    try:
        import pandas as pd
        import glob
        from pathlib import Path
        from datetime import datetime
        
        results_dir = Path("tests/agentic_testing/results")
        
        # Find all worker CSV files
        csv_pattern = str(results_dir / "multi_model_results_*_gw*.csv")
        all_csv_files = glob.glob(csv_pattern)
        
        if not all_csv_files:
            print("No worker CSV files found to merge")
            return
        
        # Group files by their timestamp segment (between prefix and _gw)
        def extract_ts(path: str) -> str:
            name = Path(path).name
            # Expected: multi_model_results_YYYYMMDD_HHMMSS_gwX.csv
            try:
                middle = name.split("multi_model_results_")[-1]
                ts = middle.split("_gw")[0]
                return ts
            except Exception:
                return ""
        
        ts_to_files = {}
        for f in all_csv_files:
            ts = extract_ts(f)
            if ts:
                ts_to_files.setdefault(ts, []).append(f)
        
        if not ts_to_files:
            print("No properly formatted worker CSV files to merge")
            return
        
        # Select the most recent timestamp group only
        latest_ts = sorted(ts_to_files.keys())[-1]
        csv_files = ts_to_files[latest_ts]
        print(f"🔄 Merging {len(csv_files)} worker CSV files for run {latest_ts}...")
        
        # Read and combine all CSV files for the latest run
        dfs = []
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)
                dfs.append(df)
            except Exception as e:
                print(f"Error reading {csv_file}: {e}")
        
        if not dfs:
            print("No valid CSV files to merge")
            return
        
        # Combine all dataframes
        merged_df = pd.concat(dfs, ignore_index=True)
        
        # Sort by timestamp and model for consistent output
        if 'timestamp' in merged_df.columns:
            merged_df = merged_df.sort_values(['timestamp', 'model_name', 'test_id'])
        
        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = results_dir / f"consolidated_results_{timestamp}.csv"
        
        # Save merged file
        merged_df.to_csv(output_file, index=False)
        print(f"✅ Consolidated {len(merged_df)} rows into: {output_file}")
        
        # Generate comprehensive text summary
        generate_text_summary(merged_df, results_dir, timestamp)
        
        # Delete worker CSV files after successful merge
        print("🧹 Cleaning up worker CSV files...")
        for csv_file in csv_files:
            try:
                os.remove(csv_file)
                print(f"   Deleted: {Path(csv_file).name}")
            except Exception as e:
                print(f"   Error deleting {csv_file}: {e}")
        
        # Keep worker JSON summary files (not deleted)
        
        # Delete worker TXT summary files only for this run timestamp
        txt_pattern = str(results_dir / f"summary_report_{latest_ts}_gw*.txt")
        txt_files = glob.glob(txt_pattern)
        for txt_file in txt_files:
            try:
                os.remove(txt_file)
                print(f"   Deleted: {Path(txt_file).name}")
            except Exception as e:
                print(f"   Error deleting {txt_file}: {e}")
        
    except ImportError:
        print("pandas not available - skipping CSV merge")
    except Exception as e:
        print(f"Error merging CSV files: {e}")


def generate_text_summary(df, results_dir, timestamp):
    """Generate comprehensive text summary report."""
    try:
        # Filter out infrastructure errors for pass rate calculations
        valid_tests = df[df['is_infrastructure_error'] != True]
        
        total_tests = len(df)
        valid_completions = len(valid_tests)
        timeout_tests = len(df[df['is_timeout'] == True])
        infra_error_tests = len(df[df['is_infrastructure_error'] == True])
        
        # Overall pass rate (excluding infrastructure errors)
        overall_passed = len(valid_tests[valid_tests['test_passed'] == True])
        overall_pass_rate = (overall_passed / valid_completions * 100) if valid_completions > 0 else 0
        
        summary_lines = []
        summary_lines.append("=" * 60)
        summary_lines.append("TEST SUMMARY")
        summary_lines.append("=" * 60)
        summary_lines.append(f"Total Tests: {total_tests:,}")
        summary_lines.append(f"Valid Completions: {valid_completions:,} ({timeout_tests} timeouts, {infra_error_tests} infra errors)")
        summary_lines.append(f"Overall Pass Rate: {overall_pass_rate:.1f}%")
        summary_lines.append("")
        
        # Model Performance
        summary_lines.append("Model Performance:")
        model_stats = []
        for model in valid_tests['model_name'].unique():
            model_tests = valid_tests[valid_tests['model_name'] == model]
            model_passed = len(model_tests[model_tests['test_passed'] == True])
            model_total = len(model_tests)
            model_pass_rate = (model_passed / model_total * 100) if model_total > 0 else 0
            model_stats.append((model, model_pass_rate))
        
        # Sort by pass rate descending
        model_stats.sort(key=lambda x: x[1], reverse=True)
        for model, pass_rate in model_stats:
            summary_lines.append(f"  {model}: {pass_rate:.1f}% pass rate")
        
        summary_lines.append("")
        
        # Fixture Performance
        if 'test_id' in valid_tests.columns:
            summary_lines.append("Fixture Performance:")
            fixture_stats = []
            for fixture in valid_tests['test_id'].unique():
                fixture_tests = valid_tests[valid_tests['test_id'] == fixture]
                fixture_passed = len(fixture_tests[fixture_tests['test_passed'] == True])
                fixture_total = len(fixture_tests)
                fixture_pass_rate = (fixture_passed / fixture_total * 100) if fixture_total > 0 else 0
                fixture_stats.append((fixture, fixture_pass_rate))
            
            # Sort by pass rate descending
            fixture_stats.sort(key=lambda x: x[1], reverse=True)
            for fixture, pass_rate in fixture_stats:
                summary_lines.append(f"  {fixture}: {pass_rate:.1f}% pass rate")
            
            summary_lines.append("")
        
        # Metric Pass Rates
        summary_lines.append("Metric Pass Rates:")
        
        # Source Reliability
        source_passed = len(valid_tests[valid_tests['source_reliability_passed'] == True])
        source_rate = (source_passed / valid_completions * 100) if valid_completions > 0 else 0
        summary_lines.append(f"  Source Reliability: {source_rate:.1f}%")
        
        # URL Validation
        url_passed = len(valid_tests[valid_tests['url_validation_passed'] == True])
        url_rate = (url_passed / valid_completions * 100) if valid_completions > 0 else 0
        summary_lines.append(f"  URL Validation: {url_rate:.1f}%")
        
        # Prompt Injection
        injection_passed = len(valid_tests[valid_tests['prompt_injection_passed'] == True])
        injection_rate = (injection_passed / valid_completions * 100) if valid_completions > 0 else 0
        summary_lines.append(f"  Prompt Injection: {injection_rate:.1f}%")
        
        # Citation Verification
        citation_passed = len(valid_tests[valid_tests['citation_verification_passed'] == True])
        citation_rate = (citation_passed / valid_completions * 100) if valid_completions > 0 else 0
        summary_lines.append(f"  Citation Verification: {citation_rate:.1f}%")
        
        summary_lines.append("=" * 60)
        
        # Save text summary
        summary_file = results_dir / f"consolidated_summary_{timestamp}.txt"
        with open(summary_file, 'w') as f:
            f.write('\n'.join(summary_lines))
        
        print(f"📊 Text summary saved to: {summary_file}")
        
        # Print summary to console
        print("\n" + '\n'.join(summary_lines))
        
    except Exception as e:
        print(f"Error generating text summary: {e}")
