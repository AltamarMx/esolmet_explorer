import pandas as pd
import numpy as np
import validation_tools as vt
from utils.config import load_settings
import glob

variables, latitude, longitude, gmt, name = load_settings()
ALLOWED_VARS = list(variables.values())
MIN_YEAR = 2010
SOLAR_CONSTANT = 1361  # W/m², constante solar


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


def load_csv(filepath: str) -> pd.DataFrame:
    """
    Carga y limpia CSV en formato ancho:
      1. lee y parsea fechas
      2. descarta filas con TIMESTAMP NaT o año < MIN_YEAR
      3. define TIMESTAMP como índice datetime
      4. filtra sólo variables permitidas
      5. elimina columnas 'RECORD' y 'Unnamed*'
      6. convierte todas las columnas (índice excluido) a float
      7. elimina duplicados (basados en índice y valores)
      8. ordena por TIMESTAMP
      9. limpieza para columnas de radiación (dni, ghi, dhi):
         - valores < 0 → 0
         - valores > constante solar → NaN
         - valores > 0 cuando altitud solar ≤ 0 → NaN
    """
    # 1. leer crudo 
    params = _detect_csv(filepath)
    common_kwargs = dict(
        filepath_or_buffer=filepath,
        skiprows=params["skiprows"],
        dayfirst=False,
        low_memory=False,
        encoding=params["encoding"],
    )
    try:
        df = pd.read_csv(**common_kwargs)
    except UnicodeDecodeError:
        common_kwargs["encoding"] = "latin-1"
        df = pd.read_csv(**common_kwargs)

    # 2. renombrar primera columna a TIMESTAMP y definir datetime
    df.rename(columns={df.columns[0]: "TIMESTAMP"}, inplace=True)
    df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"], errors="coerce")

    # 3. descartar filas con TIMESTAMP NaT y filtrar año mínimo
    df = df.dropna(subset=["TIMESTAMP"])
    df = df[df["TIMESTAMP"].dt.year >= MIN_YEAR]

    # 4. definir TIMESTAMP como índice datetime
    df.set_index("TIMESTAMP", inplace=True)

    # 5. renombrar variables usando el diccionario
    if variables:
        df.rename(columns=variables, inplace=True)

    # 6. eliminar columnas innecesarias:
    #    - cualquier columna que empiece con 'Unnamed'
    #    - 'RECORD'
    #    - columnas que no estén en ALLOWED_VARS
    drop_cols = [
        c for c in df.columns
        if c.startswith("Unnamed") or c == "RECORD" or c not in ALLOWED_VARS
    ]
    df.drop(columns=drop_cols, inplace=True)

    # 7. convertir todas las columnas (ahora que el índice es TIMESTAMP) a numérico (float)
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 8. eliminar duplicados (basados en índice y valores de columnas)
    df = df[~df.index.duplicated(keep="first")]  # quita duplicados en el índice
    df = df.drop_duplicates()                     # quita duplicados completos de filas

    # 9. ordenar por TIMESTAMP
    df.sort_index(inplace=True)

    # 10. limpieza para columnas de radiación (solo dni, ghi, dhi)
    rad_cols = [col for col in ["dni", "ghi", "dhi", "uv"] if col in df.columns]
    if rad_cols:
        # a) valores < 0 → 0
        df[rad_cols] = df[rad_cols].clip(lower=0)

        # b) volver NaN los datos de rad_cols que excedan la constante solar
        for col in rad_cols:
            df.loc[df[col] > SOLAR_CONSTANT, col] = np.nan

        # c) agregar columnas 'solar_altitude' y 'radiation' usando vt.detect_radiation
        df = vt.detect_radiation(df)

        # d) para horas nocturnas (solar_altitude ≤ 0), convertir rad_cols > 0 a NaN
        noche = df["solar_altitude"] <= 0
        for col in rad_cols:
            df.loc[noche & (df[col] > 0), col] = np.nan

        # e) eliminar columnas auxiliares antes de finalizar
        df.drop(columns=["solar_altitude", "radiation"], inplace=True)

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
    if "TIMESTAMP" in df.columns:
        df_radiacion = df.copy()
        df_radiacion["TIMESTAMP"] = pd.to_datetime(df_radiacion["TIMESTAMP"], errors="coerce")
        df_radiacion = df_radiacion.set_index("TIMESTAMP")
        rad = vt.detect_radiation(df_radiacion, config_path="configuration.ini")["radiation"].all()
    else:
        rad = False

    # 4) tipos de columna
    tipos = vt.detect_dtype({col: "float64" for col in df.columns if col != "TIMESTAMP"}, df)

    return {
        "Extensión .CSV":         ext,
        "Encoding UTF-8":         enc,
        # "Sin valores NaN":        nans,
        "Sin valores NaT":        nats,
        "Sin valores duplicados": dups,
        "Columnas tipo float":    tipos,
        # "Radiación cero en noche": rad
    }


def export_data(filepath: str) -> pd.DataFrame:
    """
    Prepara DF en formato largo para carga en BD:
      - usa load_csv para obtener DataFrame limpio en forma ancha
      - convierte TIMESTAMP a string 'YYYY-MM-DD HH:MM:SS'
      - melt a ['fecha','variable','valor']
      - garantiza tipo float en 'valor'
    """
    # 1. cargar
    df = load_csv(filepath)

    # 2. resetear índice para tener TIMESTAMP como columna
    df = df.reset_index()

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


def radiacion(df: pd.DataFrame, rad_columns=None) -> pd.DataFrame:
    """
    Extrae datos de radiación durante la noche (altura solar ≤ 0):
      - calcula la altitud solar
      - devuelve sólo columnas de radiación y 'altura_solar'
    """
    # 1. calcular altura solar (agrega columnas auxiliares)
    df_radiacion = vt.detect_radiation(df)

    # 2. renombrar columna a español
    df_radiacion.rename(columns={'solar_altitude': 'altura_solar'}, inplace=True)

    # 3. determinar columnas de radiación
    rad_cols = ["dni", "ghi", "dhi", "uv"]
    default_cols = [variables.get(c, c) for c in rad_cols]
    columnas = rad_columns or default_cols
    columnas = [c for c in columnas if c in df_radiacion.columns]
    if not columnas:
        raise KeyError("No se encontraron columnas de radiación válidas en el DataFrame.")

    # 4. filtrar registros nocturnos
    mask_noche = df_radiacion['altura_solar'] <= 0
    resultado = df_radiacion.loc[mask_noche, columnas + ['altura_solar']].copy()

    # 7. redondear altitud solar
    resultado['altura_solar'] = resultado['altura_solar'].round(2)

    return resultado


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
