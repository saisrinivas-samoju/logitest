import os
import json
from pathlib import Path
import ast
from typing import Union, List, Optional


def to_pascal_casing(snaking_cased_text: str) -> str:
    """Convert the given string from snaking casing to pascal casing

    Args:
        snaking_cased_text (str): snake cased text

    Returns:
        str: pascal cased text
    """
    return "".join([word.title() for word in snaking_cased_text.split("_")])


def to_snake_casing(pascal_cased_text: str) -> str:
    """Convert the given string from pascal casing to snake casing

    Args:
        pascal_cased_text (str): pascal cased text

    Returns:
        str: snaked cased text
    """
    return "".join(["_"+char if i > 0 and char.isupper() else char for i, char in enumerate(pascal_cased_text)]).lower()


def get_abs_path(path: str) -> str:
    """Get absolute path for the given relative path

    Args:
        path (str): file / directory path

    Returns:
        str: absolute path
    """
    return os.path.normpath(Path(path).absolute())


def make_type_handler_data(data: Union[dict, list]) -> Union[dict, list]:
    """Convert the custom type_handler data with a given sample object to match the existing type handlers in the config.py

    Args:
        data (Union[dict, list]): new type handler dictionary or list of dictionaries.

    Raises:
        Exception: When the required keys are not present
        Exception: When the data type passed is not a list of a dict

    Returns:
        Union[dict, list]: formatted type handler dictionary
    """
    try:
        json.dumps(data)
        return data
    except:
        if isinstance(data, list):
            return [make_type_handler_data(val) for val in data]
        elif isinstance(data, dict):
            if all([k in data for k in ["object", "extension", "load", "dump"]]):
                obj = data['object']
                obj_type = str(type(obj).__module__) + '.' + type(obj).__name__
                return {
                    obj_type: {
                        "extension": data['extension'],
                        "load": data['load'],
                        "dump": data['dump']
                    }
                }
            else:
                raise Exception(
                    """RequiredKeysAreNotPresent: required keys -> ["object", "extension", "load", "dump"]""")
        else:
            raise Exception("InvalidRecord")


def separate_contents_with_ast(input_string: str) -> dict:
    """separate imports, variable assignments, functions and lambda functions in the given code.

    Args:
        input_string (str): code in string format

    Returns:
        dict: dictionary with separated code
    """
    tree = ast.parse(input_string)

    imports = []
    functions = []
    lambdas = []
    variable_assignments = []

    class CodeAnalyzer(ast.NodeVisitor):
        def visit_Import(self, node):
            for alias in node.names:
                if alias.asname:
                    imports.append(f"import {alias.name} as {alias.asname}")
                else:
                    imports.append(f"import {alias.name}")

        def visit_ImportFrom(self, node):
            module = node.module if node.module else ''
            for alias in node.names:
                if alias.asname:
                    imports.append(
                        f"from {module} import {alias.name} as {alias.asname}")
                else:
                    imports.append(f"from {module} import {alias.name}")

        def visit_FunctionDef(self, node):
            func_code = f"def {node.name}({', '.join(arg.arg for arg in node.args.args)}):"
            body_lines = ast.get_source_segment(
                input_string, node).split("\n")[1:]
            functions.append(func_code + "\n" + "\n".join(body_lines))

        def visit_Assign(self, node):
            targets = [ast.get_source_segment(
                input_string, target) for target in node.targets]
            value = ast.get_source_segment(input_string, node.value)
            assignment = f"{' = '.join(targets)} = {value}"
            if isinstance(node.value, ast.Lambda):
                lambdas.append(assignment)
            else:
                variable_assignments.append(assignment)

    analyzer = CodeAnalyzer()
    analyzer.visit(tree)

    return {
        "imports": imports,
        "functions": functions,
        "lambdas": lambdas,
        "variable_assignments": variable_assignments
    }


