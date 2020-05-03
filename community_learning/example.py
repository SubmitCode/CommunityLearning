# AUTOGENERATED! DO NOT EDIT! File to edit: 05_xgboost_simple_ensemble.ipynb (unless otherwise specified).

__all__ = ['region', 'load_provice_data', 'add_region_to_nomprov', 'load_data', 'add_region_train_test',
           'get_two_region_data', 'get_two_region_base_models', 'get_prediction', 'evaluate_predictions',
           'fill_results']

# Cell
import pandas as pd
import numpy as np
import pickle
import xgboost as xgb

import community_learning.base_model as base_model

from fastscript import call_parse
from itertools import compress
from tqdm.notebook import tqdm

# Cell
region = {
"ALAVA":"north",
"ALBACETE":"south",
"ALICANTE":"south",
"ALMERIA":"south",
"ASTURIAS":"north",
"AVILA":"north",
"BADAJOZ":"south",
"BALEARS, ILLES":"north",
"BARCELONA":"north",
"BIZKAIA":"north",
"BURGOS":"north",
"CACERES":"north",
"CADIZ":"south",
"CANTABRIA":"north",
"CASTELLON":"north",
"CEUTA":"south",
"CIUDAD REAL":"south",
"CORDOBA":"south",
"CORUÑA, A":"north",
"CUENCA":"north",
"GIPUZKOA":"north",
"GIRONA":"north",
"GRANADA":"south",
"GUADALAJARA":"north",
"HUELVA":"south",
"HUESCA":"north",
"JAEN":"south",
"LEON":"north",
"LERIDA":"north",
"LUGO":"north",
"MADRID":"south",
"MALAGA":"south",
"MELILLA":"south",
"MURCIA":"south",
"NAVARRA":"north",
"OURENSE":"north",
"PALENCIA":"north",
"PALMAS, LAS":"north",
"PONTEVEDRA":"north",
"RIOJA, LA":"north",
"SALAMANCA":"north",
"SANTA CRUZ DE TENERIFE":"north",
"SEGOVIA":"north",
"SEVILLA":"south",
"SORIA":"north",
"TARRAGONA":"north",
"TERUEL":"north",
"TOLEDO":"north",
"UNKNOWN":"north",
"VALENCIA":"north",
"VALLADOLID":"north",
"ZAMORA":"north",
"ZARAGOZA":"north"
}

# Cell
def load_provice_data(path:str='data/raw/train_ver2.csv'):
    """laden der Rohdaten für die Ermittlung der Aufteilung"""
    reader = pd.read_csv(path, chunksize=100000, header=0, usecols=['ncodpers', 'nomprov'])
    train = pd.concat([chunk for chunk in reader])
    return train


# Cell
def add_region_to_nomprov(df:pd.DataFrame):
    """add a region column"""
    df = df.groupby(by='ncodpers').first()
    df['region'] = df['nomprov'].map(lambda x: region.get(x, '----'))
    return df

# Cell
def load_data(path_train='data/interim/03_train.csv',
              path_test='data/interim/03_test.csv'):
    """load data"""
    train = pd.read_csv(path_train)
    test = pd.read_csv(path_test)
    return (train, test)

# Cell
def add_region_train_test(train:pd.DataFrame,
                    test:pd.DataFrame,
                    region_df:pd.DataFrame):
    """split train and test data by region"""
    train = train.merge(region_df, left_on='id', right_on='ncodpers', how='left')
    test = test.merge(region_df, left_on='id', right_on='ncodpers', how='left')
    return (train, test)

# Cell
def get_two_region_data(source_train:str='data/interim/03_train.csv',
                               source_test:str='data/interim/03_test.csv',
                               source_raw:str='data/raw/train_ver2.csv'):
    """returns X, y data for each region"""
    data = dict()

    print('load data')
    train_org, test = load_data(source_train, source_test)
    print('prepare data')
    data['product_dict'] = base_model.get_product_dict(train_org)
    data['product_reverse_dict'] = base_model.get_product_reverse_dict(train_org)
    train = base_model.encode_products(train_org)
    region_df = load_provice_data(source_raw)
    region_df = add_region_to_nomprov(region_df)

    data['feature_cols'], data['target_cols'] = base_model.feature_cols, base_model.target_cols

    train, test = add_region_train_test(train, test, region_df)
    data['train'], data['test'] = train, test
    data['train_south'] = train.loc[train.region == 'south',]
    data['train_north'] = train.loc[train.region == 'north',]

    data['train_X_south'], data['train_y_south'] = base_model.x_y_split(train.loc[train.region == 'south',])
    data['train_X_north'], data['train_y_north'] = base_model.x_y_split(train.loc[train.region == 'north',])
    data['train_X'], data['train_y'] = base_model.x_y_split(train)


    test_south = test.loc[test.region == 'south']
    data['test_south'] = test_south.reset_index(drop=True)

    test_north = test.loc[test.region == 'north']
    data['test_north'] = test_north.reset_index(drop=True)

    return data

# Cell
def get_two_region_base_models(data:dict,
                               dest_model_south:str='data/results/model_south.dat',
                               dest_model_north:str='data/results/model_north.dat',
                               use_gpu=False):
    """load data, assign region, and train model per region"""


    print('train model south')
    model_south = base_model.runXGB(
        data['train_X_south'],
        data['train_y_south'],
        data['feature_cols'],
        use_gpu=use_gpu)

    print('train model north')
    model_north = base_model.runXGB(
        data['train_X_north'],
        data['train_y_north'],
        data['feature_cols'],
        use_gpu=use_gpu)

    print('train model all')
    model_all = base_model.runXGB(
        data['train_X'],
        data['train_y'],
        data['feature_cols'],
        use_gpu=use_gpu)

    models = {}
    models['model_south'], models['model_north'], models['model_all'] = model_south, model_north, model_all
    #pickle.dump(model_south, open(dest_model_south, 'wb'))
    #pickle.dump(model_north, open(dest_model_north, 'wb'))

    return models

# Cell
def get_prediction(model, data, feature_cols):
    """returns the results for two region model"""
    xgtest = xgb.DMatrix(data[feature_cols])
    return model.predict(xgtest)

# Cell
def evaluate_predictions(preds, test_data, target_cols, product_reverse_dict):
    """evaluates map metric"""
    preds = np.argsort(preds, axis=1)
    preds = np.fliplr(preds)[:,:7]
    preds = pd.DataFrame(preds)
    preds = preds.applymap(lambda x: product_reverse_dict[x])
    preds['added_products'] = preds.apply(lambda x: list(x.values), axis=1)
    preds = preds['added_products']

    test_data['added_products'] = preds
    test_data['truth_list'] = test_data[target_cols].apply(lambda x: list(compress(target_cols, x.values)), axis=1)
    test_data['apk'] = test_data.apply(lambda x: base_model.apk(x['truth_list'], x['added_products']),axis=1)
    #print(f"mean average precision = {test_data['apk'].mean()}")
    return test_data['apk'].mean()

# Cell
def fill_results(model_label, data_label, data, models, results_df):
    model = models[model_label]
    dat = data[data_label].copy()
    preds = get_prediction(model, dat, data['feature_cols'])
    result = evaluate_predictions(preds, dat, data['target_cols'], data['product_reverse_dict'])
    results_df.loc[data_label, model_label] = result
    return results_df