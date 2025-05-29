import matplotlib.pyplot as plt
import duckdb 
from windrose import WindroseAxes
from matplotlib.gridspec import GridSpec

from utils.config import load_settings


variables, _, _, _, _, names = load_settings()
con = duckdb.connect('esolmet.db')

def graficado_Is_matplotlib(fechas):
    
    
    # 1) Carga y pivoteo
    query = f"""
    SELECT *
      FROM lecturas
     WHERE fecha >= TIMESTAMP '{fechas[0]}'
       AND fecha <= TIMESTAMP '{fechas[1]}'
     ORDER BY fecha
    """
    df = con.execute(query).fetchdf()
    df = df.pivot(index='fecha', columns='variable', values='valor')
    df = df.rename(columns=names)

    # 2) Identificar columnas I*
    columnas = df.columns
    Is = [col for col in columnas if col.startswith("I")]

    # 3) Figure + GridSpec
    fig = plt.figure()
    # fig.set_constrained_layout(True)

    gs  = GridSpec(nrows=4, ncols=2,
                   width_ratios=[4, 1],
                   height_ratios=[1, 1, 1, 1],
                #    wspace=0.1, hspace=0.1,
                   figure=fig)

    ax_te   = fig.add_subplot(gs[0, 0])
    ax_hr   = fig.add_subplot(gs[1, 0], sharex=ax_te)
    ax_p    = fig.add_subplot(gs[2, 0], sharex=ax_te)
    ax_is   = fig.add_subplot(gs[3, 0], sharex=ax_te)
    ax_wind = fig.add_subplot(gs[:, 1], projection='windrose')
    

    # Graficar Te
    ax_te.plot(df.index, df["Te"], label="Te",c="k",alpha=0.8)
    ax_te.set_ylabel("Te [oC]")
    ax_te.legend(loc="upper left")

    # Graficar P
    ax_p.plot(df.P, label="P",alpha=0.8)
    ax_p.set_ylabel("P [--]")
    ax_p.legend(loc="upper left")

    # Graficar Is
    for I in Is:
        ax_is.plot(df.index, df[I], label=I)
    ax_is.set_ylabel("I [W/m2]")
    ax_is.legend(loc="upper left")

    # Graficar humedad relativa hr
    ax_hr.plot(df.hr,label="HR")
    ax_hr.set_ylim(0,100)
    ax_hr.set_ylabel("HR [%]")

    # 5) Rosa de vientos
    ax_wind.bar(df["wd"], df["ws"],
                normed=True, opening=0.8,
                edgecolor="white")
    ax_wind.set_title("Rosa de Vientos")

    # 6) Formato de fecha en eje X
    fig.autofmt_xdate()

    return fig


def graficado_Todo_matplotlib():
    
    fig, ax = plt.subplots()
    columnas = esolmet.columns
    for columna in columnas:
        ax.plot(esolmet[columna],label=columna)
    # ax.set_ylabel("Irradiancia [W/m2]")
    ax.spines[["top","right"]].set_visible(False)
    ax.grid(alpha=0.2)
    ax.legend()
    return fig
