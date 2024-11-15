import re
import json
import pickle
import joblib
import dill
from pathlib import Path
from typing import Any, Dict
import numpy as np
import pandas as pd
from logitest.helper import to_pascal_casing
from logitest.config import type_handlers

# to_pascal_casing = lambda snaking_cased_text: "".join([word.title() for word in snaking_cased_text.split("_")])

type_handlers = {
    "pandas.core.frame.DataFrame": {
        "extension": ".pkl",
        "load": lambda filepath: pd.read_pickle(filepath),
        "dump": lambda obj, filepath: obj.to_pickle(filepath)
    },
    "numpy.ndarray": {
        "extension": ".npy",
        "load": lambda filepath: np.load(filepath, allow_pickle=False),
        "dump": lambda obj, filepath: np.save(filepath, obj)
    },
    "generic.pickle": {
        "extension": ".pkl",
        "load": lambda filepath: joblib.load(filepath),
        "dump": lambda obj, filepath: joblib.dump(obj, filepath)
    },
    "scikit-learn.model": {
        "extension": ".joblib",
        "load": lambda filepath: joblib.load(filepath),
        "dump": lambda obj, filepath: joblib.dump(obj, filepath)
    },
    "csv": {
        "extension": ".csv",
        "load": lambda filepath: pd.read_csv(filepath),
        "dump": lambda obj, filepath: obj.to_csv(filepath, index=False)
    },
    "text": {
        "extension": ".txt",
        "load": lambda filepath: open(filepath, 'r').read(),
        "dump": lambda obj, filepath: open(filepath, 'w').write(obj)
    },
}


def load_json(filepath):
    with open(str(filepath), 'r', encoding='utf-8') as f:
        return json.load(f)
    
def dump_json(obj, filepath, indent=4):
    with open(str(filepath), 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=indent, ensure_ascii=False)
        
def load_dill(filepath):
    with open(str(filepath), 'rb') as f:
        data = dill.load(f)
    return data
    
def dump_dill(obj, filepath):
    with open(str(filepath), "wb") as f:
        dill.dump(obj, f)
        
def load_pickle(filepath):
    with open(str(filepath), "rb") as f:
        data = pickle.load(f)
    return data
    
def dump_pickle(obj, filepath):
    with open(str(filepath), "wb") as f:
        pickle.dump(obj, f)

class DataHandler:
    def __init__(self, type_handlers: dict = type_handlers, log_dir: str = "io_logs", data_dir: str = "io_logs/data"):
        self.type_handlers = type_handlers
        self.log_dir = Path(log_dir)
        self.data_dir = Path(data_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.pickle_handler = {
            "pickle": {
                "extension": "pickle", # let's keep this pickle only as the other pickle files from type handlers can have extension as 'pkl'
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
        return str(type(obj).__module__) + '.' + type(obj).__name__
    
    def load(self, filepath: Path, type_str: str, extension: str) -> Any:
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
        if not isinstance(filepath, Path):
            filepath = Path(filepath)
        if isinstance(filepath, Path):
            filepath = Path(filepath)
        if filepath.suffix == '.json':
            dump_json(obj, str(filepath.absolute().as_posix()))
        elif type_str in self.type_handlers:
            self.type_handlers[type_str]['dump'](obj, str(filepath.absolute().as_posix()))
        elif filepath.suffix == '.pickle':
            dump_pickle(obj, str(filepath.absolute().as_posix()))
        elif type_str in self.fallback_handlers:
            self.fallback_handlers[type_str]['dump'](obj, str(filepath.absolute().as_posix()))
        else:
            raise ValueError(f"Unsupported library: {type_str}")
        
    def dump_to_json(self, obj: Any, class_name: str, method_name: str, io_type: str, set_number: int, source_subdir: Path) -> Dict:
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
                filename = f"{class_name}_{to_pascal_casing(method_name)}_set_{set_number}_{io_type}{{}}" if len(class_name) else f"{to_pascal_casing(method_name)}_set_{set_number}_{io_type}{{}}"
                filepath = self.data_dir / source_subdir / filename
                filepath = str(filepath.resolve().as_posix())
                if type_str in self.type_handlers:
                    handler_dict = self.type_handlers[type_str]
                    ext = handler_dict['extension']
                    dump_func = handler_dict['dump']
                    try:
                        if not ext.startswith("."):
                            ext = "."+ext
                        # filepath = self.data_dir / f"data_{id(obj)}_{type_str.replace('.', '-')}{ext}"
                        filepath = filepath.format(ext)
                        # filepath = str(Path(filepath).resolve().as_posix())
                        dump_func(obj, filepath)
                        # return {"type": type_str, "original_type": type(obj).__name__, "filepath": str(filepath.resolve())}
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
                    # filepath = self.data_dir / f"data_{id(obj)}_{type_str.replace('.', '-')}{ext}"
                    filepath = filepath.format(ext)
                    # filepath = str(Path(filepath).resolve().as_posix())
                    dump_func(obj, filepath)
                    return {"type": type_str, "original_type": type(obj).__name__, "filepath": filepath}
                except:
                    for type_str, handler_dict in self.fallback_handlers.items():
                        ext = handler_dict['extension']
                        dump_func = handler_dict['dump']
                        if not ext.startswith("."):
                            ext = "."+ext
                        try:
                            # filepath = self.data_dir / f"data_{id(obj)}_{type_str.replace('.', '-')}{ext}"
                            filepath = filepath.format(ext)
                            # filepath = str(Path(filepath).resolve().as_posix())
                            dump_func(obj, filepath)
                            return {"type": type_str, "original_type": type(obj).__name__, "filepath": filepath}
                        except Exception:
                            continue
        raise RuntimeError("All serialization methods failed.")
    
    def load_from_json(self, data: Dict) -> Any:
        if data['type'] == 'json':
            return data['value']
        if data['type'] == 'nested':
            if data['original_type']=='list':
                return [self.load_from_json(item) for item in data['value']]
            elif data['original_type']=='tuple':
                return tuple([self.load_from_json(item) for item in data['value']])
            elif data['original_type']=='dict':
                return {k: self.load_from_json(v) for k, v in data['value']}
        if data['type'] in self.all_type_handlers:
            return self.all_type_handlers[data['type']]['load'](data['filepath'])
        raise ValueError(f"Unsupported data type: {data['type']}")
    
    def _make_arg_recipe(self, io_val):
        if isinstance(io_val, dict) and "type" in io_val:
            if io_val['type']=='json':
                return io_val['value']
            if io_val['type'] == 'nested':
                if io_val['original_type']=='list':
                    return [self._make_arg_recipe(item) for item in io_val['value']]
                elif io_val['original_type']=='tuple':
                    return [self._make_arg_recipe(item) for item in io_val['value']]
                elif io_val['original_type']=='dict':
                    return {k: self._make_arg_recipe(v) for k, v in io_val['value']}
            if io_val['type'] in self.all_type_handlers:
                return f"""data_handler.load(filepath='{Path(io_val['filepath']).as_posix()}', type_str='{io_val['type']}', extension='{Path(io_val['filepath']).suffix}')"""
        return io_val
    
    def make_arg_recipe(self, io_val):
        arg_recipe = self._make_arg_recipe(io_val)
        if isinstance(arg_recipe, str):
            arg_recipe = re.sub(r'["\'](data_handler\.load\(.*?\))["\']', r'\1', arg_recipe)
        return arg_recipe