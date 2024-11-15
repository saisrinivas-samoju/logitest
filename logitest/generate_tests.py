import os
import shutil
from pathlib import Path
from collections.abc import Sequence, Mapping
# from logitest.helper import load_json, cluster_keys_with_same_values, to_snake_casing, to_pascal_casing, get_abs_path

from logitest.helper import load_json, cluster_keys_with_same_values, to_snake_casing, to_pascal_casing, unique_dicts
from logitest.data_handler import DataHandler
# from config import MODULE_DIRPATH #, TEST_DATA_DIR

# LOG_DATA_DIR = Path("io_logs/data")
# TEST_DATA_DIR = Path('tests/data')
# TEST_DATA_DIR.parent.mkdir(parents=True, exist_ok=True)

def get_path_dict(module_dirpath):
    if not isinstance(module_dirpath, Path):
        module_dirpath = Path(module_dirpath).absolute()
    logs_dirpath = module_dirpath.parent / "io_logs"
    test_dirpath = module_dirpath.parent / "tests"
    log_data_dirpath = logs_dirpath / "data"
    test_data_dirpath = test_dirpath / "data"
    return {"module_dirpath": module_dirpath, "logs_dirpath": logs_dirpath, "test_dirpath": test_dirpath, "log_data_dirpath": log_data_dirpath, "test_data_dirpath": test_data_dirpath}

def _update_to_test_data_filepath(filepath, module_dirpath):
    path_dict = get_path_dict(module_dirpath)
    test_data_dirpath = path_dict['test_data_dirpath']
    log_data_dirpath = path_dict['log_data_dirpath']
    orig_path = Path(filepath).absolute()
    relative_path = orig_path.relative_to(log_data_dirpath)
    new_path = test_data_dirpath / relative_path
    return new_path

def update_to_test_data_filepath(io_val, module_dirpath):
    if isinstance(io_val, dict):
        for key, val in io_val.items():
            if key=='filepath':
                io_val[key] = _update_to_test_data_filepath(val, module_dirpath)
            else:
                update_to_test_data_filepath(val, module_dirpath)
    elif isinstance(io_val, list):
        for item in io_val:
            update_to_test_data_filepath(item, module_dirpath)
    return io_val

# def process_input_kwargs(value, module_dirpath):
#     path_dict = get_path_dict(module_dirpath)
#     test_data_dirpath = path_dict['test_data_dirpath']
#     log_data_dirpath = path_dict['log_data_dirpath']
#     if isinstance(value, dict):
#         if 'filepath_to_load' in value:
#             if len(value)==1:
#                 # Get relative path from log_data_dirpath
#                 orig_path = Path(value['filepath_to_load']).absolute()
#                 relative_path = orig_path.relative_to(log_data_dirpath)
#                 # Apply that relative path to test_data_dirpath
#                 new_path = test_data_dirpath / relative_path
#                 return f"load(r\'{new_path}\')"
#     return value

# def process_output(output_dict, module_dirpath):
#     path_dict = get_path_dict(module_dirpath)
#     test_data_dirpath = path_dict['test_data_dirpath']
#     log_data_dirpath = path_dict['log_data_dirpath']
#     if output_dict is not None:
#         if "filepath" in output_dict:
#             # Get relative path from log_data_dirpath
#             orig_path = Path(output_dict['filepath']).absolute()
#             relative_path = orig_path.relative_to(log_data_dirpath)
#             # Apply that relative path to test_data_dirpath
#             new_path = test_data_dirpath / relative_path
#             return f"load(r\'{new_path}\')"
#         else:
#             return output_dict['value']
#     return None

