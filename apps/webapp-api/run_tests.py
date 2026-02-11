#!/usr/bin/env python3
"""
Test Runner Script
Comprehensive test runner for the IronHub Template System
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

def run_command(cmd, cwd=None):
    """Run command and return result"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def install_dependencies():
    """Install test dependencies"""
    print("📦 Installing test dependencies...")
    
    dependencies = [
        "pytest>=7.0.0",
        "pytest-cov>=4.0.0",
        "pytest-html>=3.1.0",
        "pytest-mock>=3.10.0",
        "pytest-asyncio>=0.21.0",
        "pytest-xdist>=3.0.0",
        "coverage>=7.0.0",
        "openpyxl>=3.1.0",
        "pandas>=2.0.0",
        "matplotlib>=3.6.0",
        "Pillow>=10.0.0",
        "fastapi>=0.100.0",
        "sqlalchemy>=2.0.0"
    ]
    
    for dep in dependencies:
        success, stdout, stderr = run_command(f"pip install {dep}")
        if not success:
            print(f"❌ Failed to install {dep}: {stderr}")
            return False
    
    print("✅ Dependencies installed successfully")
    return True

def run_unit_tests(verbose=False, coverage=False):
    """Run unit tests"""
    print("\n🧪 Running Unit Tests...")
    
    cmd = ["python", "-m", "pytest"]
    
    # Test files
    test_files = [
        "tests/test_template_service.py",
        "tests/test_pdf_service.py",
        "tests/test_migration_api.py"
    ]
    
    cmd.extend(test_files)
    
    # Options
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend([
            "--cov=src",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-fail-under=80"
        ])
    
    cmd.extend([
        "--html=reports/unit_tests.html",
        "--self-contained-html",
        "-m", "not integration and not api"
    ])
    
    success, stdout, stderr = run_command(" ".join(cmd))
    
    if success:
        print("✅ Unit tests passed")
        return True
    else:
        print("❌ Unit tests failed")
        print(stdout)
        print(stderr)
        return False

def run_integration_tests(verbose=False):
    """Run integration tests"""
    print("\n🔗 Running Integration Tests...")
    
    cmd = ["python", "-m", "pytest"]
    
    # Test files
    test_files = [
        "tests/test_template_service.py::TestTemplateIntegration",
        "tests/test_pdf_service.py::TestPDFServiceIntegration",
        "tests/test_migration_api.py::TestMigrationIntegration"
    ]
    
    cmd.extend(test_files)
    
    # Options
    if verbose:
        cmd.append("-v")
    
    cmd.extend([
        "--html=reports/integration_tests.html",
        "--self-contained-html",
        "-m", "integration"
    ])
    
    success, stdout, stderr = run_command(" ".join(cmd))
    
    if success:
        print("✅ Integration tests passed")
        return True
    else:
        print("❌ Integration tests failed")
        print(stdout)
        print(stderr)
        return False

def run_api_tests(verbose=False):
    """Run API tests"""
    print("\n🌐 Running API Tests...")
    
    cmd = ["python", "-m", "pytest"]
    
    # Test files
    test_files = [
        "tests/test_template_service.py::TestTemplateAPI",
        "tests/test_migration_api.py::TestMigrationAPI"
    ]
    
    cmd.extend(test_files)
    
    # Options
    if verbose:
        cmd.append("-v")
    
    cmd.extend([
        "--html=reports/api_tests.html",
        "--self-contained-html",
        "-m", "api"
    ])
    
    success, stdout, stderr = run_command(" ".join(cmd))
    
    if success:
        print("✅ API tests passed")
        return True
    else:
        print("❌ API tests failed")
        print(stdout)
        print(stderr)
        return False

def run_migration_tests(verbose=False):
    """Run migration-specific tests"""
    print("\n📊 Running Migration Tests...")
    
    cmd = ["python", "-m", "pytest"]
    
    # Test files
    test_files = [
        "tests/test_migration_api.py"
    ]
    
    cmd.extend(test_files)
    
    # Options
    if verbose:
        cmd.append("-v")
    
    cmd.extend([
        "--html=reports/migration_tests.html",
        "--self-contained-html",
        "-k", "migration or ExcelTemplateMigrator"
    ])
    
    success, stdout, stderr = run_command(" ".join(cmd))
    
    if success:
        print("✅ Migration tests passed")
        return True
    else:
        print("❌ Migration tests failed")
        print(stdout)
        print(stderr)
        return False

def run_all_tests(verbose=False, coverage=False):
    """Run all tests"""
    print("\n🚀 Running All Tests...")
    
    # Create reports directory
    Path("reports").mkdir(exist_ok=True)
    
    results = {
        "unit": run_unit_tests(verbose, coverage),
        "integration": run_integration_tests(verbose),
        "api": run_api_tests(verbose),
        "migration": run_migration_tests(verbose)
    }
    
    # Summary
    passed = sum(results.values())
    total = len(results)
    
    print(f"\n📊 Test Summary:")
    print(f"   Total: {total}")
    print(f"   Passed: {passed}")
    print(f"   Failed: {total - passed}")
    
    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("❌ Some tests failed")
        return False

def run_specific_test(test_path, verbose=False):
    """Run specific test file or test"""
    print(f"\n🎯 Running Specific Test: {test_path}")
    
    cmd = ["python", "-m", "pytest", test_path]
    
    if verbose:
        cmd.append("-v")
    
    cmd.extend([
        "--html=reports/specific_test.html",
        "--self-contained-html"
    ])
    
    success, stdout, stderr = run_command(" ".join(cmd))
    
    if success:
        print("✅ Test passed")
        return True
    else:
        print("❌ Test failed")
        print(stdout)
        print(stderr)
        return False

