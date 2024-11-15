import inspect
import json
from pathlib import Path
from typing import Any, Dict, Optional, Callable, Union, Set
import ast
import importlib.util
import sys
from functools import lru_cache, wraps
from joblib import dump

# from logitest.helper import to_pascal_casing, to_snake_casing, load_json, dump_json, get_abs_path
# from logitest.data_handler import DataHandler

from logitest.helper import to_pascal_casing, to_snake_casing, load_json, dump_json, get_abs_path
from logitest.data_handler import DataHandler
# from config import MODULE_DIRPATH

# Constants
LOG_DIR = Path("io_logs")
LOG_DIR.mkdir(exist_ok=True)

class TestClassifier:
    """Classifies functions as unit or integration tests based on their dependencies and characteristics"""
    
    def __init__(self):
        self.unit_functions: Set[str] = set()
        self.integration_functions: Set[str] = set()
        self.dependency_graph: Dict[str, Set[str]] = {}
        
        # Known integration indicators
        self.io_operations = {
            'open', 'read', 'write', 'requests', 
            'urlopen', 'socket', 'connect'
        }
        self.db_operations = {
            'execute', 'commit', 'cursor', 'query',
            'insert', 'update', 'delete'
        }
        self.external_libs = {
            'requests', 'pandas', 'numpy', 'sqlalchemy',
            'django', 'flask', 'pymongo'
        }

    @lru_cache(maxsize=128)
    def parse_file(self, file_path: str) -> Optional[ast.Module]:
        """Safely parse Python file and cache the AST"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return ast.parse(file.read(), filename=file_path)
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    def get_import_map(self, tree: ast.Module) -> Dict[str, str]:
        """Create mapping of imported names to their full paths"""
        imports = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports[name.asname or name.name] = name.name
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for name in node.names:
                    full_name = f"{module}.{name.name}" if module else name.name
                    imports[name.asname or name.name] = full_name
        return imports

    def get_function_calls(self, node: ast.FunctionDef, imports: Dict[str, str], 
                          current_module: str) -> Set[str]:
        """Extract function calls with their full paths"""
        calls = set()
        for n in ast.walk(node):
            if isinstance(n, ast.Call):
                if isinstance(n.func, ast.Name):
                    func_name = n.func.id
                    full_path = self.resolve_function_path(func_name, imports, current_module)
                    calls.add(full_path)
                elif isinstance(n.func, ast.Attribute):
                    attrs = []
                    current = n.func
                    while isinstance(current, ast.Attribute):
                        attrs.append(current.attr)
                        current = current.value
                    if isinstance(current, ast.Name):
                        attrs.append(current.id)
                    full_name = '.'.join(reversed(attrs))
                    full_path = self.resolve_function_path(full_name, imports, current_module)
                    calls.add(full_path)
        return calls

    def analyze_dependencies(self, func_name: str, file_path: str, 
                           visited: Optional[Set[str]] = None) -> bool:
        """Recursively analyze function dependencies"""
        if visited is None:
            visited = set()

        full_func_path = f"{Path(file_path).stem}.{func_name}"
        if full_func_path in visited:
            return full_func_path in self.integration_functions
        
        visited.add(full_func_path)
        tree = self.parse_file(file_path)
        if not tree:
            return False

        imports = self.get_import_map(tree)
        current_module = Path(file_path).stem

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                calls = self.get_function_calls(node, imports, current_module)
                self.dependency_graph[full_func_path] = calls

                # Check for integration indicators
                if self._has_integration_indicators(node, calls):
                    self.integration_functions.add(full_func_path)
                    return True

                # Recursively check dependencies
                for call in calls:
                    if self._check_dependency(call, visited):
                        self.integration_functions.add(full_func_path)
                        return True

                # Check if function combines multiple unit functions
                if len(calls) > 1:
                    self.integration_functions.add(full_func_path)
                    return True

        self.unit_functions.add(full_func_path)
        return False

    def _has_integration_indicators(self, node: ast.FunctionDef, calls: Set[str]) -> bool:
        """Check if function has direct integration indicators"""
        # Check calls against known integration operations
        for call in calls:
            parts = call.split('.')
            if any(part in self.io_operations for part in parts) or \
               any(part in self.db_operations for part in parts) or \
               any(part in self.external_libs for part in parts):
                return True

        # Check decorators
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                if decorator.id in {'integration', 'integration_test'}:
                    return True
            elif isinstance(decorator, ast.Attribute):
                if decorator.attr in {'integration', 'integration_test'}:
                    return True

        return False

    def _check_dependency(self, call: str, visited: Set[str]) -> bool:
        """Check if a dependency is an integration function"""
        try:
            call_parts = call.split('.')
            call_func = call_parts[-1]
            call_module = '.'.join(call_parts[:-1])
            
            module_path = self.find_module_file(call_module)
            if module_path:
                return self.analyze_dependencies(call_func, module_path, visited)
        except Exception as e:
            print(f"Error checking dependency {call}: {e}")
        return False

    def find_module_file(self, module_name: str) -> Optional[str]:
        """Find the file path for a module name"""
        try:
            if module_name in sys.modules:
                module = sys.modules[module_name]
            else:
                spec = importlib.util.find_spec(module_name)
                if spec is None:
                    return None
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            
            return module.__file__
        except Exception:
            return None

    def classify_test(self, func_name: str, file_path: str) -> bool:
        """Classify a function as unit or integration test"""
        full_path = f"{Path(file_path).stem}.{func_name}"
        
        if full_path in self.integration_functions:
            print(f"DEBUG: {full_path} already classified as integration")
            return True
        if full_path in self.unit_functions:
            print(f"DEBUG: {full_path} already classified as unit")
            return False
            
        result = self.analyze_dependencies(func_name, file_path)
        print(f"DEBUG: Classified {full_path} as {'integration' if result else 'unit'}")
        return result

    def resolve_function_path(self, func_name: str, imports: Dict[str, str], 
                            current_module: str) -> str:
        """Resolve full path of a function based on imports"""
        try:
            if '.' in func_name:
                base = func_name.split('.')[0]
                if base in imports:
                    return func_name.replace(base, imports[base], 1)
            elif func_name in imports:
                return imports[func_name]
            return f"{current_module}.{func_name}"
        except Exception as e:
            print(f"Error resolving path for {func_name}: {e}")
            return func_name

classifier = TestClassifier()

def get_next_set_number(base_path: str, class_name: str, method_name: str) -> int:
    """Get the next available set number for data files"""
    data_dir = Path(base_path)
    existing_files = list(data_dir.glob(f"{class_name}_{method_name}_set_*.pkl"))
    
    if not existing_files:
        return 1
        
    set_numbers = []
    for file in existing_files:
        parts = file.stem.split('_')
        try:
            set_num = int(parts[-2])  # "set_X" where X is the number
            set_numbers.append(set_num)
        except (ValueError, IndexError):
            continue
    
    return max(set_numbers, default=0) + 1

def get_type_info(obj: Any) -> str:
    """Get the full type information of an object"""
    if obj is None:
        return "NoneType"
    return f"{obj.__class__.__module__}.{obj.__class__.__name__}"

def serialize_data(obj: Any, class_name: str, method_name: str, io_type: str, set_number: int, source_subdir: Path) -> Dict:
    """Serialize data with joblib support for non-JSON serializable objects"""
    # if obj is None:
    #     return None
    log_dir = Path("io_logs") # / source_subdir
    log_dir.mkdir(parents=True, exist_ok=True)
    data_dir = Path("io_logs/data") # / source_subdir
    data_dir.mkdir(parents=True, exist_ok=True)
    data_handler = DataHandler(log_dir=log_dir, data_dir=data_dir)
    return data_handler.dump_to_json(obj, class_name, method_name, io_type, set_number, source_subdir)
        
# def serialize_data(obj: Any, class_name: str, method_name: str, io_type: str, set_number: int, source_subdir: Path) -> Dict:
#     """Serialize data with joblib support for non-JSON serializable objects"""
#     if obj is None:
#         return None
        
#     try:
#         json.dumps(obj)
#         return {
#             "type": "json",
#             "original_type": get_type_info(obj),
#             "value": obj
#         }
#     except (TypeError, OverflowError):
#         # For non-JSON serializable objects, use joblib
#         data_dir = Path("io_logs/data") / source_subdir
#         data_dir.mkdir(parents=True, exist_ok=True)
        
#         filename = f"{class_name}_{to_pascal_casing(method_name)}_set_{set_number}_{io_type}.pkl" if len(class_name) else f"{to_pascal_casing(method_name)}_set_{set_number}_{io_type}.pkl"
#         file_path = data_dir / filename
        
#         dump(obj, file_path, compress=3)
        
#         return {
#             "type": "pickle",
#             "original_type": get_type_info(obj),
#             # "file_path": str(file_path)
#             "file_path": get_abs_path(file_path)
#         }
        
# def get_loadable(io_dict):
#     if io_dict['type']=='json':
#         return io_dict['value']
#     elif io_dict['type']=='pickle':
#         # return f"load(\'{io_dict['file_path']}\')"
#         return {"filepath_to_load": io_dict['file_path']}
#     else:
#         raise Exception("UnknownDataType")
    
def get_mapping_kwargs(func, args, kwargs, is_method: bool = False):
    """Get mapped kwargs from args and kwargs"""
    sig = inspect.signature(func)
    
    # Special handling for methods (both __init__ and instance methods)
    if is_method:
        try:
            # For methods, include 'self' in binding but remove it later
            bound_args = sig.bind(*(['dummy_self'] + list(args)), **kwargs)
        except TypeError:
            bound_args = sig.bind(*args, **kwargs)
    else:
        # For regular functions
        bound_args = sig.bind(*args, **kwargs)
        
    bound_args.apply_defaults()
    mapped_kwargs = bound_args.arguments
    
    # Remove 'self' and 'cls' from the mapped kwargs
    mapped_kwargs = {k: v for k, v in mapped_kwargs.items() if k not in ['self', 'cls', 'dummy_self']}
    
    return mapped_kwargs
    

# def log_io(func):
#     @wraps(func)
#     def wrapper(*args, **kwargs):
#         # Get function metadata
#         function_name = func.__name__
#         function_file = inspect.getfile(func)
#         module_name = func.__module__
#         is_integration = classifier.classify_test(function_name, function_file)
        
#         # Get relative path from module root
#         module_path = Path.cwd() / MODULE_DIRPATH  # Make module path absolute
#         source_path = Path(function_file).relative_to(module_path)
#         log_subdir = source_path.with_suffix('')
        
#         # Create log directory preserving path structure
#         log_dir = Path("io_logs") / log_subdir
#         log_dir.mkdir(parents=True, exist_ok=True)
        
#         # Create data directory preserving path structure
#         data_dir = Path("io_logs/data") / log_subdir
#         data_dir.mkdir(parents=True, exist_ok=True)
        
#         # Get class name and instance ID if it's a method
#         class_name = ""
#         instance_id = None
#         if args and hasattr(args[0].__class__, function_name):
#             class_name = args[0].__class__.__name__
#             instance_id = id(args[0])
        
#         try:
#             # Execute function
#             output = func(*args, **kwargs)
            
#             # # Get set number for this call
#             # set_number = get_next_set_number("io_logs/data", class_name, function_name)
        
#             # Save to log file
#             log_file = log_dir / f"{class_name}_{to_pascal_casing(function_name)}_log.json" if class_name else log_dir / f"{to_pascal_casing(function_name)}_log.json"
#             if log_file.exists():
#                 logs = load_json(log_file)
#                 set_number = len(load_json(log_file)) + 1
#             else:
#                 logs = []
#                 set_number = 1
            
#             # Process inputs and output
#             processed_args = [
#                 serialize_data(arg, class_name, function_name, f"input_{i}", set_number, log_subdir)
#                 for i, arg in enumerate(args[1:] if class_name else args)
#             ]
            
#             processed_kwargs = {
#                 key: serialize_data(val, class_name, function_name, f"input_kwarg_{key}", set_number, log_subdir)
#                 for key, val in kwargs.items()
#             }
            
#             processed_output = serialize_data(output, class_name, function_name, "output", set_number, log_subdir)
            
            
            
#             # mapping all kwargs
#             loadable_args = [get_loadable(arg) for arg in processed_args]
#             loadable_kwargs = {k: get_loadable(v) for k, v in processed_kwargs.items()}
#             mapped_kwargs = get_mapping_kwargs(func, loadable_args, loadable_kwargs, bool(class_name))
        
            
#             log_entry = {
#                 "function_name": function_name,
#                 "function_file": function_file,
#                 "module_name": module_name,
#                 "class_name": class_name,
#                 "instance_id": instance_id,
#                 "is_method": bool(class_name),
#                 "is_integration": is_integration,
#                 "input": {
#                     "args": processed_args,
#                     "kwargs": processed_kwargs,
#                     "mapped_kwargs": mapped_kwargs,
#                 },
#                 "output": processed_output,
#                 "set_number": set_number
#             }
            

            
#             try:
#                 # if log_file.exists():
#                 #     # with open(log_file, 'r') as f:
#                 #     #     logs = json.load(f)
#                 #     logs = load_json(log_file)
#                 # else:
#                 #     logs = []
                
#                 logs.append(log_entry)
                
#                 # with open(log_file, 'w') as f:
#                 #     json.dump(logs, f, indent=4)
#                 dump_json(logs, log_file)
                    
#             except Exception as e:
#                 print(f"Warning: Failed to log for {function_name}: {str(e)}")
            
#             return output
            
#         except Exception as e:
#             print(f"Error in {function_name}: {str(e)}")
#             raise
            
#     return wrapper

def log_io(module_path):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get function metadata
            function_name = func.__name__
            function_file = inspect.getfile(func)
            module_name = func.__module__
            is_integration = classifier.classify_test(function_name, function_file)
            
            # Get relative path from module root
            # module_path = Path.cwd() / MODULE_DIRPATH  # Make module path absolute
            # source_path = Path(function_file).relative_to(module_path)
            source_path = Path(function_file).resolve().relative_to(Path(module_path).resolve())
            log_subdir = source_path.with_suffix('')
            
            # Create log directory preserving path structure
            log_dir = Path("io_logs") / log_subdir
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Create data directory preserving path structure
            data_dir = Path("io_logs/data") / log_subdir
            data_dir.mkdir(parents=True, exist_ok=True)
            
            # Get class name and instance ID if it's a method
            class_name = ""
            instance_id = None
            if args and hasattr(args[0].__class__, function_name):
                class_name = args[0].__class__.__name__
                instance_id = id(args[0])
            
            try:
                # Execute function
                output = func(*args, **kwargs)
                
                # # Get set number for this call
                # set_number = get_next_set_number("io_logs/data", class_name, function_name)
            
                # Save to log file
                log_file = log_dir / f"{class_name}_{to_pascal_casing(function_name)}_log.json" if class_name else log_dir / f"{to_pascal_casing(function_name)}_log.json"
                if log_file.exists():
                    logs = load_json(log_file)
                    set_number = len(load_json(log_file)) + 1
                else:
                    logs = []
                    set_number = 1
                
                # Process inputs and output
                processed_args = [
                    serialize_data(arg, class_name, function_name, f"input_{i}", set_number, log_subdir)
                    for i, arg in enumerate(args[1:] if class_name else args)
                ]
                
                processed_kwargs = {
                    key: serialize_data(val, class_name, function_name, f"input_kwarg_{key}", set_number, log_subdir)
                    for key, val in kwargs.items()
                }
                
                processed_output = serialize_data(output, class_name, function_name, "output", set_number, log_subdir)
                             
                
                # mapping all kwargs
                # loadable_args = [get_loadable(arg) for arg in processed_args]
                # loadable_kwargs = {k: get_loadable(v) for k, v in processed_kwargs.items()}
                # mapped_kwargs = get_mapping_kwargs(func, loadable_args, loadable_kwargs, bool(class_name))
                mapped_kwargs = get_mapping_kwargs(func, processed_args, processed_kwargs, bool(class_name))
                
                # mapped_kwargs = {key: serialize_data(val, class_name, function_name, f"input_kwarg_{key}", set_number, log_subdir) for key, val in mapped_kwargs.items()}
            
                
                log_entry = {
                    "function_name": function_name,
                    "function_file": Path(function_file).as_posix(),
                    "module_name": module_name,
                    "class_name": class_name,
                    "instance_id": instance_id,
                    "is_method": bool(class_name),
                    "is_integration": is_integration,
                    "input": {
                        "args": processed_args,
                        "kwargs": processed_kwargs,
                        "mapped_kwargs": mapped_kwargs,
                    },
                    "output": processed_output,
                    "set_number": set_number
                }
                

                
                try:
                    # if log_file.exists():
                    #     # with open(log_file, 'r') as f:
                    #     #     logs = json.load(f)
                    #     logs = load_json(log_file)
                    # else:
                    #     logs = []
                    
                    logs.append(log_entry)
                    
                    # with open(log_file, 'w') as f:
                    #     json.dump(logs, f, indent=4)
                    dump_json(logs, log_file)
                        
                except Exception as e:
                    print(f"Warning: Failed to log for {function_name}: {str(e)}")
                
                return output
                
            except Exception as e:
                print(f"Error in {function_name}: {str(e)}")
                raise
                
        return wrapper
    return decorator