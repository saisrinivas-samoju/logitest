import numpy as np
import pandas as pd
import joblib

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

ASSERTION_MAPPING = {
    "pandas.core.frame.DataFrame": ("import pandas.testing as pd_testing", "pd_testing.assert_frame_equal"),
    "numpy.ndarray": ("import numpy.testing as np_testing", "np_testing.assert_array_equal"),
}
