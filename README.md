# logitest
A lightweight module for logging and testing. No fluff, just tools to get the job done efficiently.

## Installation
```bash
pip install logitest
```

## Running in terminal
```bash
logitest examples/example_module examples/main.py
```

## Running in python
```py
from logitest import create_test_cases

create_test_cases(module_dirpath = "examples/example_module", main_filepath="examples/main.py")
```

## Sample code to generate test cases when you have custom I/O objects

If you have external objects (non in-built python objects) as input/output in our functions/methods. Here is how you need to configure the module before trying to get the test cases.

### Add custom type handlers

```py
from logitest import get_dtype, add_to_config
```

```py
# Create custom load and dump functions

import fitz

def load_pdf(filepath):
    doc = fitz.open(filepath)
    return doc

dump_pdf = lambda doc, filepath: doc.save(filepath)
```

```py
# To know the datatype of the object, load a sample object and check like this:

doc = load_pdf("C:/Users/samoj/Downloads/COA requirements.pdf")
# doc = load_pdf("./COA requirements.pdf")

get_dtype(doc) # This will be used as the key for your new_type_handlers dictionary
```
    > 'pymupdf.Document'

```py
# Now, create a type handling dictionary as shown below
# Note: This new dictionary should have the name 'new_type_handlers'

new_type_handlers = {
    "pymupdf.Document": {
        "extension": ".npy", 
        "load": load_pdf, 
        "dump": dump_pdf
    }
}
```

```py
# Now add the entire code in a triple string, like this:

type_handler_str = """import fitz

def load_pdf(filepath):
    doc = fitz.open(filepath)
    return doc

dump_pdf = lambda doc, filepath: doc.save(filepath)

new_type_handlers = {
    "pymupdf.Document": {
        "extension": ".npy", 
        "load": load_pdf, 
        "dump": dump_pdf
    }
}"""
```

### Add custom Assertion mappings

```py
# If you have any custom assert functions to load, follow this process

# First create your custom assert function

import fitz  # PyMuPDF

def assert_documents_equal(doc1_path, doc2_path, tolerance=0):
    doc1 = fitz.open(doc1_path)
    doc2 = fitz.open(doc2_path)

    if len(doc1) != len(doc2):
        raise AssertionError(f"Documents have different number of pages: {len(doc1)} != {len(doc2)}")

    for page_num in range(len(doc1)):
        pix1 = doc1[page_num].get_pixmap()
        pix2 = doc2[page_num].get_pixmap()

        if pix1.size != pix2.size or pix1.samples != pix2.samples:
            diff = sum(
                abs(a - b)
                for a, b in zip(pix1.samples, pix2.samples)
            )
            if diff > tolerance:
                raise AssertionError(
                    f"Page {page_num + 1} differs beyond tolerance level {tolerance}. "
                    f"Difference: {diff}."
                )
    return True
```

```py
# Create a new assertion mapping dictionary
# Note, the name of this dictionary should new_assertion_mapping

new_assertion_mapping = {"pymupdf.Document": ( # key is as usual the object it can test
    "from logitest.config import assert_documents_equal", # standard import statement to import the custom function
    "assert_documents_equal" # custom function name
    )
}
```

```py
# Now add this entire code in triple quotes like this:

assertion_mapping_str = """import fitz  # PyMuPDF

def assert_documents_equal(doc1_path, doc2_path, tolerance=0):
    doc1 = fitz.open(doc1_path)
    doc2 = fitz.open(doc2_path)

    if len(doc1) != len(doc2):
        raise AssertionError(f"Documents have different number of pages: {len(doc1)} != {len(doc2)}")

    for page_num in range(len(doc1)):
        pix1 = doc1[page_num].get_pixmap()
        pix2 = doc2[page_num].get_pixmap()

        if pix1.size != pix2.size or pix1.samples != pix2.samples:
            diff = sum(
                abs(a - b)
                for a, b in zip(pix1.samples, pix2.samples)
            )
            if diff > tolerance:
                raise AssertionError(
                    f"Page {page_num + 1} differs beyond tolerance level {tolerance}. "
                    f"Difference: {diff}."
                )
    return True

new_assertion_mapping = {"pymupdf.Document": ("from logitest.config import assert_documents_equal", "assert_documents_equal")}
"""
```

### Adding custom code to config

```py
# The final line for configuring the module

add_to_config(type_handling_str=type_handler_str, assertion_mapping_str=assertion_mapping_str)
```

### Create and run tests
```py
# Finally to create the test cases for your code

from logitest import create_test_cases

# Pass your module directory path and main.py which uses this code to run your module pipeline
create_test_cases(module_dirpath = "examples/example_module", main_filepath="examples/main.py")
```

## Contributing

Feel free to fork the repo and submit pull requests. Contributions are always welcome!

## License

This project is licensed under the [MIT License](https://github.com/saisrinivas-samoju/langchain_training/blob/main/LICENSE)