from example_module.file1 import add, subtract
from example_module.file2 import multiply
from example_module.file3 import calc
from example_module.file4 import DataPreprocessor

if __name__=="__main__":
    dp = DataPreprocessor("./example_module/iris.csv")
    # dp = DataPreprocessor('D:/CodeWork/GitHub/logitest/examples/example_module/iris.csv')
    df = dp.read()
    dp.clean(df)
    print(df)
    add(a = 2, b = 3)
    add(8, b=2)
    add(5, 10)
    dp = DataPreprocessor("./example_module/iris copy.csv")
    # dp = DataPreprocessor('D:/CodeWork/GitHub/logitest/examples/example_module/iris.csv')
    df = dp.get_df()
    add(20, 30)
    subtract(10, 5)
    subtract(10, 3)
    multiply(2, 3)
    calc(10, 13)