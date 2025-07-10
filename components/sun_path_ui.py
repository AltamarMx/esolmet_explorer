from shiny import App, ui, render, reactive
from shinywidgets import output_widget, render_widget
from utils.sun_path import obtener_zonas_horarias_gmt
from utils.config import load_settings

_, latitude, longitude, gmt_default, _ = load_settings()


zonas_horarias = obtener_zonas_horarias_gmt()

sun_path_ui = ui.page_fluid(
    ui.h2("Trayectoria solar interactiva"),
    ui.layout_sidebar(
        ui.sidebar(
            ui.div(
            ui.input_numeric("lat", "Latitud:", value=latitude,update_on='blur'),
            ui.tags.small('Norte=Positivo, Sur=Negativo',style='color:gray;')),
            ui.div(
            ui.input_numeric("lon", "Longitud:", value=longitude,update_on='blur'),
            ui.tags.small('Este=Positivo, Oeste=Negativo',style='color: gray;')),
            ui.input_select("timezone", "Zona horaria:", zonas_horarias, selected="America/Mexico_City"),
            ui.input_radio_buttons("horario", "Horario:", {
                "civil": "Horario estándar (civil)",
                "solar": "Horario solar verdadero"
            }, selected="civil"),
            ui.input_radio_buttons("graficas", "Mostrar:", {
                "cartesiana": "Solo cartesiana",
                "polar": "Solo estereográfica",
                "ambas": "Ambas gráficas"
            }, selected="cartesiana"),
            ui.input_checkbox("ver_tabla_check", "Mostrar tabla de datos", False),
            ui.download_button("descargar_datos", "📥 Descargar datos")
        ),
        ui.div(
            output_widget("grafico_cartesiano"),
            output_widget("grafico_polar"),
            ui.output_ui("mostrar_tabla")
        )
    )
)