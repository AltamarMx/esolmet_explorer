# %%
import pandas as pd
import numpy as np
import validation_tools as vt
from utils.config import load_settings

# %%
def load_csv(filepath: str) -> pd.DataFrame:
    # 1. lectura inicial
    df = pd.read_csv(
        filepath,
        skiprows=[0, 2, 3],
        dayfirst=False,
        low_memory=False
    )
    variables, latitude, longitude, gmt, name = load_settings()
    ALLOWED_VARS = list(variables.values())
    MIN_YEAR = 2010
    SOLAR_CONSTANT = 1361

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

        # c) agregar columnas 'solar_altitude' y 'radiation_ok' usando vt.detect_radiation
        df = vt.detect_radiation(df)

        # d) para horas nocturnas (solar_altitude ≤ 0), convertir rad_cols > 0 a NaN
        noche = df["solar_altitude"] <= 0
        for col in rad_cols:
            df.loc[noche & (df[col] > 0), col] = np.nan

        # e) eliminar columnas auxiliares antes de finalizar
        df.drop(columns=["solar_altitude", "radiation_ok"], inplace=True)

    return df

# %%
load_csv('Esolmet_CR6_IP_TableWEB_10min.csv')