import os
import json
from pathlib import Path
from collections.abc import Iterable
import importlib
# import pytest
# from config import ASSERTION_MAPPING

to_pascal_casing = lambda snaking_cased_text: "".join([word.title() for word in snaking_cased_text.split("_")])

to_snake_casing = lambda pascal_cased_text: "".join(["_"+char if i>0 and char.isupper() else char for i, char in enumerate(pascal_cased_text)]).lower()

get_abs_path = lambda path: os.path.normpath(Path(path).absolute())

def make_type_handler_data(data):
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
                raise Exception("""RequiredKeysAreNotPresent: required keys -> ["object", "extension", "load", "dump"]""")
        else:
            raise Exception("InvalidRecord")

def unique_dicts(dicts):
    unique_set = set()
    unique_list = []

    for d in dicts:
        # Serialize the dictionary to a JSON string to make it hashable
        serialized = json.dumps(d, sort_keys=True)
        if serialized not in unique_set:
            unique_set.add(serialized)
            unique_list.append(d)

    return unique_list

def clean_directory(path):
    # Walk through the directory
    for root, dirs, files in os.walk(path, topdown=False):
        # Check for empty directories and delete them
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            if not os.listdir(dir_path):  # Check if the directory is empty
                os.rmdir(dir_path)  # Remove the empty directory
                print(f"Deleted empty directory: {dir_path}")
            else:
                # Check if __init__.py exists in the directory
                if not any(file == '__init__.py' for file in files):
                    # Create an empty __init__.py file
                    init_file_path = os.path.join(dir_path, '__init__.py')
                    with open(init_file_path, 'w') as init_file:
                        pass  # Create an empty file
                    print(f"Added __init__.py to: {dir_path}")

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)
    
def dump_json(python_dict, filepath, indent=4):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(python_dict, f, indent=indent, ensure_ascii=False)
        
def update_dict(dct, k, v):
    if k not in dct:
        dct[k] = [v]
    else:
        dct[k].append(v)
    return dct

def cluster_keys_with_same_values(d):
    dct = {}
    for comp, group_id in d.items():
        dct = update_dict(dct, group_id, comp)
    return dct

def cluster_values_with_same_keys(dict_list):
    res_dict = {}
    kv_list = [(k, v)  if type(v)==list else (k, [v]) for dct in dict_list for k, v in dct.items()]
    for k, v in kv_list:
        if k in res_dict:
            res_dict[k] = res_dict[k] + v
        else:
            res_dict[k] = v
    return res_dict

# def assert_equal(result, expected, visited=None):
#     if visited is None:
#         visited = {}

#     # Ensure both result and expected are of the same type
#     assert type(result) == type(expected), f"Types do not match: {type(result)} != {type(expected)}"

#     # Check if the data type is in the ASSERTION_MAPPING dictionary
#     result_type = type(result).__name__
#     if result_type in ASSERTION_MAPPING:
#         module_name, test_func_name = ASSERTION_MAPPING[result_type]
        
#         # Dynamically import the module using importlib
#         module = importlib.import_module(module_name)
        
#         # Dynamically get the test function and call it
#         test_func = getattr(module, test_func_name)
#         test_func(result, expected)  # Use the testing function from the library
#         return True

#     # Primitive type comparison (int, str, bool, etc.)
#     if isinstance(result, (int, float, bool, str, bytes, complex, type(None))):
#         assert result == expected, f"Values do not match: {result} != {expected}"
#         return True

#     # Handle iterables (list, tuple, set, frozenset, etc.)
#     elif isinstance(result, Iterable) and not isinstance(result, (dict, str)):
#         assert len(result) == len(expected), f"Length mismatch: {len(result)} != {len(expected)}"
        
#         for r, e in zip(result, expected):
#             assert_equal(r, e, visited)
#         return True

#     # Handle dictionaries
#     elif isinstance(result, dict):
#         assert set(result.keys()) == set(expected.keys()), f"Keys do not match: {result.keys()} != {expected.keys()}"

#         for key in result:
#             # Ensure the values for this key are comparable before proceeding
#             if not is_comparable(result[key], expected[key]):
#                 raise ValueError(f"Values for key {key} are not comparable: {result[key]} != {expected[key]}")
#             assert_equal(result[key], expected[key], visited)
#         return True

#     # Handle sets and frozensets
#     elif isinstance(result, (set, frozenset)):
#         assert len(result) == len(expected), f"Set/Frozenset length mismatch: {len(result)} != {len(expected)}"

#         for r, e in zip(result, expected):
#             assert_equal(r, e, visited)
#         return True

#     # Handle custom objects (including NamedTuples)
#     elif hasattr(result, '_fields'):  # NamedTuple
#         assert isinstance(expected, type(result)), f"Types do not match: {type(result)} != {type(expected)}"

#         for field in result._fields:
#             assert_equal(getattr(result, field), getattr(expected, field), visited)
#         return True

#     elif hasattr(result, "__dict__"):  # For custom objects with __dict__
#         assert isinstance(expected, type(result)), f"Types do not match: {type(result)} != {type(expected)}"

#         # Check for circular references to prevent infinite recursion
#         if id(result) in visited and visited[id(result)] == visited.get(id(expected)):
#             return True

#         visited[id(result)] = expected

#         # Compare attributes (including properties) by inspecting the object
#         for attr in dir(result):
#             if not attr.startswith('__'):
#                 assert_equal(getattr(result, attr), getattr(expected, attr), visited)
#         return True

#     # Handle cases for objects with __eq__
#     elif hasattr(result, "__eq__"):
#         assert result == expected, f"Objects do not match: {result} != {expected}"
#         return True

#     # If none of the above, raise an error
#     else:
#         raise ValueError(f"Unsupported type for comparison: {type(result)}")

# def is_comparable(val1, val2):
#     """
#     A helper function to check if two values are comparable.
#     It handles special cases where direct comparison might not be possible.
#     """
#     try:
#         # Check if the types are comparable directly
#         val1 == val2
#         return True
#     except TypeError:
#         # If comparison raises an error, return False
#         return False