from setuptools import setup, find_packages

setup(
    name='logitest',
    version='0.1.3',
    description='Automated test case generation tool for Python modules.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Sai Srinivas',
    author_email='saisrinivas.samoju@example.com',
    url='https://github.com/saisrinivas-samoju/logitest',
    packages=find_packages(),
    include_package_data=True,  # Includes files specified in MANIFEST.in
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.9',
    install_requires=[
        'pytest',   # Used for running generated tests
        'joblib',   # For serialization
        'dill',
    ],
    entry_points={
        'console_scripts': [
            'logitest=logitest.__init__:create_test_cases_cli',  # Entry point for CLI
        ],
    },
)
