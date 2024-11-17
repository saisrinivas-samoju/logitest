from pathlib import Path


def create_conftest(parent_dir: Path) -> None:
    """
    Create conftest.py if it doesn't exist in the parent directory.

    Args:
        parent_dir (Path): Directory where conftest.py should be created
    """
    conftest_path = parent_dir / 'conftest.py'

    # Only create if it doesn't exist
    if not conftest_path.exists():
        conftest_content = '''import os
import sys

# Add the parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
'''
        with open(conftest_path, 'w') as f:
            f.write(conftest_content)
        print(f"Created conftest.py at {conftest_path}")


if __name__ == "__main__":
    create_conftest(Path("."))