def merge_dicts(*dicts: dict) -> dict:
    """Merge dictionary values with same keys

    Returns:
        dict: python dictionary with values in list format
    """
    merged_dict = {}

    for d in dicts:
        for key, value in d.items():
            if key in merged_dict:
                # Merge values, ensuring uniqueness and handling lists
                merged_dict[key] = list(
                    dict.fromkeys(merged_dict[key] + value))
            else:
                merged_dict[key] = value.copy() if isinstance(
                    value, list) else [value]

    return merged_dict


def unique_dicts(dicts: List[dict]) -> List[dict]:
    """Get the unique list of dictionaries

    Args:
        dicts (List[dict]): List of dictionaries

    Returns:
        List[dict]: List of unique dictionaries
    """
    unique_set = set()
    unique_list = []

    for d in dicts:
        # Serialize the dictionary to a JSON string to make it hashable
        serialized = json.dumps(d, sort_keys=True)
        if serialized not in unique_set:
            unique_set.add(serialized)
            unique_list.append(d)

    return unique_list


def clean_directory(path: Union[Path, str]) -> None:
    """Remove empty folder in the given directory path and add __init__.py in any directory with files.

    Args:
        path (Union[Path, str]): Directory path
    """
    # Walk through the directory
    for root, dirs, files in os.walk(path, topdown=False):
        # Check for empty directories and delete them
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            if not os.listdir(dir_path):  # Check if the directory is empty
                os.rmdir(dir_path)  # Remove the empty directory
                # print(f"Deleted empty directory: {dir_path}")
            else:
                # Check if __init__.py exists in the directory
                if not any(file == '__init__.py' for file in files):
                    # Create an empty __init__.py file
                    init_file_path = os.path.join(dir_path, '__init__.py')
                    with open(init_file_path, 'w') as init_file:
                        pass  # Create an empty file
                    # print(f"Added __init__.py to: {dir_path}")


def load_json(filepath: Union[Path, str]) -> Optional[dict]:
    """Load the JSON file at the given filepath

    Args:
        filepath (Union[str, Path]): filepath of the JSON file

    Returns:
        Union[list, dict]: content in the JSON file
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def dump_json(python_dict: Union[dict, list], filepath: str, indent: int = 4):
    """Dump the JSON Content at the given filepath

    Args:
        obj (Any): Object to be dumped as JSON
        filepath (Union[str, Path]): filepath of the JSON file
        indent (int, optional): number of spaces to be present in the JSON file indentation. Defaults to 4.
    """
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(python_dict, f, indent=indent, ensure_ascii=False)

def update_dict(dct: dict, k, v) -> dict:
    """Update key-value mapping in the given dictionary

    Args:
        dct (dict): dictionary to be updated
        k (_type_): key to be updated
        v (_type_): value to be updated

    Returns:
        dict: updated dictionary
    """
    if k not in dct:
        dct[k] = [v]
    else:
        dct[k].append(v)
    return dct


def cluster_keys_with_same_values(d: dict) -> dict:
    """Cluster keys with same values. Create a mapping dictionary with list of keys as values for the values that are repeating.

    Args:
        d (dict): initial dictionary where some values are repeating.

    Returns:
        dict: value mapping to the list of keys.
    """
    dct = {}
    for comp, group_id in d.items():
        dct = update_dict(dct, group_id, comp)
    return dct


def cluster_values_with_same_keys(dict_list: List[dict]) -> dict:
    """Cluster values with same keys.
    When mulitple dictionaries are having same keys with different values, combine them and make the union of the values for the given keys.

    Args:
        dict_list (List[dict]): list of dictionaries

    Returns:
        dict: combined dictionary
    """    
    res_dict = {}
    kv_list = [(k, v) if type(v) == list else (k, [v])
               for dct in dict_list for k, v in dct.items()]
    for k, v in kv_list:
        if k in res_dict:
            res_dict[k] = res_dict[k] + v
        else:
            res_dict[k] = v
    return res_dict
