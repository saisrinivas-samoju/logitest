import os
import sys
from pathlib import Path
import subprocess
from typing import Any, Union, Optional
from logitest.helper import clean_directory, separate_contents_with_ast
from logitest.insert_decorators import insert_decorators, insert_decorators_to_file
from logitest.create_conftest import create_conftest
from logitest.generate_tests import generate_tests, get_path_dict
from logitest.cleanup_decorators import cleanup_decorators
from logitest.del_pycache import del_pycache


def get_dtype(obj: Any) -> str:
    """Get the data type name of any object

    Args:
        obj (Any): any python object

    Returns:
        str: data type of the object
    """
    return str(type(obj).__module__) + '.' + type(obj).__name__


def add_to_config(type_handling_str: str = "", assertion_mapping_str: str = "") -> str:
    """Add custom code to config file to run the test cases with custom I/O objects

    Args:
        type_handling_str (str, optional): custom type handlers code in string format. Defaults to "".
        assertion_mapping_str (str, optional): custom assertion code in string format. Defaults to "".

    Returns:
        str: Message
    """
    if type_handling_str:
        type_handling_str = type_handling_str + \
            "\n\ntype_handlers = type_handlers | new_type_handlers"

    if assertion_mapping_str:
        assertion_mapping_str = assertion_mapping_str + \
            "\n\nASSERTION_MAPPING = ASSERTION_MAPPING | new_assertion_mapping"

    with open("logitest/config.py", 'r') as f:
        existing_txt = f.read()

    full_config_text = "\n".join(
        [existing_txt, type_handling_str, assertion_mapping_str])

    new_config = separate_contents_with_ast(full_config_text)

    new_config_text = "\n\n\n".join(filter(None, ["\n".join(new_config.get('imports', [])), "\n\n".join(new_config.get(
        'functions', [])), "\n\n".join(new_config.get('lambdas', [])), "\n\n".join(new_config.get('variable_assignments', []))]))

    with open("logitest/config.py", 'w') as f:
        f.write(new_config_text)

    return "Added custom code to config"


def create_test_cases(module_dirpath: Union[Path, str], main_filepath: Optional[Union[Path, str]] = None):
    """Create test cases for code in the given module with all the inputs and outputs that go through each function/method in the pipeline while running main.py at the given location.
    Also, test the code generated test cases and get the coverage information

    Args:
        module_dirpath (Union[Path, str]): relative or absolute directory path of the module which contains the source code.
        main_filepath (Optional[Union[Path, str]], optional): relative or absolute filepath of the main.py that runs the code in the give module directory path. Defaults to None.
    """

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
            insert_decorators_to_file(
                main_filepath.as_posix(), module_path=module_dirpath)

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
        result = subprocess.run(
            pytest_cmd, capture_output=True, text=True, env=env)

        # Print test results
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)

        del_pycache(module_dirpath.parent)
        return result.returncode

    finally:
        # Restore original working directory
        os.chdir(original_dir)


def create_test_cases_cli() -> None:
    """
    CLI entry point for LogiTest.
    Usage: logitest <module_dirpath> [<main_filepath>]
    """

    if len(sys.argv) < 2:
        print("Usage: logitest <module_dirpath> [<main_filepath>]")
        sys.exit(1)

    module_dirpath = sys.argv[1]
    main_filepath = sys.argv[2] if len(sys.argv) > 2 else None
    exit_code = create_test_cases(module_dirpath, main_filepath)
    sys.exit(exit_code)
