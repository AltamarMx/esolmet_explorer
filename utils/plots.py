import pandas as pd
import plotly.graph_objects as go
from utils.data_processing import load_csv, radiacion

def graficado_plotly(path_archivo: str, columnas: list[str] = None) -> go.Figure:
    """
    - carga el CSV con load_csv (que devuelve un DataFrame con TIMESTAMP como índice datetime)
    - convierte el índice TIMESTAMP en columna de texto con formato "YYYY-MM-DD HH:MM"
    - selecciona las variables a graficar (todas las columnas numéricas, salvo TIMESTAMP_str)
    - construye un scattergl para cada variable
    """

    # 1. cargar datos (load_csv ya deja TIMESTAMP como índice datetime)
    df = load_csv(path_archivo)

    # 2. resetear índice para que TIMESTAMP vuelva a ser columna y formatearla
    df = df.reset_index()  # ahora 'TIMESTAMP' es columna de tipo datetime
    df["TIMESTAMP"] = df["TIMESTAMP"].dt.strftime("%Y-%m-%d %H:%M")

    # 3. determinar qué variables graficar (descartar la columna TIMESTAMP)
    variables = columnas or [c for c in df.columns if c != "TIMESTAMP"]

    # 4. construir figura
    fig = go.Figure()
    for var in variables:
        if var not in df.columns:
            # si el usuario pidió una columna que no existe, la omitimos
            continue
        mask = df[var].notna()
        fig.add_trace(
            go.Scattergl(
                x = df.loc[mask, "TIMESTAMP"],
                y = df.loc[mask, var],
                mode = "markers",
                name = var,
                marker = dict(size=5),
            )
        )

    # 5. configurar layout
    fig.update_layout(
        hovermode = "x unified",
        showlegend = True,
        xaxis_title = "TIMESTAMP",
        yaxis_title = "Valores",
    )
    fig.update_xaxes(
        showgrid = True,
        tickformat = "%Y-%m-%d %H:%M",
        tickmode = "auto",
    )
    fig.update_yaxes(showgrid = True)

    return fig


def graficado_radiacion(path_archivo: str, rad_columns: list[str] = None) -> go.Figure:
    # 1. cargar datos y calcular radiación nocturna
    df = load_csv(path_archivo)
    df_rad = radiacion(df, rad_columns)

    # 2. preparar TIMESTAMP para graficar
    df_plot = df_rad.reset_index().rename(columns={'index': 'TIMESTAMP'})
    df_plot['TIMESTAMP'] = pd.to_datetime(df_plot['TIMESTAMP'], errors='coerce')
    df_plot = df_plot.dropna(subset=['TIMESTAMP'])
    df_plot['TIMESTAMP'] = df_plot['TIMESTAMP'].dt.strftime('%Y-%m-%d %H:%M')

    # 3. determinar columnas a graficar (excluyendo altura_solar)
    cols_to_plot = [col for col in df_plot.columns if col not in ['TIMESTAMP', 'altura_solar']]

    # 4. construir figura
    fig = go.Figure()
    for col in cols_to_plot:
        fig.add_trace(
            go.Scattergl(
                x=df_plot['TIMESTAMP'],
                y=df_plot[col],
                mode='markers',
                name=col,
                marker=dict(size=5),
            )
        )

    # 5. configurar layout
    fig.update_layout(
        showlegend=True,
        xaxis_title='TIMESTAMP',
        yaxis_title='Valores',
    )
    fig.update_xaxes(showgrid=True, tickformat='%Y-%m-%d %H:%M', tickmode='auto')
    fig.update_yaxes(showgrid=True)

    return fig


# def graficado_nulos(df):
#     na_counts = df.isna().sum()
#     cols_with_na = na_counts[na_counts > 0].index.tolist()
#     if not cols_with_na:
#         fig = plt.figure(figsize=(8, 4))
#         fig.suptitle("Sin valores nulos")
#         return fig

#     fig, ax = plt.subplots(
#         figsize=(
#             max(14, 0.6 * len(cols_with_na)),
#             8
#         )
#     )
#     msno.bar(
#         df[cols_with_na],
#         ax=ax,
#         fontsize=10,
#         sort="descending"
#     )

#     plt.setp(ax.get_xticklabels(), ha="right")
#     ax.grid(axis="y", alpha=0.3)
#     ax.set_ylabel("Proporción")

#     if len(fig.axes) > 1:
#         fig.axes[1].set_ylabel("Conteo")

#     return fig
