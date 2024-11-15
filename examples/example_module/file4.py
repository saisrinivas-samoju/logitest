import pandas as pd

class DataPreprocessor:
    def __init__(self, filepath):
        self.filepath = filepath

    def read(self):
        df = pd.read_csv(self.filepath)
        return df

    def clean(self, df):
        df = df.dropna()
        return df

    def preprocess(self, df):
        df = self.clean(df)
        df = df.drop_duplicates()
        return df

    def get_df(self):
        df = self.read()
        df = self.preprocess(df)
        return df
