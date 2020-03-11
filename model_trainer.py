from sklearn.ensemble import RandomForestClassifier
from preprocessing import *
from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split, StratifiedKFold
import mlflow
import mlflow.sklearn
import mlflow.tracking
from xgboost import XGBClassifier
from catboost import CatBoostClassifier
from skopt import BayesSearchCV
import pickle
from sklearn.metrics import f1_score, precision_score, recall_score, accuracy_score
import matplotlib.pyplot as plt
import seaborn as sns
import os
from sklearn.utils import class_weight
from lightgbm import LGBMClassifier
from imblearn.over_sampling import RandomOverSampler, SMOTE
from imblearn.under_sampling import RandomUnderSampler
from imblearn.pipeline import Pipeline
from collections import Counter
from imblearn.pipeline import Pipeline

NAME = 'lightgbm_geovars_11_03'
N_ITER = 50
cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=100)

'''
params = {'n_estimators': (100, 1500),
            'max_depth': (6, 12),
            'class_weight': [None, 'balanced'],
            'n_jobs': [-1],
            'max_features': ['auto', 'log2'],
            }

'''

params = {'model__reg_alpha': (1e-2, 2.0, 'log-uniform'),
          'model__reg_lambda': (1e-2, 20.0, 'log-uniform'),
          'model__n_estimators': (1000, 2000),
          'model__learning_rate': (5e-3, 1.0, 'log-uniform')}


'''
params = {
        'learning_rate': (0.001, 1.0, 'log-uniform'),
        'min_child_weight': (0, 10),
        'max_depth': (2, 10),
        'max_delta_step': (1, 20),
        'subsample': (0.01, 1.0, 'uniform'),
        'colsample_bytree': (0.01, 1.0, 'uniform'),
        'colsample_bylevel': (0.01, 1.0, 'uniform'),
        'reg_lambda': (1e-9, 1000., 'log-uniform'),
        'reg_alpha': (1e-9, 10.0, 'log-uniform'),
        'gamma': (1e-9, 1.0, 'log-uniform'),
        'n_estimators': (100, 1000),
        'scale_pos_weight': (1e-6, 500., 'log-uniform')
    }
'''

'''
params = {
        'depth':(6,15),
        'iterations': (500, 1600),
        #'learning_rate': (1e-7, 1e-1),
        'reg_lambda': (1e-5, 10.0),
        #'l2_leaf_reg':(0.1, 100.),
        'bagging_temperature':(1e-8, 1., 'log-uniform'),
        'border_count':(1,255),
        #'rsm':(0.10, 0.8, 'uniform'),
        'random_strength':(1e-3, 3.0, 'log-uniform'),
    }
'''



#model = RandomForestClassifier()
#model = XGBClassifier(eval_metric = 'auc', n_jobs=-1, objective='multi:softmax', num_class=7)
#model = CatBoostClassifier(silent=True, objective='multi:softmax')

def print_confusion_matrix(confusion_matrix, class_names, figsize = (10,7), fontsize=14, normalize=True):
    """Prints a confusion matrix, as returned by sklearn.metrics.confusion_matrix, as a heatmap.

    Arguments
    ---------
    confusion_matrix: numpy.ndarray
        The numpy.ndarray object returned from a call to sklearn.metrics.confusion_matrix.
        Similarly constructed ndarrays can also be used.
    class_names: list
        An ordered list of class names, in the order they index the given confusion matrix.
    figsize: tuple
        A 2-long tuple, the first value determining the horizontal size of the ouputted figure,
        the second determining the vertical size. Defaults to (10,7).
    fontsize: int
        Font size for axes labels. Defaults to 14.

    Returns
    -------
    matplotlib.figure.Figure
        The resulting confusion matrix figure
    """
    if normalize:
        confusion_matrix = confusion_matrix.astype('float') / confusion_matrix.sum(axis=1)[:, np.newaxis]
        print("Normalized confusion matrix")
    else:
        print('Confusion matrix, without normalization')
    df_cm = pd.DataFrame(
        confusion_matrix, index=class_names, columns=class_names,
    )
    fig = plt.figure(figsize=figsize)
    fmt = '.2f' if normalize else 'd'
    try:
        heatmap = sns.heatmap(df_cm, annot=True, fmt=fmt)
    except ValueError:
        raise ValueError("Confusion matrix values must be integers.")
    heatmap.yaxis.set_ticklabels(heatmap.yaxis.get_ticklabels(), rotation=0, ha='right', fontsize=fontsize)
    heatmap.xaxis.set_ticklabels(heatmap.xaxis.get_ticklabels(), rotation=45, ha='right', fontsize=fontsize)
    plt.ylabel('True label')
    plt.xlabel('Predicted label')
    return fig


