import os
import sys
from pathlib import Path
import subprocess

from logitest.helper import clean_directory, make_type_handler_data
from logitest.insert_decorators import insert_decorators, insert_decorators_to_file
from logitest.create_conftest import create_conftest
from logitest.generate_tests import generate_tests, get_path_dict
from logitest.cleanup_decorators import cleanup_decorators
from logitest.del_pycache import del_pycache

# def create_conftest(parent_dir: Path) -> None:
#     """
#     Create conftest.py if it doesn't exist in the parent directory.
    
#     Args:
#         parent_dir (Path): Directory where conftest.py should be created
#     """
#     conftest_path = parent_dir / 'conftest.py'
    
#     # Only create if it doesn't exist
#     if not conftest_path.exists():
#         conftest_content = '''import os
# import sys

# # Add the parent directory to Python path
# sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
# '''
#         with open(conftest_path, 'w') as f:
#             f.write(conftest_content)
#         print(f"Created conftest.py at {conftest_path}")

def create_test_cases(module_dirpath, main_filepath=None):
    
    # Convert to absolute path and normalize
    module_dirpath = Path(os.path.normpath(Path(module_dirpath).absolute()))
    parent_dir = module_dirpath.parent
    
    path_dict = get_path_dict(module_dirpath)
    
    # Change working directory to parent directory
    original_dir = os.getcwd()
    os.chdir(parent_dir)
    
    # Create conftest.py if needed
    create_conftest(parent_dir)
    
    # Add parent_dir to PYTHONPATH
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    
    try:
        # Original test generation logic
        insert_decorators(module_dirpath)
        if main_filepath is not None:
            main_filepath = parent_dir / 'main.py'
            insert_decorators_to_file(main_filepath.as_posix(), module_path=module_dirpath)
        
        del_pycache(parent_dir)
        
        # os.system(f"python -m {main_filepath}")
        os.system(f"python main.py")
        generate_tests(module_dirpath)
        cleanup_decorators(module_dirpath)
        
        clean_directory(path_dict['logs_dirpath'])
        clean_directory(path_dict['test_dirpath'])
        
        # Run pytest with coverage
        print("\nRunning tests with coverage...\n")
        pytest_cmd = ["pytest", "--cov=.", "--cov-report=term-missing"]
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{parent_dir}{os.pathsep}{env.get('PYTHONPATH', '')}"
        result = subprocess.run(pytest_cmd, capture_output=True, text=True, env=env)
        
        # Print test results
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
        
        del_pycache(module_dirpath.parent)
        return result.returncode
        
    finally:
        # Restore original working directory
        os.chdir(original_dir)

def create_test_cases_cli():
    """
    CLI entry point for LogiTest.
    Usage: logitest <module_dirpath>
    """
    if len(sys.argv) < 2:
        print("Usage: logitest <module_dirpath>")
        sys.exit(1)
    
    module_dirpath = sys.argv[1]
    exit_code = create_test_cases(module_dirpath)
    sys.exit(exit_code)