# def process_output(output_dict, module_dirpath):
#     path_dict = get_path_dict(module_dirpath)
#     test_data_dirpath = path_dict['test_data_dirpath']
#     log_data_dirpath = path_dict['log_data_dirpath']
#     if output_dict is not None:
#         if "file_path" in output_dict:
#                 filepath = os.path.normpath(output_dict['file_path'])
#                 filepath = test_data_dirpath / Path(filepath).relative_to(log_data_dirpath)
#                 filepath = get_abs_path(filepath)
#                 return f"load(r\'{filepath}\')"
#                 # return f"load(get_abs_path(r\'{filepath}\'))"
                
#         else:
#             return output_dict['value']
#     return None

def generate_function_tests(function_case_list, module_dirpath):
    path_dict = get_path_dict(module_dirpath=module_dirpath)
    data_handler = DataHandler(log_dir=path_dict['logs_dirpath'], data_dir=path_dict['log_data_dirpath'])
    imports = ['import pytest', 'import os', 'from logitest.assertion import assert_equal', 'from logitest.data_handler import DataHandler']
    input_fixtures = []
    output_fixtures = []
    io_pair_list = []
    
    global_variables = ['data_handler = DataHandler()']
    
    test_function_str = """@pytest.mark.parametrize(('input_fixture, expected_fixture'), [{io_pair_str}])
def test_{function_name}(input_fixture, expected_fixture, request):
    input_kwargs = request.getfixturevalue(input_fixture)
    expected_result = request.getfixturevalue(expected_fixture)
    result = {function_name}(**input_kwargs)
    assert assert_equal(result, expected_result)"""
    
    function_imports = set()
    
    function_name_set = set()
    
    function_case_list = unique_dicts(function_case_list) # Added
    
    for test_set in function_case_list:
        function_name = test_set['function_name']
        function_name_set.add(function_name)
        module_name = test_set['module_name']
        function_import = f'from {module_name} import {function_name}'
        function_imports.add(function_import)
        
        set_number = test_set['set_number']
        input_kwargs = test_set.get('input', {}).get('mapped_kwargs', {})
        output = test_set['output']
        # processed_input_kwargs = {k: process_input_kwargs(v, module_dirpath) for k, v in input_kwargs.items()}
        # processed_output = process_output(output, module_dirpath)
        preprocessed_input_kwargs = {k: update_to_test_data_filepath(v, module_dirpath) for k, v in input_kwargs.items()}
        preprocessed_output = update_to_test_data_filepath(output, module_dirpath)
        
        processed_input_kwargs = {k: data_handler.make_arg_recipe(v) for k, v in preprocessed_input_kwargs.items()}
        processed_output = data_handler.make_arg_recipe(preprocessed_output)
        
        input_fixture = f"{function_name}_input_set_{set_number}"
        expected_fixture = f"{function_name}_output_set_{set_number}"
        
        processed_input_str = "{" + ", ".join([f"'{k}': {v}" for k, v in processed_input_kwargs.items()]) + "}"
        
        # input_fixtures.append(f"@pytest.fixture\ndef {input_fixture}():\n    return {processed_input_kwargs}")
        input_fixtures.append(f"@pytest.fixture\ndef {input_fixture}():\n    return {processed_input_str}")
        output_fixtures.append(f"@pytest.fixture\ndef {expected_fixture}():\n    return {processed_output}")
        
        io_pair_list.append(f"('{input_fixture}', '{expected_fixture}')")
        # io_pair_list.append(f"('pytest.lazy_fixture({input_fixture})', 'pytest.lazy_fixture({expected_fixture})')")
        
    imports.extend(list(function_imports))
    
    imports = list(dict.fromkeys(imports))
    
    # io_pair_str = f'[{", ".join(io_pair_list)}]'
    io_pair_str = ", ".join(io_pair_list)
    
    if len(function_name_set) == 0:
        raise Exception("NoFunctionsIdentified")
    elif len(function_name_set)>1:
        raise Exception("MoreThanOneFunctionIdentified")
    else:
        function_name = list(function_name_set)[0]
        
    test_function_str = test_function_str.format(io_pair_str=io_pair_str, function_name=function_name)
    
    # import_str = "\n".join(imports)
    # input_fixtures_str = "\n\n".join(input_fixtures)
    # output_fixtures_str = "\n\n".join(output_fixtures)
    # full_code = "\n\n".join([import_str, input_fixtures_str, output_fixtures_str, test_function_str])
    
    full_code = get_full_test_file_code(input_fixtures, output_fixtures, test_function_str, imports, global_variables)
    return {
        "function_name": function_name,
        "imports": imports,
        "input_fixtures": input_fixtures,
        "output_fixtures": output_fixtures,
        "test_function": test_function_str,
        "full_code": full_code
    }
    
