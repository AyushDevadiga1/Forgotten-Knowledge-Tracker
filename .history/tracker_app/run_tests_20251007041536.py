# run_tests.py
import sys
import subprocess

def run_tests():
    """
    Run all pytest tests with coverage and generate reports.
    """
    print("🔹 Running pytest with coverage...")

    # Command to run pytest with coverage
    cmd = [
        sys.executable, "-m", "pytest",
        "--cov=core",              # measure coverage for core modules
        "--cov-report=term",       # show coverage in terminal
        "--cov-report=html:htmlcov", # generate HTML report in htmlcov/
        "-v",                      # verbose
        "--maxfail=2",             # stop after 2 failures
        "--disable-warnings",
        "tests"
    ]

    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\n✅ All tests passed successfully!")
    else:
        print("\n❌ Some tests failed. Check details above.")

    print("\n📂 Coverage HTML report generated at: htmlcov/index.html")

    # Exit with the pytest return code (important for CI/IEEE pipelines)
    sys.exit(result.returncode)

if __name__ == "__main__":
    run_tests()
