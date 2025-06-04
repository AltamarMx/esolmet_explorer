from typing import Dict
import pandas as pd
import glob
import pvlib
from utils.config import load_settings


def detect_encoding(filepath: str) -> bool:
    """
    Detects whether a file is encoded in UTF-8 by attempting to decode it.

    Args:
        filepath (str): Path to the file to analyze.

    Returns:
        bool: True if the sample can be decoded as UTF-8 (or UTF-8 compatible), False otherwise.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for _ in f:  # read line by line
                pass
        return True
    except UnicodeDecodeError:
        return False


def detect_endswith(filepath):
    """
    Detects the type of file based on its extension.
    Parameters:
        filepath (str): The path to the file to be checked.
    Returns:
        bool: True if the file ends with '.csv', False otherwise.
    """
    if filepath.endswith('.csv'):
        tag_endswith = True
    else:
        tag_endswith = False
        print("El archivo no termina en csv")
        
    return tag_endswith


def detect_nans(df : pd.DataFrame) -> bool:
    """
    Detects if a DataFrame contains any NaN values.
    Parameters:
        df (pd.DataFrame): The DataFrame to check for NaN values.
    Returns:
        bool: True if there are no NaN values in the DataFrame, False otherwise.
    """
    if df.isnull().sum().sum() == 0:
        tag_nans = True
    else:
        tag_nans = False

    return tag_nans


def detect_nats(df: pd.DataFrame) -> bool:
    """
    Checks whether a DataFrame contains any NaT (Not a Time) values in its datetime columns.
    Parameters:
        df (pd.DataFrame): The DataFrame to inspect.
    Returns:
        bool: True if no NaT values are found in any datetime columns;
              False if at least one NaT is present.
    """
    # Select only datetime columns (including timezone-aware)
    datetime_cols = df.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns

    # Check each datetime column for NaT values
    for col in datetime_cols:
        if df[col].isna().any():
            return False

    return True


def detect_duplicates(df: pd.DataFrame) -> bool:
    """Return ``True`` if the ``DataFrame`` contains no duplicate rows."""

    # ``DataFrame.duplicated`` checks row-wise duplicates ignoring the index.
    has_dups = df.duplicated().any()
    return not has_dups


def detect_dtype(columns_expected_type: Dict[str, str], data: pd.DataFrame) -> bool:
    """
    Verifies that the data types of the DataFrame columns match the expected types.
    
    Parameters:
        columns_expected_type (Dict[str, str]): A dictionary where the keys are the column names and the values 
                                                  are the expected data types (as strings).
        data (pd.DataFrame): The DataFrame containing the data to verify.
    
    Returns:
        bool: True if all column types match the expected types; False if any mismatch is found.
    """
    for col in columns_expected_type:
        if col not in data.columns:
            raise KeyError(f"Column '{col}' does not exist in the DataFrame.")

    columns_types = {col: str(data[col].dtype) for col in data.columns}

    tag_dtypes = True

    for col in set(columns_expected_type.keys()).union(columns_types.keys()):
        expected = columns_expected_type.get(col)
        obtained = columns_types.get(col)
        if expected != obtained:
            tag_dtypes = False
            break

    return tag_dtypes


def detect_radiation(df: pd.DataFrame, config_path: str = "configuration.ini") -> pd.DataFrame:
    """
    Detects nighttime radiation inconsistencies in a DataFrame.

    Parameters:
        df (pd.DataFrame): DataFrame with
            - a naive DatetimeIndex representing local time.
            - una o más de las columnas de radiación renombradas según la
              configuración.
        config_path (str): Path to the configuration INI file
            containing [settings] with latitude, longitude, and tz name.

    Returns:
        pd.DataFrame: A copy of the original DataFrame with two additional columns:
            - solar_altitude (float): apparent solar elevation in degrees.
            - radiation_ok (bool): True if no positive radiation values occur
              when solar_altitude ≤ 0; False otherwise.
    """
    vars_dict, lat, lon, gmt, name = load_settings(config_path)
    vars_list = list(vars_dict.values())

    # 1) generar tz a partir de gmt
    inv = -gmt
    sign = "+" if inv >= 0 else "-"
    tz = f"Etc/GMT{sign}{abs(inv)}"

    # 2) localizar el índice
    if df.index.tz is None:
        df = df.tz_localize(tz)
    else:
        df = df.tz_convert(tz)

    # 3) crear objeto Location correctamente
    loc = pvlib.location.Location(latitude=lat,
                                  longitude=lon,
                                  tz=tz)

    # 4) calcular posición solar
    solpos = loc.get_solarposition(times=df.index, method="nrel_numpy")
    df["solar_altitude"] = solpos["apparent_elevation"].values

    # 5) detectar columnas de radiación
    rad_cols = [c for c in vars_list if c in df.columns]
    if not rad_cols:
        raise KeyError("No se encontraron columnas de radiación")

    # 6) marcar inconsistencias
    has_rad = df[rad_cols].gt(0).any(axis=1)
    night   = df["solar_altitude"] <= 0
    df["radiation"] = ~(night & has_rad)

    return df


def compare(path, extension):
    """
    Reads all files with a specific extension in the given directory,
    and compares the columns of each file with those of the first file read, which is used as a reference.
    
    Args:
        path (str): Path to the directory containing the CSV files.
        extension (str): Extension of the files to read (e.g., 'csv').
    
    Returns:
        None: The function prints the results of the column comparison to the console.
    """
    # Obtiene todos los archivos con la extensión indicada en el directorio especificado
    files = glob.glob(f'{path}/*.{extension}')
    
    # Diccionario para almacenar columnas de cada archivo
    file_columns = {}

    for file in files:
        # Si el nombre del archivo contiene "2022" o "2023", se lee sin skiprows
        if "2022" in file or "2023" in file:
            df = pd.read_csv(file, encoding='ANSI', index_col=0, parse_dates=True, low_memory=False)
        else:
            df = pd.read_csv(file, encoding='ANSI', skiprows=[0, 2, 3],
                             index_col=0, parse_dates=True, dayfirst=True, low_memory=False)
        
        # Almacena las columnas del DataFrame
        file_columns[file] = set(df.columns)
    
    # Compara columnas entre archivos usando el primero como referencia
    reference_columns = None
    for file, columns in file_columns.items():
        if reference_columns is None:
            reference_columns = columns
            print(f"\n{file} se usa como referencia con columnas: \n{columns}")
        else:
            # Calcula las columnas comunes y las diferencias
            common = reference_columns.intersection(columns)
            missing = reference_columns.difference(columns)  # Columnas que faltan en el archivo actual
            extra = columns.difference(reference_columns)    # Columnas que tiene el archivo actual de más

            print(f"\nComparación para {file}:")
            print(f"Columnas comunes: {common}")
            print(f"Columnas faltantes (en referencia): {missing}")
            print(f"Columnas extra (en archivo): {extra}")

            if columns == reference_columns:
                print(f"{file} coincide con la referencia.")
            else:
                print(f"{file} no coincide con la referencia.")