def get_full_test_file_code(input_fixtures, output_fixtures, test_function_str, imports=[], global_variables=[]):
    import_str = "\n".join(imports)
    global_var_str = "\n".join(global_variables)
    input_fixtures_str = "\n\n".join(input_fixtures)
    output_fixtures_str = "\n\n".join(output_fixtures)
    full_code = "\n\n".join(filter(None, [import_str, global_var_str, input_fixtures_str, output_fixtures_str, test_function_str]))
    return full_code

def classify_filepath(filepath):
    if not isinstance(filepath, Path):
        filepath = Path(filepath)
    filename = filepath.stem
    if len(filename.split("_")) == 2:
        return "standalone_function" # function
    elif len(filename.split("_")) == 3:
        return filename.split("_")[0] # class name
    else:
        raise Exception("IssueWithTheFilename: {filepath}")

def get_cluster_filepath_dict(dirpath):
    if not isinstance(dirpath, Path):
        dirpath = Path(dirpath)
    filepath_gen = dirpath.glob("*.json")
    filepath_dict = {str(filepath): classify_filepath(filepath) for filepath in filepath_gen}
    cluster_filepath_dict = cluster_keys_with_same_values(filepath_dict)
    return cluster_filepath_dict

def combine_class_test_cases(class_filepath_list):
    class_test_case_list = []
    for filepath in class_filepath_list:
        json_data = load_json(filepath)
        class_test_case_list.extend(json_data)
    return class_test_case_list

def cluster_class_test_cases_with_instances(class_test_case_list):
    instance_class_test_case_dict = {}
    for test_case in class_test_case_list:
        instance_id = test_case['instance_id']
        if instance_id in instance_class_test_case_dict:
            instance_class_test_case_dict[instance_id] = instance_class_test_case_dict[instance_id] + [test_case]
        else:
            instance_class_test_case_dict[instance_id] = [test_case]
    instance_id_mapping_dict = {inst_id: i for i, inst_id in enumerate(instance_class_test_case_dict, 1)}
    instance_class_test_case_dict = {instance_id_mapping_dict[k]: v for k, v in instance_class_test_case_dict.items()}
    return instance_class_test_case_dict

def cluster_method_test_cases(instance_class_test_case_list):
    method_test_case_dict = {}
    for test_case in instance_class_test_case_list:
        if not test_case['is_method']:
            raise Exception("NotAMethod")
        method = test_case['function_name']
        if method in method_test_case_dict:
            method_test_case_dict[method] = method_test_case_dict[method] + [test_case]
        else:
            method_test_case_dict[method] = [test_case]
    if "__init__" in method_test_case_dict:
        num_init_methods = len(method_test_case_dict['__init__'])
        if num_init_methods > 1:
            raise Exception("MultipleInitMethods")
    else:
        method_test_case_dict["__init__"] = [{}]
    return method_test_case_dict

