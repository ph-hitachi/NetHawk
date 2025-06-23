import re
from pathlib import Path

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def humanize(name: str) -> str:
    """Convert snake_case to Title Case."""
    return re.sub(r"_", " ", name).capitalize()

def pytest_itemcollected(item):
    # Extract file name (like test_dispatcher.py → Dispatcher)
    file_name = Path(item.fspath).stem  # test_dispatcher
    component = file_name.replace("test_", "").capitalize()

    # Extract function name and convert to readable
    func_name = item.originalname or item.name
    description = humanize(func_name)

    # Final formatted test ID
    item._nodeid = f"[{humanize(component)}]: {description}"
                
def pytest_terminal_summary(terminalreporter):
    passed = len(terminalreporter.stats.get("passed", []))
    failed = len(terminalreporter.stats.get("failed", []))
    skipped = len(terminalreporter.stats.get("skipped", []))

    terminalreporter.write_sep("=", "Test Summary")
    terminalreporter.write_line(f"{GREEN}[PASS]{RESET}   Passed:  {passed}")
    terminalreporter.write_line(f"{RED}[FAIL]{RESET}   Failed:  {failed}")
    terminalreporter.write_line(f"{YELLOW}[SKIP]{RESET}   Skipped: {skipped}")