def generate_coverage_report():
    """Generate coverage report"""
    print("\n📈 Generating Coverage Report...")
    
    cmd = [
        "python", "-m", "pytest",
        "--cov=src",
        "--cov-report=html",
        "--cov-report=xml",
        "--cov-report=term",
        "tests/"
    ]
    
    success, stdout, stderr = run_command(" ".join(cmd))
    
    if success:
        print("✅ Coverage report generated")
        print("📄 HTML report: htmlcov/index.html")
        return True
    else:
        print("❌ Coverage report failed")
        print(stderr)
        return False

def lint_code():
    """Run code linting"""
    print("\n🔍 Running Code Linting...")
    
    # Install linting dependencies if not present
    linting_deps = ["flake8", "black", "isort", "mypy"]
    for dep in linting_deps:
        success, _, _ = run_command(f"pip show {dep}")
        if not success:
            print(f"Installing {dep}...")
            run_command(f"pip install {dep}")
    
    # Run flake8
    print("Running flake8...")
    success, stdout, stderr = run_command("flake8 src/ tests/ --max-line-length=100 --ignore=E203,W503")
    if not success:
        print("⚠️ Flake8 issues found:")
        print(stdout)
    
    # Run black check
    print("Running black check...")
    success, stdout, stderr = run_command("black --check src/ tests/")
    if not success:
        print("⚠️ Black formatting issues found:")
        print(stdout)
    
    # Run isort check
    print("Running isort check...")
    success, stdout, stderr = run_command("isort --check-only src/ tests/")
    if not success:
        print("⚠️ Import sorting issues found:")
        print(stdout)
    
    print("✅ Code linting completed")

def check_dependencies():
    """Check if all dependencies are installed"""
    print("\n🔍 Checking Dependencies...")
    
    required_packages = [
        "pytest",
        "fastapi",
        "sqlalchemy",
        "openpyxl",
        "matplotlib",
        "Pillow"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        success, _, _ = run_command(f"pip show {package}")
        if not success:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("Run with --install-deps to install missing dependencies")
        return False
    else:
        print("✅ All dependencies are installed")
        return True

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="IronHub Template System Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests
  python run_tests.py
  
  # Run with coverage
  python run_tests.py --coverage
  
  # Run specific test
  python run_tests.py --specific tests/test_template_service.py
  
  # Run only unit tests
  python run_tests.py --unit
  
  # Install dependencies and run tests
  python run_tests.py --install-deps
  
  # Run with verbose output
  python run_tests.py --verbose
        """
    )
    
    parser.add_argument(
        "--unit", action="store_true",
        help="Run only unit tests"
    )
    
    parser.add_argument(
        "--integration", action="store_true",
        help="Run only integration tests"
    )
    
    parser.add_argument(
        "--api", action="store_true",
        help="Run only API tests"
    )
    
    parser.add_argument(
        "--migration", action="store_true",
        help="Run only migration tests"
    )
    
    parser.add_argument(
        "--specific", type=str,
        help="Run specific test file or test"
    )
    
    parser.add_argument(
        "--coverage", action="store_true",
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "--install-deps", action="store_true",
        help="Install test dependencies"
    )
    
    parser.add_argument(
        "--lint", action="store_true",
        help="Run code linting"
    )
    
    parser.add_argument(
        "--check-deps", action="store_true",
        help="Check if dependencies are installed"
    )
    
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--no-cleanup", action="store_true",
        help="Don't cleanup temporary files"
    )
    
    args = parser.parse_args()
    
    # Print header
    print("🧪 IronHub Template System Test Runner")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Working Directory: {Path.cwd()}")
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    success = True
    
    try:
        # Install dependencies if requested
        if args.install_deps:
            if not install_dependencies():
                success = False
        
        # Check dependencies
        if args.check_deps:
            if not check_dependencies():
                success = False
        
        # Run linting if requested
        if args.lint:
            lint_code()
        
        # Run specific test
        if args.specific:
            if not run_specific_test(args.specific, args.verbose):
                success = False
        
        # Run specific test types
        elif args.unit:
            if not run_unit_tests(args.verbose, args.coverage):
                success = False
        
        elif args.integration:
            if not run_integration_tests(args.verbose):
                success = False
        
        elif args.api:
            if not run_api_tests(args.verbose):
                success = False
        
        elif args.migration:
            if not run_migration_tests(args.verbose):
                success = False
        
        # Run coverage report if requested
        elif args.coverage:
            if not generate_coverage_report():
                success = False
        
        # Run all tests (default)
        else:
            if not run_all_tests(args.verbose, args.coverage):
                success = False
        
        # Print final status
        print("\n" + "=" * 50)
        if success:
            print("🎉 All operations completed successfully!")
            sys.exit(0)
        else:
            print("❌ Some operations failed!")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Test run interrupted by user")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
    
    finally:
        # Cleanup if requested
        if not args.no_cleanup:
            # Cleanup temporary files
            temp_files = [
                ".coverage",
                "coverage.xml",
                ".pytest_cache"
            ]
            
            for temp_file in temp_files:
                try:
                    if Path(temp_file).exists():
                        if Path(temp_file).is_dir():
                            import shutil
                            shutil.rmtree(temp_file)
                        else:
                            Path(temp_file).unlink()
                except:
                    pass

if __name__ == "__main__":
    main()