def generate_class_instance_tests(module_dirpath, instance_class_test_case_list, class_name, instance_id=None):
    path_dict = get_path_dict(module_dirpath=module_dirpath)
    data_handler = DataHandler(log_dir=path_dict['logs_dirpath'], data_dir=path_dict['log_data_dirpath'])
    imports = ['import pytest', 'import os', 'from joblib import load', 'from logitest.assertion import assert_equal', 'from logitest.data_handler import DataHandler']
    
    global_variables = ['data_handler = DataHandler()']
    
    method_test_case_dict = cluster_method_test_cases(instance_class_test_case_list)
    init_method_data = method_test_case_dict["__init__"][0]
    instance_str = f"_instance_{instance_id}" if instance_id is not None else ""
    class_instance = to_snake_casing(class_name) + instance_str
    
    init_method_kwargs = init_method_data.get('input', {}).get('mapped_kwargs', "")
    init_method_kwargs = {key: data_handler.make_arg_recipe(update_to_test_data_filepath(val, module_dirpath)) for key, val in init_method_kwargs.items()}
    # init_method_code = f"""@pytest.fixture\ndef {fixture_name}():\n\tdef create_instance():\n\t\treturn {class_name}(**{init_method_kwargs})\n\treturn create_instance"""
    init_method_code = f"""@pytest.fixture(scope='class')\ndef {class_instance}():\n\treturn {class_name}(**{init_method_kwargs})"""
    
    method_str_template = """@pytest.mark.parametrize(('input_fixture', 'expected_fixture'), [{io_pair_str}])
def test_{method_name}{instance_str}(input_fixture, expected_fixture, request, {class_instance}):
    input_kwargs = request.getfixturevalue(input_fixture)
    expected_result = request.getfixturevalue(expected_fixture)
    result = {class_instance}.{method_name}(**input_kwargs)
    assert assert_equal(result, expected_result)"""
    
    method_imports = set()
    
    method_res_dict = {}
    
    for method_name, method_test_case_list in method_test_case_dict.items():
        curr_imports = []
        io_pair_list = []
        input_fixtures = []
        output_fixtures = []
        if method_name == "__init__":
            continue
        
        method_test_case_list = unique_dicts(method_test_case_list) # Added
        
        for test_set in method_test_case_list:
            module_name = test_set['module_name']
            function_import = f'from {module_name} import {class_name}'
            method_imports.add(function_import)
            
            set_number = instance_id
            input_kwargs = test_set.get('input', {}).get('mapped_kwargs', {})
            output = test_set['output']
            # processed_input_kwargs = {k: process_input_kwargs(v, module_dirpath) for k, v in input_kwargs.items()}
            # processed_output = process_output(output, module_dirpath)
            
            preprocessed_input_kwargs = {k: update_to_test_data_filepath(v, module_dirpath) for k, v in input_kwargs.items()}
            preprocessed_output = update_to_test_data_filepath(output, module_dirpath)
            
            processed_input_kwargs = {k: data_handler.make_arg_recipe(v) for k, v in preprocessed_input_kwargs.items()}
            processed_output = data_handler.make_arg_recipe(preprocessed_output)
            
            input_fixture = f"{method_name}_input_set_{set_number}"
            expected_fixture = f"{method_name}_output_set_{set_number}"
            processed_input_str = "{" + ", ".join([f"'{k}': {v}" for k, v in processed_input_kwargs.items()]) + "}"
            
            
            input_fixtures.append(f"@pytest.fixture\ndef {input_fixture}():\n    return {processed_input_str}")
            # input_fixtures.append(f"@pytest.fixture\ndef {input_fixture}():\n    return {processed_input_kwargs}")
            output_fixtures.append(f"@pytest.fixture\ndef {expected_fixture}():\n    return {processed_output}")
            
            # io_pair_list.append(f"(pytest.lazy_fixture({input_fixture}), pytest.lazy_fixture({expected_fixture}))")
            io_pair_list.append(f"('{input_fixture}', '{expected_fixture}')")
            # io_pair_list.append(f"(pytest.lazy_fixture('{input_fixture}'), pytest.lazy_fixture('{expected_fixture}'))")
            
        curr_imports.extend(list(method_imports))
        curr_imports = list(dict.fromkeys(curr_imports))
        imports.extend(curr_imports)
        imports = list(dict.fromkeys(imports))
        
        # io_pair_str = f'[{", ".join(io_pair_list)}]'
        io_pair_str = ", ".join(io_pair_list)
        
        curr_method_str = method_str_template.format(method_name=method_name, class_instance=class_instance, io_pair_str=io_pair_str, instance_str=instance_str)
        
        curr_full_code = get_full_test_file_code(input_fixtures, output_fixtures, curr_method_str, imports=[], global_variables=[])
        
        method_res_dict[method_name] = {
            "imports": curr_imports,
            "input_fixtures": input_fixtures,
            "output_fixtures": output_fixtures,
            "test_method": curr_method_str,
            "full_code": curr_full_code
        }
        
    res_dict = {'imports': imports, "instance_fixture": init_method_code}

    input_fixtures = []
    output_fixtures = []
    test_method_list = []
    test_method_dict = {}
    code_list = []
    for method, method_test_code_dict in method_res_dict.items():
        curr_input_fixtures = method_test_code_dict['input_fixtures']
        curr_input_fixtures = list(dict.fromkeys(curr_input_fixtures))
        input_fixtures.extend(curr_input_fixtures)
        
        curr_output_fixtures = method_test_code_dict['output_fixtures']
        curr_output_fixtures = list(dict.fromkeys(curr_output_fixtures))
        output_fixtures.extend(curr_output_fixtures)
        
        curr_test_method_list = method_test_code_dict['test_method']
        curr_test_method_list = list(dict.fromkeys(curr_test_method_list))
        test_method_list.extend(curr_test_method_list)
        
        test_method_dict[method] = curr_test_method_list
        
        curr_code_list = method_test_code_dict["full_code"]
        code_list.append(curr_code_list)
    
    full_code_list = imports + list(dict.fromkeys(global_variables)) + code_list
    full_code = "\n\n".join(full_code_list)
    
    res_dict['input_fixtures'] = input_fixtures
    res_dict['output_fixtures'] = output_fixtures
    res_dict['test_method_list'] = test_method_list
    res_dict['test_method_dict'] = test_method_dict
    res_dict['code_list'] = code_list
    res_dict['full_code'] = full_code
    res_dict['global_variables'] = global_variables # newly added
    
    return res_dict


