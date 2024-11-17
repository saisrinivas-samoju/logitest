import os


def cleanup_decorators_in_file(filepath: str, decorator_name: str = 'log_io') -> None:
    """Removes only the decorator and its import that we added

    Args:
        filepath (str): Filepath of the python file to clean up the added decorators and corresponding import statements
        decorator_name (str, optional): name of the decorator to be removed. Defaults to 'log_io'.
    """
    with open(filepath, "r") as file:
        lines = file.readlines()

    # Skip if file is empty
    if not lines:
        return

    res_lines = []
    decorator_import = f"from logitest.decorators import {decorator_name}\n"
    decorator_pattern = f"@{decorator_name}"

    # Process each line
    for line in lines:
        # Skip decorator import line
        if line == decorator_import:
            continue
        # Skip decorator lines
        if line.lstrip().startswith(decorator_pattern):
            continue
        # Keep all other lines unchanged
        res_lines.append(line)

    # Write back to file
    with open(filepath, "w") as file:
        file.writelines(res_lines)


def cleanup_decorators(directory: str, decorator_name: str = 'log_io') -> None:
    """Process all Python files in the directory

    Args:
        directory (str): directory path to remove the decorators and corresponding imports for all the python files
        decorator_name (str, optional): name of the decorator to be removed. Defaults to 'log_io'.
    """
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                cleanup_decorators_in_file(filepath, decorator_name)
