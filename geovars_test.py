from programa_geovars import *

with open("kmeans.pkl", "rb") as f:
    kmeans = pickle.load(f)
with open("scaler_lat.pkl", "rb") as f:
    scaler_lat = pickle.load(f)
with open("scaler_lon.pkl", "rb") as f:
    scaler_lon = pickle.load(f)
inProj = Proj(init="epsg:25830")
outProj = Proj(init="epsg:4326")
distance_thres = 0.0016
COD = "geo_"
test_df = pd.read_csv("dataset_test.csv")


def get_dfs(d):
    """
    Get nomecalles geopandas dfs and put them in a list so that it's easier to work with them.
    """
    dfs, nombres = [], []
    for folder in tqdm(os.listdir(d)):
        try:
            nombre = [
                f
                for f in os.listdir(f"{d}/{folder}/".replace(".zip", ""))
                if ".shp" in f
            ][0]
            dfs.append(
                gpd.read_file(
                    f"{d}/{folder}/{nombre}".replace(".zip", ""), encoding="latin1"
                )
            )
            nombres.append(nombre)
        except Exception as e:
            print(e)
    return dfs, nombres


def closest_node(node, nodes):
    """
    Computes the closest point and the distance to that point between a node and a bunch of nodes.
    """
    nodes = np.asarray(nodes)
    deltas = nodes - node
    dist_2 = np.einsum("ij,ij->i", deltas, deltas)
    return np.argmin(dist_2), np.min(dist_2)


def get_lon_lat(df, nombre, ruido=False):
    """
    This function receives a geopandas df, and a desired name for the variable
    extracted from that dataframe. It inspects the geometric objects inside the
    geopandas df and returns the latitude and longitude of each observation.
    
    Parameters
    ---------------
    df
        geopandas df.
    nombre
        the desired name for the variable.
    ruido
        This boolean controls whether we are calling it for the nomecalles variables 
        or for the "ruido" one.
    
    Return
    ----------------
    Dic
        {nombre: {'lat':..., 'lon':...}}
    """
    lat, lon = [], []
    for index, row in tqdm(df.iterrows()):
        lati, loni = [], []
        try:
            for pt in list(row["geometry"].exterior.coords):
                lati.append(pt[1])
                loni.append(pt[0])
        except Exception as e:
            try:
                row.geometry = row.geometry.map(lambda x: x.convex_hull)
                for pt in list(row["geometry"].exterior.coords):
                    lati.append(pt[1])
                    loni.append(pt[0])
            except Exception as e:
                try:
                    lati.append(df.iloc[index].geometry.centroid.y)
                    loni.append(df.iloc[index].geometry.centroid.x)
                except Exception as e:
                    if not ruido:
                        continue
                    else:
                        print(e)
                        print(df.iloc[index].geometry.centroid)
        lat.append(sum(lati) / len(lati))
        lon.append(sum(loni) / len(loni))
    latnew, lonnew = [], []
    for la, lo in zip(lat, lon):
        o, a = transform(inProj, outProj, lo, la)
        if o != float("inf") and a != float("inf"):
            latnew.append(a)
            lonnew.append(o)
    return {nombre: {"lon": lonnew, "lat": latnew}}


def get_zpae():
    """
    Returns the corrected geopandas df for ruido.
    """
    zpae = gpd.read_file("./ZPAE/ZPAE/TODAS_ZPAE_ETRS89.shp")
    mydic = get_lon_lat(zpae, "zpae", ruido=True)
    mydic["zpae"]["ruido"] = zpae.ZonaSupera
    return pd.DataFrame(mydic["zpae"])


def get_clusters(nombre):
    """
    Takes a name and, looking for the lat and lon inside the dictionary of that name,
    it applies a cluster over them and therefore we obtain a cluster assignation per
    observation.
    """
    lon, lat = mydic[nombre]["lon"], mydic[nombre]["lat"]
    scaled_lon = scaler_lon.transform(np.array(lon).reshape(-1, 1))
    scaled_lat = scaler_lat.transform(np.array(lat).reshape(-1, 1))
    clusters = kmeans.predict(
        pd.DataFrame({"x": [l for l in scaled_lat], "y": [l for l in scaled_lon]})
    )
    return clusters


def get_suma_var(nombre):
    """
    Counts how many obs for the variable <name> are in each cluster.
    """
    print(mydic[nombre]["clusters"])
    contador = dict(Counter([c for c in mydic[nombre]["clusters"]]))
    contador = {int(k): int(v) for k, v in contador.items()}
    # print(contador)
    return contador


