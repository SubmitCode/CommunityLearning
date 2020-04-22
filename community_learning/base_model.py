# AUTOGENERATED! DO NOT EDIT! File to edit: 04_base_model.ipynb (unless otherwise specified).

__all__ = ['load_data', 'train_test_split', 'x_y_split', 'runXGB', 'predict_all_products', 'apk',
           'get_top7_preds_string', 'get_results']

# Cell
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import cross_validate
from .features import target_cols
from fastscript import *
from tqdm.notebook import tqdm
from itertools import compress

# Cell
def load_data(path='data/interim/03_train.csv'):
    """load data"""
    return pd.read_csv(path)

# Cell
def train_test_split(df:pd.DataFrame):
    """split the data in a training and testset"""
    test_data = df[df.month_int == 17].copy()
    train_data = df[df.month_int < 17].copy()
    return (train_data, test_data)


# Cell
def x_y_split(df:pd.DataFrame, target_cols=target_cols):
    """returns 2 dataframes for X and Y variables"""
    X = df.drop(target_cols, axis=1)
    Y = df[target_cols].copy()
    return (X, Y)

# Cell
def runXGB(train_X, train_y, test_X, target_col, seed_val=0):
    param = {}
    param['objective'] = 'binary:logistic'
    param['eta'] = 0.05 # learning rate
    param['max_depth'] = 8
    #param['silent'] = 0
    #param['num_class'] = 22
    param['eval_metric'] = "logloss"
    param['min_child_weight'] = 1
    param['subsample'] = 0.7
    param['colsample_bytree'] = 0.7
    param['seed'] = seed_val
    num_rounds = 50

    plst = list(param.items())
    xgtrain = xgb.DMatrix(train_X, label=np.array(train_y[target_col]))
    model = xgb.train(plst, xgtrain, num_rounds)
    y_pred = model.predict(xgb.DMatrix(X_test))
    result_xgb_df = pd.DataFrame(index=test_X.id, columns=['pred_' + target_col], data=y_pred)
    result_xgb_df.reset_index(inplace=True)
    return result_xgb_df

# Cell
def predict_all_products(train_X, train_y, test_X, target_col):
    """create a model for each product and return a DataFrame with all predictions"""

    result_xgb = pd.DataFrame(test_X[['id']])

    for col in tqdm(target_col):
        result_xgb_df = runXGB(X_train.copy(), Y_train.copy(), X_test.copy(), col)
        result_xgb['pred_' + col] = result_xgb_df['pred_' + col].values

    result_xgb.drop('id', axis=1, inplace=True)
    return result_xgb

# Cell
def apk(actual, predicted, k=7):
    """
    Computes the average precision at k.
    This function computes the average prescision at k between two lists of
    items.
    Parameters
    ----------
    actual : list
             A list of elements that are to be predicted (order doesn't matter)
    predicted : list
                A list of predicted elements (order does matter)
    k : int, optional
        The maximum number of predicted elements
    Returns
    -------
    score : double
            The average precision at k over the input lists
    """
    if len(predicted)>k:
        predicted = predicted[:k]

    score = 0.0
    num_hits = 0.0

    for i,p in enumerate(predicted):
        if p in actual and p not in predicted[:i]:
            num_hits += 1.0
            score += num_hits / (i+1.0)

    if not actual:
        return 0.0

    return score / min(len(actual), k)

#%%
def get_top7_preds_string(row):
    """return top 7 column names"""
    row.sort_values(inplace=True)
    return row.index[-7:][::-1].tolist()

# Cell
def get_results(results:pd.DataFrame, Y_test:pd.DataFrame,  target_cols:list):
    """"""
    pred_cols = []
    for col in target_cols:
        name = 'pred_' + col
        pred_cols.append('pred_' + col)

    results['added_products'] = results[pred_cols].apply(lambda row: get_top7_preds_string(row), axis=1)
    results['added_products'] = results['added_products'].map(lambda x: [x[5:] for x in x]) #remove pred_ prefix
    results['truth_list'] = Y_test[target_cols].apply(lambda x: list(compress(target_cols, x.values)), axis=1)
    results['apk'] = results.apply(lambda x: apk(x['truth_list'],x['added_products']),axis=1)
    return results['apk'].mean()
