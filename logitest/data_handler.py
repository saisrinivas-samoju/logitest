import re
import json
import pickle
import joblib
import dill
from pathlib import Path
from typing import Any, Dict, Union, Optional
from logitest.helper import to_pascal_casing
from logitest.config import type_handlers


def load_json(filepath: Union[str, Path]) -> Union[list, dict]:
    """Load the JSON file at the given filepath

    Args:
        filepath (Union[str, Path]): filepath of the JSON file

    Returns:
        Union[list, dict]: content in the JSON file
    """
    with open(str(filepath), 'r', encoding='utf-8') as f:
        return json.load(f)


def dump_json(obj: Any, filepath: Union[str, Path], indent: int = 4):
    """Dump the JSON Content at the given filepath

    Args:
        obj (Any): Object to be dumped as JSON
        filepath (Union[str, Path]): filepath of the JSON file
        indent (int, optional): number of spaces to be present in the JSON file indentation. Defaults to 4.
    """
    with open(str(filepath), 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=indent, ensure_ascii=False)


def load_dill(filepath: Union[str, Path]):
    """Load the dill file at the given filepath

    Args:
        filepath (Union[str, Path]): filepath of the dill file

    Returns:
        Union[list, dict]: content in the dill file
    """
    with open(str(filepath), 'rb') as f:
        data = dill.load(f)
    return data


def dump_dill(obj: Any, filepath: Union[str, Path]):
    """Dump the dill content at the given filepath

    Args:
        obj (Any): Object to be dumped as dill
        filepath (Union[str, Path]): filepath of the dill file
    """
    with open(str(filepath), "wb") as f:
        dill.dump(obj, f)


def load_pickle(filepath: Union[str, Path]):
    """Load the pickle file at the given filepath

    Args:
        filepath (Union[str, Path]): filepath of the pickle file

    Returns:
        Union[list, dict]: content in the pickle file
    """
    with open(str(filepath), "rb") as f:
        data = pickle.load(f)
    return data


def dump_pickle(obj: Any, filepath: Union[str, Path]):
    """Dump the pickle content at the given filepath

    Args:
        obj (Any): Object to be dumped as pickle
        filepath (Union[str, Path]): filepath of the pickle file
    """
    with open(str(filepath), "wb") as f:
        pickle.dump(obj, f)