def get_classes_order_catboost(X_train, y_train):
    cat = CatBoostClassifier(iterations=10, depth=2, learning_rate=0.05, loss_function='MultiClass')
    cat.fit(X_train, y_train)
    return cat.classes_

def main():
    mlflow.start_run(run_name=NAME)
    print('procesando los datos')
    X, y, tag2idx = preprocess_data('TOTAL_TRAIN.csv', process_cat=True)
    print(f"##################### The shape of X is {X.shape} #######################")
    y=y.astype('int')
    
    if 'X_train.pkl' not in os.listdir():
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, random_state=15, stratify=y)

    else:
        with open('X_train.pkl', 'rb') as f:
            X_train = pickle.load(f)
        with open('X_test.pkl', 'rb') as f:
            X_test = pickle.load(f)
        with open('y_train.pkl', 'rb') as f:
            y_train = pickle.load(f)
        with open('y_test.pkl', 'rb') as f:
            y_test = pickle.load(f)
    
    X = X.astype('float')
    print(X.shape)
    print(X_train.shape)
    counter = Counter(y_train)
    maximo = 0
    for k, v in dict(counter).items():
        if v > maximo:
            maximo = v
            llave = k
        else:
            continue
    
    dic_smote = {k:int(v*20*(2/3)) for k, v in dict(counter).items()
                                if k != llave}
    print(dic_smote)
    dic_smote[tag2idx['OFFICE']] = int(dic_smote[tag2idx['OFFICE']]*1.7)
    over = SMOTE(sampling_strategy=dic_smote)
    
    under = RandomUnderSampler(sampling_strategy={k:int(v*0.95*(2/3)) for k, v in dict(counter).items()
                               if k == llave})

    with open('X_train.pkl', 'wb') as f:
        pickle.dump(X_train, f)
    with open('X_test.pkl', 'wb') as f:
        pickle.dump(X_test, f)
    with open('y_train.pkl', 'wb') as f:
        pickle.dump(y_train, f)
    with open('y_test.pkl', 'wb') as f:
        pickle.dump(y_test, f)

    #setlabs = [l for l in set(y_train)]
    #tag2idx = {i: l for l, i in enumerate(setlabs)}
    print(f"tag2idx is {tag2idx}")
    with open(f"tag2idx_{NAME}.pkl", "wb") as f:
        pickle.dump(tag2idx, f)
    '''
    pipe_imb = Pipeline([('o', over), ('u', under)])
    X_train_resam = pd.get_dummies(X_train, columns = X_train.columns[categoricas])
    X_resam, y_resam = pipe_imb.fit_resample(X_train_resam, y_train)
    '''
    '''
    cw = list(class_weight.compute_class_weight('balanced',
                                             get_classes_order_catboost(X_train, y_train),
                                             y_train))
    '''
    #print(f"Las features categoricas son {categoricas}, con dtypes {X_train.dtypes[categoricas]}")
    #model = CatBoostClassifier(silent=True, loss_function='MultiClass', cat_features=categoricas, class_weights=cw, boosting_type='Plain', max_ctr_complexity=2,  thread_count=-1) #, task_type="GPU", devices='0:1')
    
    model = LGBMClassifier(class_weight='balanced', objective='multiclass:softmax', n_jobs=-1)
    
    steps = [('o', over), ('u', under), ('model', model)]
    pipeline = Pipeline(steps)
    
    with open('best_lightgbm_geovars_10_03_params.pkl', 'rb') as f:
        params_probar_primero = pickle.load(f)
    
    nuevo_dic = {}
    
    for k in params_probar_primero.keys():
        k_ = k.replace('model__', '')
        nuevo_dic[k_] = params_probar_primero[k]
    
    pipeline_prueba = Pipeline([('o', over), 
                       ('u', under), 
                       ('model', LGBMClassifier(class_weight='balanced', objective='multiclass:softmax', n_jobs=-1, **nuevo_dic))])
    
    pipeline_prueba.fit(X_train, y_train)
    preds_pipeline_prueba = pipeline_prueba.predict(X_test)
    print(f"Resultado pipeline prueba: {f1_score(y_test, preds_pipeline_prueba, average='macro')}")
    #print(f"Score is {pipeline_prueba.score(y_test, X_test)}")
    best_model = BayesSearchCV(
                pipeline,
                params,
                n_iter = N_ITER,
                n_points=1,
                cv=cv,
                scoring='f1_macro',
                random_state=100,
                )

    def on_step(optim_result):
        score = best_model.best_score_
        results = best_model.cv_results_
        #preds = best_model.predict(X_test)
        try:
            results_df = pd.DataFrame(results)
            results_df.to_csv(f'results_{NAME}.csv', header=True, index=False)
            print(f'############ Llevamos {results_df.shape[0]} pruebas #################')
            print(f'los resultados del cv de momento son {results_df}')
        except:
            print('Unable to convert cv results to pandas dataframe')
        mlflow.log_metric('best_score', score)
        with open(f'./best_{NAME}_params.pkl', 'wb') as f:
            pickle.dump(best_model.best_params_, f)
        with open(f'./totalbs_{NAME}_model.pkl', 'wb') as f:
            pickle.dump(best_model, f)
        print("best score: %s" % score)
        if score >= 0.98:
            print('Interrupting!')
            return True

    #print(f'Los nombres de los features son {X.columns}')
    good_colnames = []
    for col in X_train.columns:
        if not col.isascii():
            print(f'La columna {col} no es ascii')
            good_colnames.append('ruido_Sin_Superacion')
        else:
            good_colnames.append(col)
    X_train.columns = good_colnames
    print('ajustando modelo')
    best_model.fit(X_train, y_train, callback=[on_step])
    with open(f'./best_{NAME}_model.pkl', 'wb') as f:
        pickle.dump(best_model, f)
    print('loggeando movidas')
    preds = best_model.predict(X_test)
    #print(f"El score ha sido de {best_model.score(X_test, y_test)}")
    #mlflow.log_artifact(f'./best_{NAME}_model.pkl')
    mlflow.log_metrics(metrics={'f1': f1_score(y_test, preds, average='macro'),
                           'precision': precision_score(y_test, preds, average='macro'),
                           'recall': recall_score(y_test, preds, average='macro'),
                           'accuracy': accuracy_score(y_test, preds)})
    best_params = best_model.best_params_
    for param in best_params.keys():
         mlflow.log_param(param, best_params[param])
    preds = best_model.predict(X_test)
    preds_proba = best_model.predict_proba(X_test)
    cm = confusion_matrix(y_test, preds)
    grafico_conf_matrix = print_confusion_matrix(cm, class_names = setlabs)
    grafico_conf_matrix.savefig(NAME)
    grafico_norm = print_confusion_matrix(cm, class_names = setlabs, normalize=False)
    grafico_norm.savefig(f'{NAME}_no_norm')
    mlflow.log_artifact(f'./{NAME}.png')
    mlflow.log_artifact(f'./{NAME}_no_norm.png')
    #mlflow.sklearn.log_model(best_model.best_estimator_, 'random_forest_model')
    mlflow.end_run()


if __name__ == '__main__':
    main()
