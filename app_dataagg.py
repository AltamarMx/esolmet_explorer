import os
import duckdb

from shiny import App, Inputs, Outputs, Session, render, ui, req, reactive
from shinywidgets import render_plotly
import faicons as fa

from utils.data_processing import load_csv, run_tests, export_data, radiacion
from utils.plots import graficado_plotly, graficado_radiacion
from components.panels import panel_subir_archivo, panel_pruebas_archivo, panel_cargar_datos
from components.helper_text import info_modal


# ui definition
app_ui = ui.page_fluid(
    ui.page_navbar(
        ui.nav_spacer(),
        panel_subir_archivo(),
        panel_pruebas_archivo(),
        panel_cargar_datos(),
        ui.nav_control(
            ui.input_action_button(
                id="info_icon",
                label=None,
                icon=fa.icon_svg("circle-info"),
                class_=(
                    "btn "
                    "d-flex align-items-center "
                    "border-0 p-3 "
                ),
                title="Documentación"
            )
        ),
        title="ESOLMET Explorer"
    )
)


# server logic
def server(input: Inputs, output: Outputs, session: Session):
    # shared reactive storage
    rv_loaded = reactive.Value(None)
    rv_tests  = reactive.Value(None)
    rv_plotly = reactive.Value(None)
    rv_rad_plot = reactive.Value(None)
    # rv_missing = reactive.Value(None)
    rv_rad     = reactive.Value(None)
    # rv_nans    = reactive.Value(None)
    # rv_nats    = reactive.Value(None)
    rv_types   = reactive.Value(None)

    @reactive.Effect
    @reactive.event(input.info_icon)
    def _():
        info_modal()

    # full pipeline on file upload
    @output
    @render.ui
    @reactive.event(input.archivo)
    async def upload_status():
        archivo = req(input.archivo())[0]["datapath"]
        total_steps = 5

        with ui.Progress(min=0, max=total_steps) as p:
            p.set(1, message="1/4 leyendo y formateando el archivo…")
            df = load_csv(archivo)
            rv_loaded.set(df)

            p.set(2, message="2/4 ejecutando pruebas de integridad…")
            tests = run_tests(df, archivo)
            rv_tests.set(tests)

            p.set(3, message="3/4 generando gráficos interactivos…")
            rv_plotly.set(graficado_plotly(archivo))
            rv_rad_plot.set(graficado_radiacion(archivo))

            p.set(4, message="4/5 analizando tipos de columnas…")
            rv_types.set(
                df.dtypes
                    .rename_axis("Columna")
                    .reset_index(name="Tipo")
            )

            p.set(5, message="5/5 calculando radiación solar…")
            df_rad = radiacion(df)
            df_rad.index = df_rad.index.tz_localize(None)
            rv_rad.set(
                df_rad.reset_index()
                    .sort_values("TIMESTAMP")
                    .rename(columns={"index": "TIMESTAMP"})
            )

            # p.set(6, message="6/7 localizando NaN y NaT…")
            # rv_nans.set(_df_nans(df_fmt, archivo))
            # rv_nats.set(_df_nats(df_fmt))

    # load into DuckDB
    @output
    @render.ui
    @reactive.event(input.btn_load)
    async def load_status():
        df_load = export_data(req(input.archivo())[0]["datapath"])
        with ui.Progress(min=1, max=len(df_load)) as p:
            p.set(message="Iniciando carga…")
            con = duckdb.connect('esolmet.db')
            con.execute("""
                CREATE TABLE IF NOT EXISTS lecturas (
                    fecha TIMESTAMP,
                    variable VARCHAR,
                    valor DOUBLE,
                    PRIMARY KEY (fecha, variable)
                );
            """)
            con.execute("BEGIN TRANSACTION;")
            chunk = 5000
            for i in range(0, len(df_load), chunk):
                c = df_load.iloc[i : i + chunk]
                con.register('tmp', c)
                con.execute("INSERT INTO lecturas SELECT * FROM tmp;")
                p.set(i + chunk, message=f"Cargando filas {i+1}-{min(i+chunk, len(df_load))}…")
            con.execute("COMMIT;")
            con.close()
        return ui.tags.div("Carga completada", class_="text-success")

    # delete DB file
    @output
    @render.ui
    @reactive.event(input.btn_delete)
    async def delete_status():
        db_path = "esolmet.db"
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
                return ui.tags.div("Base de datos eliminada", class_="text-danger")
            except PermissionError:
                return ui.tags.div(
                    "No se puede eliminar: cierre las conexiones abiertas o reinicie la app.",
                    class_="text-danger"
                )
            except Exception as e:
                return ui.tags.div(f"Error al eliminar la base de datos: {e}", class_="text-danger")
        else:
            return ui.tags.div("No se encontró la base de datos.", class_="text-warning")

    # render outputs
    @render_plotly
    def plot_plotly():
        return rv_plotly.get()
    
    @render_plotly
    def plot_radiacion():
        return rv_rad_plot.get()

    # @render.plot
    # def plot_missing():
    #     return rv_missing.get()

    @render.data_frame
    def df_types():
        return rv_types.get()

    @render.data_frame
    def df_radiacion():
        return rv_rad.get()

    # @render.data_frame
    # def df_nans():
    #     return rv_nans.get()

    # @render.data_frame
    # def df_nats():
    #     return rv_nats.get()

    @render.ui
    def table_tests():
        tests = rv_tests.get() or {}
        filas = []
        for prueba, ok in tests.items():
            icon = "circle-check" if ok else "circle-exclamation"
            color = "text-success" if ok else "text-danger"
            filas.append(
                ui.tags.tr(
                    ui.tags.td(prueba, style="text-align:left;"),
                    ui.tags.td(fa.icon_svg(icon).add_class(color), style="text-align:center;"),
                )
            )
        return ui.tags.table(
            ui.tags.thead(
                ui.tags.tr(
                    ui.tags.th("Prueba", style="text-align:left;"),
                    ui.tags.th("Estado", style="text-align:center;"),
                )
            ),
            ui.tags.tbody(*filas),
            class_="table table-sm table-striped w-auto",
        )

# instantiate app
app = App(app_ui, server)
