import pandas as pd
import validation_tools as vt
from utils.config import load_settings
import glob

variables, latitude, longitude, gmt, name, alias = load_settings()
ALLOWED_VARS = variables
MIN_YEAR = 2010


def _detect_csv(filepath: str) -> dict:
    """
    Detecta encoding y filas a omitir según el header.
    """
    use_utf8 = vt.detect_encoding(filepath)
    encoding = "utf-8" if use_utf8 else "latin-1"
    with open(filepath, "r", encoding=encoding, errors="replace") as f:
        header = f.readline()
    skiprows = [] if "TIMESTAMP" in header else [0, 2, 3]
    return {"encoding": encoding, "skiprows": skiprows}


def load_csv(filepath: str, sort: bool = True) -> pd.DataFrame:
    """
    Carga y limpia CSV en formato ancho:
      - lee y parsea fechas
      - filtra sólo variables permitidas
      - convierte todas las columnas (excepto TIMESTAMP) a float
      - elimina columnas 'RECORD' y 'Unnamed*'
      - filtra TIMESTAMP ≥ MIN_YEAR
      - elimina filas con NaN en TIMESTAMP o en datos
      - elimina duplicados
      - ordena por TIMESTAMP
    """
    # 1. leer crudo
    params = _detect_csv(filepath)
    common_kwargs = dict(
        filepath_or_buffer=filepath,
        skiprows=params["skiprows"],
        parse_dates=[0],
        dayfirst=True,
        low_memory=False,
        encoding=params["encoding"],
    )
    try:
        df = pd.read_csv(**common_kwargs)
    except UnicodeDecodeError:
        common_kwargs["encoding"] = "latin-1"
        df = pd.read_csv(**common_kwargs)

    # 2. renombrar fecha y asegurar datetime
    df.rename(columns={df.columns[0]: "TIMESTAMP"}, inplace=True)
    df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"], errors="coerce")

    # 3. eliminar columnas innecesarias
    drop_cols = [c for c in df.columns if c.startswith("Unnamed")
                 or c == "RECORD"
                 or c not in (["TIMESTAMP"] + ALLOWED_VARS)]
    if drop_cols:
        df.drop(columns=drop_cols, inplace=True)

    # 4. filtrar año mínimo
    df = df[df["TIMESTAMP"].dt.year >= MIN_YEAR]

    # 5. convertir datos a float y limpiar nulos/duplicados
    for col in df.columns:
        if col != "TIMESTAMP":
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df.dropna(subset=["TIMESTAMP"], inplace=True)
    df.dropna(axis=0, how="any", subset=[c for c in df.columns if c!="TIMESTAMP"], inplace=True)
    df.drop_duplicates(inplace=True)

    # 6. ordenar
    if sort:
        df.sort_values("TIMESTAMP", inplace=True)
        df.reset_index(drop=True, inplace=True)

    return df


def run_tests(df: pd.DataFrame, filepath: str) -> dict:
    """
    Ejecuta pruebas de calidad sobre el DataFrame y usa filepath para la extensión y el encoding.
    """
    # 1) pruebas sobre el archivo 
    ext = vt.detect_endswith(filepath)
    enc = vt.detect_encoding(filepath)

    # 2) integridad de datos en el df
    nans = vt.detect_nans(df)
    nats = vt.detect_nats(df)
    dups = vt.detect_duplicates(df)

    # 3) radiación nocturna
    rad_df = df.set_index("TIMESTAMP", drop=True)
    rad = vt.detect_radiation(rad_df, config_path="configuration.ini")["radiation_ok"].all()

    # 4) tipos de columna
    expected_types = {"TIMESTAMP": "datetime64[ns]"}
    for col in df.columns:
        if col != "TIMESTAMP":
            expected_types[col] = "float64"
    tipos = vt.detect_dtype(expected_types, df)

    return {
        "Extensión .CSV":         ext,
        "Encoding UTF-8":         enc,
        "Sin valores NaN":        nans,
        "Sin valores NaT":        nats,
        "Sin valores duplicados":         dups,
        "Columnas tipo float":          tipos,
        # "Sin radiación en la noche": rad,
    }


