import os

def cleanup_decorators_in_file(filepath: str, decorator_name: str = 'log_io'):
    """Removes only the decorator and its import that we added"""
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

def cleanup_decorators(directory: str):
    """Process all Python files in the directory"""
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                cleanup_decorators_in_file(filepath)