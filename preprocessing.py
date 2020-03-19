import pandas as pd 
import numpy as np
from sklearn.preprocessing import MinMaxScaler, StandardScaler, LabelEncoder
from missingpy import MissForest
import pickle
from tqdm import tqdm
imputer = MissForest()
#X_imputed = imputer.fit_transform(X)

##### variables que se distribuyen "raro": 
# 3 , 13, 14 (rarísimo), 15 (casi normal pero algo asimétrico),
# 23 (casi normal pero algo asimétrico), 24, 25,
# 26 (asimétrica a tope), 27, 28, 30 (muy centrada, aunque así hay más)
# 31 (parecida a 30), 32 (igual q 31, 30), 33 (asimétrica con algunos outliers)
# 34 (parecida a 33), 35 (bastante asimétrica con outliers claros), 
# 36 (solo tiene valores en una franja concreta a excepción de unos pocos outliers)
# 38 (mucha asimetría), 39 (igual), 40 (igual), 41 (igual), 42 (igual), 43 (igual)
# 44 (igual), 45 (igual), 46 (rarísima, échale un ojo tú mismo),  
# 47 (casi todos los valores cerca del 0, algunos valores a tomar x culo)
# 49 (parecida a 47, pero el rango es menor), 50 (igual q 49)
# 51 (igual que 49 y 50 pero algo mayor el rango), 
# 52 (claramente entre los años 50 y 2000 se construyen la mayoría de las casas)
# 53 (me parece claramente categórica, dime tu como lo ves )
# 54 (claramente categórica; las clases B, A y C poco presentes)
# OBJ: 55 (una asimetría brutal la verdad..., pillar x ejemplo la clase agriculture va a ser muy complicado).

categorical = [53, 54]

minmax = MinMaxScaler()
stdscaler = StandardScaler()
encoder = LabelEncoder()

def process_categorical(df, cat_columns):
    for col in tqdm(cat_columns):
        print(f"procesada columna {col}")
        set_ = [l for l in set(df[col])]
        dic_ = {l:i for i, l in enumerate(set_)}
        #print(f'El diccionario de categorías es {dic_clase}')
        for i in range(df.shape[0]):
            df[col].iloc[i] = dic_[df[col].iloc[i]]
        df[col] = df[col].astype('category')
    return df

#CADASTRALQUALITYID A> B > C ...> 9

def process_cadqual(df):
    dic_ = {'A': 12, 'B':11, 'C': 10, '1': 9, '2':8, '3':7, '4':6, '5':4, '6':3, '7':2, '8':1, '9':0,
            '1.0':9, '2.0':8, '3.0':7, '4.0':6, '5.0':4, '6.0':3, '7.0':2, '8.0':1, '9.0':0, 'nan':np.nan}
    for i in tqdm(range(df.shape[0])):
        df['CADASTRALQUALITYID'].iloc[i] = dic_[df['CADASTRALQUALITYID'].iloc[i]]
    df.CADASTRALQUALITYID = df.CADASTRALQUALITYID.astype('float')
    return df

def rotate(p, origin=(0, 0), degrees=0):
    angle = np.deg2rad(degrees)
    R = np.array([[np.cos(angle), -np.sin(angle)],
                  [np.sin(angle),  np.cos(angle)]])
    o = np.atleast_2d(origin)
    p = np.atleast_2d(p)
    return np.squeeze((R @ (p.T-o.T) + o.T).T)


def three_dim_space(lat, lon):
    x = np.cos(lat) * np.cos(lon)
    y = np.cos(lat) * np.sin(lon)
    z = np.sin(lat)
    return x, y, z


def partial_preprocess_train(f, scale=True, scaler = 'std', process_cat = False, y_name='CLASE', sample_trials=None):
    """
    takes a file name and returns the processed dataset
    
    Parameters
    -------------
    f
        the filename
    scale
        whether to scale the numerical variables
    scaler
        which scaler to use for numerical variables
    process_cat
        whether to do one-hot encoding for categorical, as some models like catboost don't want them one-hot.
    y_name
        name of the variable where the objective is.
    sample_trials
        number of samples to take, if None, full data is returned.
    
    Returns
    -------------
    X
        The matrix with features
    y
        The vector with objective variable
    """
    df = pd.read_csv(f)
    if sample_trials is not None:
        df = df.sample(sample_trials)
    #set_clase = [l for l in set(df['CLASE'])]
    #dic_clase = {l:i for i, l in enumerate(set_clase)}
    #for i in tqdm(range(df.shape[0])):
    #    df['CLASE'].iloc[i] = dic_clase[df['CLASE'].iloc[i]]
    #y = df['CLASE'].values
    encoder.fit(df.CLASE.values)
    
    X = df.drop(['CLASE', 'ID', 'lat', 'lon'], axis = 1)
    X.CADASTRALQUALITYID = X.CADASTRALQUALITYID.astype('str')
    X.CODIGO_POSTAL = X.CODIGO_POSTAL.astype('str')
    X = process_cadqual(X)
    #X.MAXBUILDINGFLOOR = X.MAXBUILDINGFLOOR.astype('str')
    X.cluster = X.cluster.astype('str')
    if process_cat:
        X = pd.get_dummies(X, columns = X.columns[X.dtypes == object])
    cols = X.columns
    return X


