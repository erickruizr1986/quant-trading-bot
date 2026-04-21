import sqlite3
import pandas as pd
from sklearn.linear_model import LogisticRegression

def train_model():

    conn = sqlite3.connect("trades.db")
    df = pd.read_sql("SELECT * FROM trades WHERE result IS NOT NULL", conn)
    conn.close()

    if len(df) < 30:
        return None

    X = df[["score"]]
    y = df["result"].apply(lambda x: 1 if x == "WIN" else 0)

    model = LogisticRegression()
    model.fit(X, y)

    return model


def predict(model, score):

    if model is None:
        return 0.6

    return model.predict_proba([[score]])[0][1]
