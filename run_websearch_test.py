#!/usr/bin/env python3
"""
Automated test runner that automatically sets worker count based on active models.
"""

import subprocess
import sys
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()


MAX_WORKERS = 10

def get_active_model_count():
    """Get the number of active models from test_config.py"""
    try:
        # Add the project root to Python path
        project_root = Path(__file__).parent
        sys.path.insert(0, str(project_root))
        
        # Import test configuration
        from tests.agentic_testing.test_config import get_active_models
        
        active_models = get_active_models()
        return len(active_models)
    except Exception as e:
        print(f"Warning: Could not determine active model count: {e}")
        print("Falling back to 4 workers")
        return 4

def get_system_cpu_count():
    """Get the number of CPU cores on the system"""
    try:
        import multiprocessing
        return multiprocessing.cpu_count()
    except:
        return 4  # Fallback

def main():
    """Run websearch tests with optimal worker count"""
    
    # Get active model count
    model_count = get_active_model_count()
    cpu_count = get_system_cpu_count()
    
    # Cap worker count at CPU cores and maximum of 8
    worker_count = min(model_count, cpu_count, MAX_WORKERS)
    
    print(f"🔧 Configuration:")
    print(f"   Active models: {model_count}")
    print(f"   CPU cores: {cpu_count}")
    print(f"   Using workers: {worker_count} (max 10)")
    print()
    
    # Build command
    cmd = [
        "uv", "run", "pytest", 
        "tests/agentic_testing/test_websearch_agent.py",
        "-q", "--tb=no", 
        f"-n", str(worker_count),
        "--dist", "loadscope"
    ]
    
    # Add any additional arguments passed to the script
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])
    
    print(f"🚀 Running: {' '.join(cmd)}")
    print()
    
    # Run the command
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n❌ Test run interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