def generate_class_tests(module_dirpath, class_test_case_list, class_name):
    instance_class_test_case_dict = cluster_class_test_cases_with_instances(class_test_case_list)
    if len(instance_class_test_case_dict)==1:
        instance_class_test_case_dict = {inst_id: generate_class_instance_tests(module_dirpath, instance_class_test_case_list, class_name, None) for inst_id, instance_class_test_case_list in instance_class_test_case_dict.items()}
    else:
        instance_class_test_case_dict = {inst_id: generate_class_instance_tests(module_dirpath, instance_class_test_case_list, class_name, inst_id) for inst_id, instance_class_test_case_list in instance_class_test_case_dict.items()}
    return instance_class_test_case_dict

# def generate_class_test_code_from_filepath_list(module_dirpath, class_filepath_list, class_name):
#     class_test_case_list = combine_class_test_cases(class_filepath_list)
#     instance_class_test_case_dict = generate_class_tests(module_dirpath, class_test_case_list, class_name)
#     imports = []
#     code_list = []
#     instance_fixture_list = []
#     for inst_id, class_test_dict in instance_class_test_case_dict.items():
#         instance_fixture = class_test_dict['instance_fixture']
#         instance_fixture_list.append(instance_fixture)
#         imports.extend(class_test_dict['imports'])
#         code_list.extend(class_test_dict['code_list'])
#     imports = list(dict.fromkeys(imports))
#     import_str = "\n".join(imports)
#     full_code_list = [import_str] + instance_fixture_list + code_list
#     full_code = "\n\n".join(full_code_list)
#     return {"full_code": full_code}