def preprocess_data(f, scale=True, scaler = 'std', process_cat = False, y_name='CLASE', sample_trials=None):
    """
    takes a file name and returns the processed dataset
    
    Parameters
    -------------
    f
        the filename
    scale
        whether to scale the numerical variables
    scaler
        which scaler to use for numerical variables
    process_cat
        whether to do one-hot encoding for categorical, as some models like catboost don't want them one-hot.
    y_name
        name of the variable where the objective is.
    sample_trials
        number of samples to take, if None, full data is returned.
    
    Returns
    -------------
    X
        The matrix with features
    y
        The vector with objective variable
    """
    df = pd.read_csv(f)
    if sample_trials is not None:
        df = df.sample(sample_trials)
    #set_clase = [l for l in set(df['CLASE'])]
    #dic_clase = {l:i for i, l in enumerate(set_clase)}
    #print(f'El diccionario de categorías es {dic_clase}')
    #print(f'En momento 1 el shape es {df.shape}')
    #for i in range(df.shape[0]):
    #    df.loc[i, 'CLASE'] = dic_clase[df.loc[i, 'CLASE']]
    encoder.fit(df.CLASE.values)
    y = encoder.transform(df.CLASE.values)
    #y = df['CLASE'].values
    X = df.drop(['CLASE', 'ID', 'lat', 'lon', 'cluster'], axis = 1)
    print(f"Valores unicos de CADASTRAL--- {X.CADASTRALQUALITYID.unique()}")
    
    X.CADASTRALQUALITYID = X.CADASTRALQUALITYID.astype('str')
    X.CODIGO_POSTAL = X.CODIGO_POSTAL.astype('str')
    
    X = process_cadqual(X)
    print(f'En momento 2 el shape es de {X.shape}')
    #X.MAXBUILDINGFLOOR = X.MAXBUILDINGFLOOR.astype('str')
    #X.cluster = X.cluster.astype('str')
    print(f"Las columnas que tienen dtype object son {X.columns[X.dtypes == object]}")
    for col in X.columns[X.dtypes==object]:
        if sum(X[col].isna()):
            X.loc[X[col].isna(), col] = f"{col}_Ausente"
    
    if process_cat:
        X = pd.get_dummies(X, columns = X.columns[X.dtypes == object])
    print(f'En momento 3 el shape es de {X.shape}')
    print('Imputando valores con Random Forest')
    cols = X.columns
    imputer.fit(X)
    X = imputer.transform(X)
    with open('imputer.pkl', 'wb') as f:
        pickle.dump(imputer, f)
    
    print(f'En momento 4 el shape es de {X.shape}')
    X = pd.DataFrame(X, columns=cols)
    X.MAXBUILDINGFLOOR.clip(0., 25., inplace=True)
    X.CADASTRALQUALITYID.clip(0., 12., inplace=True)
    ########## HERE I TREAT LAT AND LON ########################
    geo_x, geo_y, geo_z = three_dim_space(X.X, X.Y)
    X['GEO_X'] = geo_x
    X['GEO_Y'] = geo_y
    X['GEO_Z'] = geo_z
    points = [(x, y) for x, y in zip(X.X, X.Y)]
    origin = (X.X.mean(), X.Y.mean())
    rotated90=rotate(points, origin, degrees=90)
    rotated180=rotate(points, origin, degrees=180)
    x_rot_90 = [r[0] for r in rotated90]
    y_rot_90 = [r[1] for r in rotated90]
    x_rot_180 = [r[0] for r in rotated180]
    y_rot_180 = [r[1] for r in rotated180]
    X['x_rot_90'] = x_rot_90
    X['y_rot_90'] = y_rot_90
    X['x_rot_180'] = x_rot_180
    X['y_rot_180'] = y_rot_180
    X['lat_2'] = X.X **2
    X['lon_2'] = X.Y **2
    X['latxlon'] = X.X * X.Y
    print(f'En momento 5 el shape es de {X.shape}')
    ############ VARIABLES GEOM Y AREA #########################
    #X['area_2'] = X.AREA ** 2
    #select_columns = [i for i in range(X.shape[1]) if i != categorical]
    # en caso de que lo veas bien, mete aquí transformaciones del tipo X[:, var] = np.log1p(X[:, var]),
    # antes de escalar
    select_columns = X.dtypes!=object
    if not process_cat:
        categoricas = []
        for i in range(X.shape[1]):
            if X.dtypes[i] == object:
                categoricas.append(i)
        X = process_categorical(X, X.columns[X.dtypes == object])
    colnames = X.columns
    X = np.array(X)                                   
    if scale:
        if scaler == 'std':
            X[:, select_columns] = stdscaler.fit_transform(X[:, select_columns])
        elif scaler == 'minmax':
            X[:, select_columns] = minmax.fit_transform(X[:, select_columns])
        print(f'En momento 6 el shape es de {X.shape}')
    if not process_cat:
        return pd.DataFrame(X, columns=colnames), y, categoricas
    else:
        return pd.DataFrame(X, columns=colnames), y, encoder
    
    
