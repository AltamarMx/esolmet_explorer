# %%
import pandas as pd
import duckdb
# %%


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

    df = pd.read_csv(filepath,skiprows=[0,2,3],parse_dates=[0],dayfirst=True,low_memory=False)
    ALLOWED_VARS = ["I_dir_Avg","I_glo_Avg","I_dif_Avg","I_uv_Avg","AirTC_Avg","RH","WS_ms_Avg","WindDir","CS106_PB_Avg","Rain_mm_Tot"]

    # 2. renombrar fecha y asegurar datetime
    df.rename(columns={df.columns[0]: "TIMESTAMP"}, inplace=True)
    df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"], errors="coerce")

    # 3. eliminar columnas innecesarias
    drop_cols = [c for c in df.columns if c.startswith("Unnamed")
                 or c == "RECORD"
                 or c not in (["TIMESTAMP"] + ALLOWED_VARS)]
    if drop_cols:
        df.drop(columns=drop_cols, inplace=True)


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

load_csv('Esolmet_CR6_IP_TableWEB_10min.csv')
# %%