def generate_class_test_code_from_filepath_list(module_dirpath, class_filepath_list, class_name):
    class_test_case_list = combine_class_test_cases(class_filepath_list)
    instance_class_test_case_dict = generate_class_tests(module_dirpath, class_test_case_list, class_name)
    imports = []
    global_variable_list = []
    code_list = []
    instance_fixture_list = []
    for inst_id, class_test_dict in instance_class_test_case_dict.items():
        global_variables = class_test_dict['global_variables']
        global_variable_list.extend(global_variables)
        instance_fixture = class_test_dict['instance_fixture']
        instance_fixture_list.append(instance_fixture)
        imports.extend(class_test_dict['imports'])
        code_list.extend(class_test_dict['code_list'])
    imports = list(dict.fromkeys(imports))
    import_str = "\n".join(imports)
    global_variable_str = "\n".join(list(dict.fromkeys(global_variable_list)))
    full_code_list = [import_str] + [global_variable_str] + instance_fixture_list + code_list
    full_code = "\n\n".join(full_code_list)
    return {"full_code": full_code}

def generate_class_test_code_from_dirpath(dirpath, module_dirpath):
    if not isinstance(dirpath, Path):
        dirpath = Path(dirpath)
    cluster_filepath_dict = get_cluster_filepath_dict(dirpath)
    res_dict = {}
    for item_type, filepath_list in cluster_filepath_dict.items():
        if item_type == 'standalone_function':
            for filepath in filepath_list:
                function_case_list = load_json(filepath)
                func_res_dict = generate_function_tests(function_case_list, module_dirpath)
                func_name = func_res_dict['function_name']
                res_dict[to_pascal_casing(func_name)] = func_res_dict
        else:
            # class test cases
            class_name = item_type
            class_res_dict = generate_class_test_code_from_filepath_list(module_dirpath, filepath_list, class_name)
            res_dict[class_name] = class_res_dict
    return res_dict

def copy_test_data(logs_dirpath, test_dirpath):
    if not isinstance(logs_dirpath, Path):
        logs_dirpath = Path(logs_dirpath)
    if not isinstance(test_dirpath, Path):
        test_dirpath = Path(test_dirpath)
    test_dirpath.mkdir(parents=True, exist_ok=True)
    src_path = logs_dirpath / "data"
    dst_path = test_dirpath / "data"
    if dst_path.exists():
        shutil.rmtree(dst_path)
    shutil.copytree(src_path, dst_path)
    # if not dst_path.exists():
    #     shutil.copytree(src_path, dst_path)
    

def generate_tests(module_dirpath):

    path_dict = get_path_dict(module_dirpath)
    path_dict = {k: Path(v) for k, v in path_dict.items()}
    logs_dirpath = path_dict['logs_dirpath']
    test_dirpath = path_dict['test_dirpath']
    module_dirpath = Path(module_dirpath).absolute()

    copy_test_data(logs_dirpath, test_dirpath)

    python_file_list = list(module_dirpath.glob("*.py"))
    log_dir_list = [
        logs_dirpath / filepath.relative_to(module_dirpath).with_suffix("") 
        for filepath in python_file_list 
        if filepath.stat().st_size > 0
    ]
    test_dir_list = [
        test_dirpath / filepath.relative_to(module_dirpath).with_suffix("") 
        for filepath in python_file_list 
        if filepath.stat().st_size > 0
    ]

    output_dir_to_input_dir_list = list(zip(test_dir_list, log_dir_list))
    
    res_filepath_list = []
    
    for output_dir, input_dir in output_dir_to_input_dir_list:
        name_code_dict = generate_class_test_code_from_dirpath(input_dir, module_dirpath)
        for name, code_dict in name_code_dict.items():
            print(name)
            filename = f"test_{to_snake_casing(name)}.py"
            filepath = output_dir / filename
            file_code = code_dict['full_code']
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(file_code)
            res_filepath_list.append(str(filepath))
    
    return res_filepath_list