class DataHandler:
    def __init__(self, type_handlers: dict = type_handlers, log_dir: str = "io_logs", data_dir: str = "io_logs/data") -> None:
        """Create an instance of the Data Handler class with the required inputs

        Args:
            type_handlers (dict, optional): Python dictionary of custom objects and their load and dump functions. Defaults to type_handlers.
            log_dir (str, optional): directory path to save I/O logs. Defaults to "io_logs".
            data_dir (str, optional): directory path to save the data files to be loaded. Defaults to "io_logs/data".
        """
        self.type_handlers = type_handlers
        self.log_dir = Path(log_dir)
        self.data_dir = Path(data_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.pickle_handler = {
            "pickle": {
                # let's keep this pickle only as the other pickle files from type handlers can have extension as 'pkl'
                "extension": "pickle",
                "load": load_pickle,
                "dump": dump_pickle
            },
        }
        self.fallback_handlers = {
            "joblib": {
                "extension": "joblib",
                "load": joblib.load,
                "dump": joblib.dump
            },
            "dill": {
                "extension": "dill",
                "load": load_dill,
                "dump": dump_dill
            }
        }

        self.all_type_handlers = self.type_handlers | self.pickle_handler | self.fallback_handlers

    def _get_type_info(self, obj: Any) -> str:
        """Get the data type information

        Args:
            obj (Any): Any python object

        Returns:
            str: string representation of the python object
        """
        return str(type(obj).__module__) + '.' + type(obj).__name__

    def load(self, filepath: Path, type_str: str, extension: str) -> Any:
        """Load any python object at the given path with the given extension and data type

        Args:
            filepath (Path): filepath of the python object
            type_str (str): data type of the python object
            extension (str): filepath extension to write

        Raises:
            ValueError: If the data type is not recorded in config or in fallbacks

        Returns:
            Any: loaded python object
        """
        if not isinstance(filepath, Path):
            filepath = Path(filepath)
        if isinstance(filepath, Path):
            filepath = Path(filepath)
        if filepath.suffix == '.json':
            return load_json(str(filepath.absolute().as_posix()))
        elif type_str in self.type_handlers:
            handler = self.type_handlers[type_str]
            if extension == handler['extension']:
                return handler['load'](str(filepath.absolute().as_posix()))
        elif filepath.suffix == '.pickle':
            return load_pickle(str(filepath.absolute().as_posix()))
        elif type_str in self.fallback_handlers:
            handler = self.fallback_handlers[type_str]
            if extension == handler['extension']:
                return handler['load'](str(filepath.absolute().as_posix()))
        raise ValueError(f"Unsupported library: {type_str}")

    def dump(self, obj: Any, filepath: Path, type_str: str) -> None:
        """Dump any python object from the given filepath with the given data type

        Args:
            obj (Any): Any python object
            filepath (Path): filepath to dump the python object
            type_str (str): data type of the python object

        Raises:
            ValueError: If the data type is not recorded in config or in fallbacks
        """
        if not isinstance(filepath, Path):
            filepath = Path(filepath)
        if isinstance(filepath, Path):
            filepath = Path(filepath)
        if filepath.suffix == '.json':
            dump_json(obj, str(filepath.absolute().as_posix()))
        elif type_str in self.type_handlers:
            self.type_handlers[type_str]['dump'](
                obj, str(filepath.absolute().as_posix()))
        elif filepath.suffix == '.pickle':
            dump_pickle(obj, str(filepath.absolute().as_posix()))
        elif type_str in self.fallback_handlers:
            self.fallback_handlers[type_str]['dump'](
                obj, str(filepath.absolute().as_posix()))
        else:
            raise ValueError(f"Unsupported library: {type_str}")

    def dump_to_json(self, obj: Any, class_name: str, method_name: str, io_type: str, set_number: int, source_subdir: Path) -> Dict:
        """Dump the python object and record it in a JSON format to add it in the logs.

        Args:
            obj (Any): Any python object
            class_name (str): Class name in which it being used (if any)
            method_name (str): method name or function in which is being used as I/O
            io_type (str): input or output
            set_number (int): set number of record for the given class method/function
            source_subdir (Path): location of the python file in which it is being used

        Raises:
            RuntimeError: Raise this exception when there is no way mentioned to seralize this python object

        Returns:
            Dict: Output dictionary to add to the JSON logs
        """
        try:
            json.dumps(obj)
            return {"type": "json", "original_type": type(obj).__name__, "value": obj}
        except (TypeError, OverflowError):
            if isinstance(obj, (list, tuple)):
                return {
                    "type": "nested",
                    "original_type": type(obj).__name__,
                    "value": [self.dump_to_json(item, class_name=class_name, method_name=method_name, io_type=io_type, set_number=set_number, source_subdir=source_subdir) for item in obj]
                }
            elif isinstance(obj, dict):
                return {
                    "type": "nested",
                    "original_type": "dict",
                    "value": {k: self.dump_to_json(v, class_name=class_name, method_name=method_name, io_type=io_type, set_number=set_number, source_subdir=source_subdir) for k, v in obj.items()}
                }
            else:
                type_str = self._get_type_info(obj)
                filename = f"{class_name}_{to_pascal_casing(method_name)}_set_{set_number}_{io_type}{{}}" if len(
                    class_name) else f"{to_pascal_casing(method_name)}_set_{set_number}_{io_type}{{}}"
                filepath = self.data_dir / source_subdir / filename
                filepath = str(filepath.resolve().as_posix())
                if type_str in self.type_handlers:
                    handler_dict = self.type_handlers[type_str]
                    ext = handler_dict['extension']
                    dump_func = handler_dict['dump']
                    try:
                        if not ext.startswith("."):
                            ext = "."+ext
                        filepath = filepath.format(ext)
                        dump_func(obj, filepath)
                        return {"type": type_str, "original_type": type(obj).__name__, "filepath": filepath}
                    except:
                        pass
                # else:
                type_str = list(self.pickle_handler.keys())[0]
                ext = self.pickle_handler[type_str]['extension']
                dump_func = self.pickle_handler[type_str]['dump']
                try:
                    if not ext.startswith("."):
                        ext = "."+ext
                    filepath = filepath.format(ext)
                    dump_func(obj, filepath)
                    return {"type": type_str, "original_type": type(obj).__name__, "filepath": filepath}
                except:
                    for type_str, handler_dict in self.fallback_handlers.items():
                        ext = handler_dict['extension']
                        dump_func = handler_dict['dump']
                        if not ext.startswith("."):
                            ext = "."+ext
                        try:
                            filepath = filepath.format(ext)
                            dump_func(obj, filepath)
                            return {"type": type_str, "original_type": type(obj).__name__, "filepath": filepath}
                        except Exception:
                            continue
        raise RuntimeError("All serialization methods failed.")

    def load_from_json(self, data: Dict) -> Any:
        """Load the python object from the JSON data/python dictionary

        Args:
            data (Dict): python dictionary with the recordings of the python object to load.

        Raises:
            ValueError: raise this error if there is no way mentioned in the config to load the given python object

        Returns:
            Any: Loaded python object
        """
        if data['type'] == 'json':
            return data['value']
        if data['type'] == 'nested':
            if data['original_type'] == 'list':
                return [self.load_from_json(item) for item in data['value']]
            elif data['original_type'] == 'tuple':
                return tuple([self.load_from_json(item) for item in data['value']])
            elif data['original_type'] == 'dict':
                return {k: self.load_from_json(v) for k, v in data['value']}
        if data['type'] in self.all_type_handlers:
            return self.all_type_handlers[data['type']]['load'](data['filepath'])
        raise ValueError(f"Unsupported data type: {data['type']}")

    def _make_arg_recipe(self, io_val: Optional[dict]) -> Optional[Union[dict, list, str]]:
        """Helper function to make the recipe to load the python object in code

        Args:
            io_val (Optional[dict]): argument/keyword argument/output value to generate the code recipe

        Returns:
            Optional[Union[dict, str]]: code recipe string when the object is not JSON serializable, else dictionary or a list
        """
        if isinstance(io_val, dict) and "type" in io_val:
            if io_val['type'] == 'json':
                return io_val['value']
            if io_val['type'] == 'nested':
                if io_val['original_type'] == 'list':
                    return [self._make_arg_recipe(item) for item in io_val['value']]
                elif io_val['original_type'] == 'tuple':
                    return [self._make_arg_recipe(item) for item in io_val['value']]
                elif io_val['original_type'] == 'dict':
                    return {k: self._make_arg_recipe(v) for k, v in io_val['value']}
            if io_val['type'] in self.all_type_handlers:
                return f"""data_handler.load(filepath='{Path(io_val['filepath']).as_posix()}', type_str='{io_val['type']}', extension='{Path(io_val['filepath']).suffix}')"""
        return io_val

    def make_arg_recipe(self, io_val: Optional[dict]) -> str:
        """Code recipe to load custom objects in the test cases code

        Args:
            io_val (Optional[dict]): argument/keyword argument/output value to generate the code recipe

        Returns:
            str: Code recipe to load custom objects in the test cases code in string format
        """
        arg_recipe = self._make_arg_recipe(io_val)
        if isinstance(arg_recipe, str):
            arg_recipe = re.sub(
                r'["\'](data_handler\.load\(.*?\))["\']', r'\1', arg_recipe)
        return arg_recipe
