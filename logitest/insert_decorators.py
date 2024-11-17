import ast
import os
from typing import List, Tuple
from pathlib import Path
from typing import Optional


def find_class_methods(node: ast.ClassDef) -> List[str]:
    """Find all methods in a class including __init__

    Args:
        node (ast.ClassDef): node object from python syntax tree

    Returns:
        List[str]: List of class method names
    """
    methods = []
    for item in node.body:
        if isinstance(item, ast.FunctionDef):  # Include all methods
            methods.append(item.name)
    return methods


def find_functions_and_classes(tree: ast.AST) -> Tuple[List[str], List[Tuple[str, List[str]]]]:
    """Find both standalone functions and classes with their methods

    Args:
        tree (ast.AST): python syntax tree object

    Returns:
        Tuple[List[str], List[Tuple[str, List[str]]]]: Tuple of functions and classes
    """
    functions = []
    classes = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Check if this is a standalone function (not a method)
            if not isinstance(node.parent, ast.ClassDef):
                functions.append(node.name)
        elif isinstance(node, ast.ClassDef):
            methods = find_class_methods(node)
            if methods:  # Only add class if it has methods
                classes.append((node.name, methods))

    return functions, classes


def insert_decorators_to_file(filepath: str, module_path: str, decorator_name: Optional[str] = 'log_io') -> None:
    """Adds decorators to functions and methods without modifying existing code

    Args:
        filepath (str): python filepath to added decorator to all the functions and methods in it.
        module_path (str): module directory path of the source code folder.
        decorator_name (str, optional): decorator name to be added. Defaults to 'log_io'.
    """
    with open(filepath, "r") as source:
        content = source.read()
        tree = ast.parse(content)

    module_path = Path(module_path).resolve().as_posix()
    import_statement = f"from logitest.decorators import {decorator_name}"
    decorator_text = f"@{decorator_name}(module_path='{module_path}')\n"

    # Check if decorator is already imported
    if import_statement in content:
        return None  # File already processed

    # Add parent information to nodes
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node

    # Find all functions and classes
    functions, classes_and_methods = find_functions_and_classes(tree)

    # Only proceed if there are functions or methods to decorate
    if not (functions or classes_and_methods):
        return

    with open(filepath, "r") as file:
        lines = file.readlines()

    res_lines = []
    current_class = None

    # Add decorator import at the very first line if needed
    if functions or classes_and_methods:
        res_lines.append(import_statement+"\n")

    # Simply copy all lines, adding decorators where needed
    for line in lines:
        # Skip if this is our decorator or any other decorator
        if line.lstrip().startswith('@'):
            res_lines.append(line)
            # Skip adding our decorator if this is our decorator or any other decorator
            if decorator_name in line or not line.lstrip().startswith(f'@{decorator_name}'):
                continue

        # Track class context
        if "class " in line:
            class_name = line.split("class ")[1].split(
                "(")[0].split(":")[0].strip()
            current_class = next(
                (c for c in classes_and_methods if c[0] == class_name), None)

        # Add decorator to class methods
        if current_class and "    def " in line:
            method_name = line.split("def ")[1].split("(")[0].strip()
            if method_name in current_class[1]:
                # Check previous line for any decorator
                prev_line = res_lines[-1].lstrip() if res_lines else ""
                if not (prev_line.startswith('@') and
                        (decorator_name in prev_line or not prev_line.startswith(f'@{decorator_name}'))):
                    indent = len(line) - len(line.lstrip())
                    res_lines.append(" " * indent + decorator_text)

        # Add decorator to standalone functions
        elif "def " in line and not line.startswith(" "):
            func_name = line.split("def ")[1].split("(")[0].strip()
            if func_name in functions:
                # Check previous line for any decorator
                prev_line = res_lines[-1].lstrip() if res_lines else ""
                if not (prev_line.startswith('@') and
                        (decorator_name in prev_line or not prev_line.startswith(f'@{decorator_name}'))):
                    res_lines.append(decorator_text)

        # Add the original line unchanged
        res_lines.append(line)

    # Write back to file
    with open(filepath, "w") as file:
        file.writelines(res_lines)


def insert_decorators(directory: str, decorator_name='log_io'):
    """Process all Python files in the directory

    Args:
        directory (str): directory path in which all the python files will be scanned and the given decorator will be added.
        decorator_name (str, optional): decorator name to be added. Defaults to 'log_io'.
    """
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                insert_decorators_to_file(
                    filepath, directory, decorator_name=decorator_name)