def preprocess_test(f, scale=True, scaler = 'std', process_cat = False, sample_trials=None):
    """
    takes a file name and returns the processed dataset
    
    Parameters
    -------------
    f
        the filename
    scale
        whether to scale the numerical variables
    scaler
        which scaler to use for numerical variables
    process_cat
        whether to do one-hot encoding for categorical, as some models like catboost don't want them one-hot.
    y_name
        name of the variable where the objective is.
    sample_trials
        number of samples to take, if None, full data is returned.
    
    Returns
    -------------
    X
        The matrix with features
    y
        The vector with objective variable
    """
    df = pd.read_csv(f)
    if sample_trials is not None:
        df = df.sample(sample_trials)
    #set_clase = [l for l in set(df['CLASE'])]
    #dic_clase = {l:i for i, l in enumerate(set_clase)}
    print(f'En momento 1 el shape es {df.shape}')
    X = df.drop(['ID', 'lat', 'lon', 'lat.1', 'lon.1'], axis = 1)
    print(f"Valores unicos de CADASTRAL--- {X.CADASTRALQUALITYID.unique()}")
    X.CADASTRALQUALITYID = X.CADASTRALQUALITYID.astype('str')
    X.CODIGO_POSTAL = X.CODIGO_POSTAL.astype('str')
    X = process_cadqual(X)
    print(f'En momento 2 el shape es de {X.shape}')
    #X.MAXBUILDINGFLOOR = X.MAXBUILDINGFLOOR.astype('str')
    #X.cluster = X.cluster.astype('str')
    print(f"Las columnas que tienen dtype object son {X.columns[X.dtypes == object]}")
    if process_cat:
        X = pd.get_dummies(X, columns = X.columns[X.dtypes == object])
    print(f'En momento 3 el shape es de {X.shape}')
    print('Imputando valores con Random Forest')
    cols = X.columns
    X_train = partial_preprocess_train('TOTAL_TRAIN.csv', scale=True, scaler = 'std', process_cat = True, y_name='CLASE')
    '''
    with open('imputer.pkl', 'rb') as f:
        imputer = pickle.load(f)
    '''
    try:
        imputer.fit(X_train)
        X = imputer.transform(X)
    except Exception as e:
        print(e)
        X = imputer.fit_transform(X)
    print(f'En momento 4 el shape es de {X.shape}')
    X = pd.DataFrame(X, columns=cols)
    ########## HERE I TREAT LAT AND LON ########################
    geo_x, geo_y, geo_z = three_dim_space(X.X, X.Y)
    X['GEO_X'] = geo_x
    X['GEO_Y'] = geo_y
    X['GEO_Z'] = geo_z
    points = [(x, y) for x, y in zip(X.X, X.Y)]
    origin = (X.X.mean(), X.Y.mean())
    rotated90=rotate(points, origin, degrees=90)
    rotated180=rotate(points, origin, degrees=180)
    x_rot_90 = [r[0] for r in rotated90]
    y_rot_90 = [r[1] for r in rotated90]
    x_rot_180 = [r[0] for r in rotated180]
    y_rot_180 = [r[1] for r in rotated180]
    X['x_rot_90'] = x_rot_90
    X['y_rot_90'] = y_rot_90
    X['x_rot_180'] = x_rot_180
    X['y_rot_180'] = y_rot_180
    X['lat_2'] = X.X **2
    X['lon_2'] = X.Y **2
    X['latxlon'] = X.X * X.Y
    print(f'En momento 5 el shape es de {X.shape}')
    ############ VARIABLES GEOM Y AREA #########################
    #X['area_2'] = X.AREA ** 2
    #select_columns = [i for i in range(X.shape[1]) if i != categorical]
    # en caso de que lo veas bien, mete aquí transformaciones del tipo X[:, var] = np.log1p(X[:, var]),
    # antes de escalar
    select_columns = X.dtypes!=object
    if not process_cat:
        categoricas = []
        for i in range(X.shape[1]):
            if X.dtypes[i] == object:
                categoricas.append(i)
        X = process_categorical(X, X.columns[X.dtypes == object])
    colnames = X.columns
    X = np.array(X)                                   
    if scale:
        if scaler == 'std':
            X[:, select_columns] = stdscaler.fit_transform(X[:, select_columns])
        elif scaler == 'minmax':
            X[:, select_columns] = minmax.fit_transform(X[:, select_columns])
        print(f'En momento 6 el shape es de {X.shape}')
    if not process_cat:
        return pd.DataFrame(X, columns=colnames)
    else:
        return pd.DataFrame(X, columns=colnames)

