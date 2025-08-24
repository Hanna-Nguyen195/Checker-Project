#!/usr/bin/env python3
"""
Test runner script for the plagiarism detection system.
Provides options to run different test suites and manage test environment.
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path


def run_command(cmd: str, cwd: str = None) -> int:
    """Run a shell command and return exit code."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    return result.returncode


def check_docker_compose():
    """Check if docker-compose is available."""
    try:
        subprocess.run(["docker-compose", "--version"], 
                      capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            subprocess.run(["docker", "compose", "version"], 
                          capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False


def start_test_services():
    """Start test services using Docker Compose."""
    print("Starting test services...")
    
    if not check_docker_compose():
        print("Error: docker-compose or docker compose not found!")
        return False
    
    # Try docker compose first, then docker-compose
    cmd = "docker compose -f docker-compose.test.yml up -d"
    if run_command(cmd) != 0:
        cmd = "docker-compose -f docker-compose.test.yml up -d"
        if run_command(cmd) != 0:
            print("Failed to start test services!")
            return False
    
    print("Waiting for services to be ready...")
    time.sleep(10)
    return True


def stop_test_services():
    """Stop test services."""
    print("Stopping test services...")
    
    cmd = "docker compose -f docker-compose.test.yml down"
    if run_command(cmd) != 0:
        cmd = "docker-compose -f docker-compose.test.yml down"
        run_command(cmd)


def run_tests(test_type: str = "all", verbose: bool = False, coverage: bool = False):
    """Run the specified test suite."""
    project_root = Path(__file__).parent.parent
    
    # Base pytest command
    pytest_cmd = ["python", "-m", "pytest"]
    
    if verbose:
        pytest_cmd.append("-v")
    
    if coverage:
        pytest_cmd.extend([
            "--cov=app",
            "--cov-report=html",
            "--cov-report=term-missing"
        ])
    
    # Add test selection based on type
    if test_type == "unit":
        pytest_cmd.extend([
            "tests/test_auth.py",
            "-k", "not integration"
        ])
    elif test_type == "integration":
        pytest_cmd.extend([
            "tests/test_integration_auth.py",
            "tests/test_integration_documents.py",
            "tests/test_integration_plagiarism.py",
            "tests/test_integration_admin.py",
            "tests/test_integration_storage.py"
        ])
    elif test_type == "e2e":
        pytest_cmd.append("tests/test_integration_end_to_end.py")
    elif test_type == "all":
        pytest_cmd.append("tests/")
    else:
        pytest_cmd.append(f"tests/{test_type}")
    
    # Run tests
    print(f"Running {test_type} tests...")
    cmd = " ".join(pytest_cmd)
    return run_command(cmd, cwd=str(project_root))


def setup_test_env():
    """Set up test environment variables."""
    env_vars = {
        "DATABASE_URL": "postgresql://postgres:postgres123@localhost:5433/plagiarism_detector_test",
        "MINIO_ENDPOINT": "localhost:9002",
        "MINIO_ACCESS_KEY": "testadmin",
        "MINIO_SECRET_KEY": "testadmin123",
        "MINIO_SECURE": "false",
        "MINIO_BUCKET_NAME": "test-documents",
        "JWT_SECRET_KEY": "test-secret-key-for-testing-only",
        "JWT_ALGORITHM": "HS256",
        "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "30",
        "ENVIRONMENT": "test"
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
    
    print("Test environment variables set.")


def main():
    parser = argparse.ArgumentParser(description="Run tests for plagiarism detection system")
    parser.add_argument(
        "test_type",
        nargs="?",
        default="all",
        choices=["unit", "integration", "e2e", "all"],
        help="Type of tests to run (default: all)"
    )
    parser.add_argument(
        "--no-services",
        action="store_true",
        help="Don't start/stop Docker services"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose test output"
    )
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Generate coverage report"
    )
    parser.add_argument(
        "--keep-services",
        action="store_true",
        help="Keep test services running after tests"
    )
    
    args = parser.parse_args()
    
    # Set up test environment
    setup_test_env()
    
    services_started = False
    exit_code = 0
    
    try:
        # Start services if needed
        if not args.no_services and args.test_type in ["integration", "e2e", "all"]:
            if not start_test_services():
                return 1
            services_started = True
        
        # Run tests
        exit_code = run_tests(
            test_type=args.test_type,
            verbose=args.verbose,
            coverage=args.coverage
        )
        
        if exit_code == 0:
            print(f"\n✅ {args.test_type.title()} tests passed!")
        else:
            print(f"\n❌ {args.test_type.title()} tests failed!")
        
    except KeyboardInterrupt:
        print("\nTests interrupted by user.")
        exit_code = 130
    
    finally:
        # Stop services if we started them and user doesn't want to keep them
        if services_started and not args.keep_services:
            stop_test_services()
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