def export_data(filepath: str) -> pd.DataFrame:
    """
    Prepara DF en formato largo para carga en BD:
      - usa load_csv para obtener DataFrame limpio en forma ancha
      - convierte TIMESTAMP a string 'YYYY-MM-DD HH:MM:SS'
      - melt a ['fecha','variable','valor']
      - elimina duplicados y garantiza tipo float en 'valor'
    """
    # 1. cargar y limpiar
    df = load_csv(filepath, sort=False)

    # 2. renombrar columnas según alias definido en configuration.ini
    if alias:
        df.rename(columns=alias, inplace=True)

    # 3. convertir la fecha a string
    df['TIMESTAMP'] = df['TIMESTAMP'].dt.strftime('%Y-%m-%d %H:%M')

    # 4. transformar a formato largo
    long_df = df.melt(
        id_vars=['TIMESTAMP'],
        var_name='variable',
        value_name='valor'
    )
    long_df.columns = ['fecha', 'variable', 'valor']

    # 5. limpiar duplicados y asegurar tipo float
    long_df.drop_duplicates(subset=['fecha', 'variable'], inplace=True)
    long_df['valor'] = long_df['valor'].astype(float)

    return long_df


def radiacion(df, rad_columns=None):
    """
    Detecta eventos de radiación nocturna manteniendo solo las columnas configuradas.
    """
    # 0. filtrar columnas extras
    keep = ['TIMESTAMP'] + [c for c in ALLOWED_VARS if c in df.columns]
    df = df.loc[:, keep].copy()
    
    # 1. preparar índice datetime
    if 'TIMESTAMP' in df.columns:
        df['TIMESTAMP'] = pd.to_datetime(df['TIMESTAMP'], errors='coerce')
        df = df.dropna(subset=['TIMESTAMP']).set_index('TIMESTAMP')

    # 2. obtener solar_altitude y radiation_ok
    rad_df = vt.detect_radiation(df)

    # 3. renombrar para usar español
    rad_df = rad_df.rename(columns={'solar_altitude': 'altura_solar'})

    # 4. columnas de radiación
    cols = rad_columns or ['I_dir_Avg', 'I_glo_Avg', 'I_dif_Avg', 'I_dif_Calc', 'I_uv_Avg']
    cols = [c for c in cols if c in rad_df.columns]
    if not cols:
        raise KeyError("No hay columnas de radiación para filtrar.")

    # 5. filtrar registros nocturnos con radiación > 0
    mask_noche = rad_df['altura_solar'] <= 0
    mask_rad   = rad_df[cols].gt(0).any(axis=1)
    nocturna   = rad_df.loc[mask_noche & mask_rad, cols + ['altura_solar']]

    # 6. redondear altura solar a 2 decimales
    nocturna['altura_solar'] = nocturna['altura_solar'].round(2)

    return nocturna

# def _df_nans(df: pd.DataFrame, filepath: str) -> pd.DataFrame:
#     # 1. Calcula offset según skiprows
#     csv_opts   = _detect_csv(filepath)
#     skip_count = len(csv_opts["skiprows"]) - 1
#     offset     = skip_count + 3  # +2 líneas de cabecera +1 para 1-based

#     # 2. Encuentra los NaN en columnas no datetime
#     non_dt = df.select_dtypes(exclude=["datetime64[ns]", "datetimetz"]).columns
#     mask   = df[non_dt].isna()
#     nans   = mask.stack()[lambda s: s]

#     # 3. Si no hay NaN, devuelve mensaje
#     if nans.empty:
#         return pd.DataFrame({"Info": ["No se encontró ningún NaN en las columnas de datos."]})

#     # 4. Reconstruye posiciones y aplica offset
#     loc = nans.reset_index()
#     loc.columns      = ["Fila_idx", "Columna", "is_nan"]
#     loc["fila_original"] = loc["Fila_idx"] + offset

#     # 5. Devuelve sólo fila y columna
#     return (
#         loc[["fila_original", "Columna"]]
#         .rename(columns={"fila_original": "Fila"})
#     )


# def _df_nats(df: pd.DataFrame) -> pd.DataFrame:
#     # 1. Encuentra NaT en columnas datetime
#     datetime_cols = df.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns
#     mask          = df[datetime_cols].isna()
#     nats          = mask.stack()[lambda s: s]

#     # 2. Si no hay NaT, devuelve mensaje
#     if nats.empty:
#         return pd.DataFrame({"Info": ["No se encontró ningún NaT en la estampa temporal."]})

#     # 3. Reconstruye posiciones
#     loc = nats.reset_index()
#     loc.columns = ["Fila", "Columna", "is_nat"]

#     # 4. Devuelve sólo la fila original
#     return loc[["Fila"]]

def load_esolmet_data():
    archivos = glob.glob('data/2023*.csv')
    
    def importa_esolmet(archivo):
        # Usamos el parámetro archivo para leer cada CSV
        return pd.read_csv(archivo,
                           index_col=0, parse_dates=True, dayfirst=True)
    
    esolmet = pd.concat([importa_esolmet(archivo) for archivo in archivos])
    esolmet.sort_index(inplace=True)
    # esolmet.reset_index(inplace=True)
    esolmet.I_dir_Avg = esolmet.I_dir_Avg.astype(float)
    print(esolmet.info())
    return esolmet
