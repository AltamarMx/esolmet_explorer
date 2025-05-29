import configparser
import ast

def load_settings(path: str = "configuration.ini"):
    """
    Lee el archivo INI y devuelve:
      - variables: list[str]
      - latitude: float
      - longitude: float
      - gmt: int
      - name: str
    """
    config = configparser.ConfigParser()
    config.read(path)

    sec = config["settings"]
    variables = ast.literal_eval(sec.get("variables", "[]"))
    latitude  = sec.getfloat("latitude", fallback=0.0)
    longitude = sec.getfloat("longitude", fallback=0.0)
    gmt       = sec.getint("gmt", fallback=0)
    name      = sec.get("name", fallback="")
    alias_str = sec.get("alias", "{}")
    alias     = ast.literal_eval(alias_str)

    return variables, latitude, longitude, gmt, name, alias

