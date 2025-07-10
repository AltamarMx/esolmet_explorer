import configparser
import ast

def load_settings(path: str = "configuration.ini"):
    """
    Lee el archivo INI y devuelve:
      - variables: dict[str, str]  # {col_original: col_nuevo}
      - latitude: float
      - longitude: float
      - gmt: int
      - name: str
    """
    config = configparser.ConfigParser()
    config.read(path)

    sec = config["settings"]
    var_str   = sec.get("variables", "{}")
    variables = ast.literal_eval(var_str)
    latitude  = sec.getfloat("latitude", fallback=0.0)
    longitude = sec.getfloat("longitude", fallback=0.0)
    gmt       = sec.getint("gmt", fallback=0)
    name      = sec.get("name", fallback="")
    return variables, latitude, longitude, gmt, name
