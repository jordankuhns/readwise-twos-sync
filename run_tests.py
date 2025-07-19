#!/usr/bin/env python3
"""
Test runner script for the Readwise-Twos sync application
"""

import sys
import subprocess
import os
from pathlib import Path

def run_tests():
    """Run the test suite with appropriate configuration."""
    
    # Ensure we're in the project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Set environment variables for testing
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['TESTING'] = 'true'
    
    # Basic test command
    cmd = [
        sys.executable, '-m', 'pytest',
        'tests/',
        '-v',
        '--tb=short',
        '--color=yes'
    ]
    
    # Add coverage if available
    try:
        import coverage
        cmd.extend([
            '--cov=backend',
            '--cov-report=term-missing',
            '--cov-report=html:htmlcov'
        ])
        print("Running tests with coverage...")
    except ImportError:
        print("Running tests without coverage (install pytest-cov for coverage reports)...")
    
    # Run the tests
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

def run_specific_test(test_path):
    """Run a specific test file or test function."""
    cmd = [
        sys.executable, '-m', 'pytest',
        test_path,
        '-v',
        '--tb=short',
        '--color=yes'
    ]
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except Exception as e:
        print(f"Error running test {test_path}: {e}")
        return 1

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific test
        test_path = sys.argv[1]
        exit_code = run_specific_test(test_path)
    else:
        # Run all tests
        exit_code = run_tests()
    
    sys.exit(exit_code)