def get_individual_df(nombre):
    """
    Creates a df with the subdictionary of that variable (name).
    """
    clusters = []
    contadores = []
    for k, v in mydic[nombre]["contador"].items():
        clusters.append(k)
        contadores.append(v)
    return pd.DataFrame({"cluster": clusters, f"contadores_{nombre}": contadores})


if __name__ == "__main__":
    print("#### ABRIENDO DFS ########")
    conflictivos = []
    dfs, nombres = get_dfs("./nomecalles2")
    print(nombres)
    mydic = {}
    print("########### COGIENDO LAT LON ##########")
    for df, nombre in zip(dfs, nombres):
        try:
            mydic.update(get_lon_lat(df, nombre))
        except Exception as e:
            print(e)
            conflictivos.append(nombre)
            continue
    print(mydic)
    test_df.drop("Unnamed: 0", axis=1, inplace=True)
    lat_scaled = scaler_lat.transform(test_df.lat.values.reshape(-1, 1)).reshape(-1, 1)
    lon_scaled = scaler_lon.transform(test_df.lon.values.reshape(-1, 1)).reshape(-1, 1)

    print("####### COGIENDO CLUSTERS #########")
    for nombre in tqdm(nombres):
        try:
            mydic[nombre]["clusters"] = get_clusters(nombre)
        except Exception as e:
            print(e)
            mydic.pop(nombre, None)
            conflictivos.append(nombre)
    print("######### SUMA VAR ############")
    for nombre in tqdm(nombres):
        try:
            mydic[nombre]["contador"] = get_suma_var(nombre)
        except Exception as e:
            print(e)
            conflictivos.append(nombre)
    print("########### INDIVIDUAL DFS ###########")
    processed_dfs = []
    for nombre in tqdm(nombres):
        try:
            processed_dfs.append(get_individual_df(nombre))
        except Exception as e:
            print(e)
            conflictivos.append(nombre)
    print("########## AÑADIENDO VARIABLE DE RUIDO ##############")

    zpae = get_zpae()
    points = [
        [l for l in test_df[["lon", "lat"]].iloc[ii]] for ii in range(test_df.shape[0])
    ]
    comparing_points = [
        [l for l in zpae[["lon", "lat"]].iloc[ii]] for ii in range(zpae.shape[0])
    ]
    closest_nodes = [closest_node(point, comparing_points) for point in points]
    distances = [t[1] for t in closest_nodes]
    which_points = [t[0] for t in closest_nodes]
    ruidos = []
    dists = []
    for i in tqdm(range(test_df.shape[0])):
        if distances[i] >= distance_thres:
            ruidos.append(zpae["ruido"].iloc[which_points[i]])
        else:
            ruidos.append("No_Reg_Cerca")
        dists.append(distances[i])
    test_df["ruido"] = ruidos
    test_df["distancias_al_ruido"] = dists

    print("####### MERGEANDO #########")
    df_final = reduce(
        lambda left, right: pd.merge(left, right, on="cluster", how="outer", sort=True),
        processed_dfs,
    )
    df_final.fillna(0, inplace=True)
    clusters_orig = kmeans.predict(
        pd.DataFrame({"x": [l for l in lat_scaled], "y": [l for l in lon_scaled]})
    )
    test_df["cluster"] = clusters_orig
    distances = kmeans.transform(
        pd.DataFrame({"x": [l for l in lat_scaled], "y": [l for l in lon_scaled]})
    )
    distances_to_centroids = []
    for i in range(test_df.shape[0]):
        distances_to_centroids.append(
            distances[i, test_df["cluster"].iloc[i]]
        )  # se podría hacer un np.min(..., axis=1) y debería salir igual, pero no se nota tanto el coste (unos segundos), y así nos aseguramos.
    test_df["distance_to_centroid"] = distances_to_centroids
    merged_df = pd.merge(test_df, df_final, on="cluster", how="inner")
    cols_with_nas = ["MAXBUILDINGFLOOR", "CADASTRALQUALITYID"]
    print(f"En el momento 4 el shape es de {merged_df.shape}")
    cols_imputar = []
    for col in merged_df:
        if col not in cols_with_nas:
            cols_imputar.append(col)
    merged_df[cols_imputar].fillna(value=0, inplace=True)
    print(f"En el momento 5 el shape es de {merged_df.shape}")
    merged_df.to_csv("TOTAL_TEST.csv", header=True, index=False)
    print("********** Finalizado ***********")
    print(
        f"****************** \n Los archivos conflictivos han sido \n {set(conflictivos)} ************"
    )
