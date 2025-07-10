from shiny import reactive, render, ui
from shinywidgets import render_widget
from utils.sun_path import calcular_posicion_solar, figura_cartesiana, figura_estereografica
import io 


def sun_path_server(input, output, session):
    @reactive.calc
    def datos():
        usar_hora_solar = input.horario() == "solar"
        return calcular_posicion_solar(input.lat(), input.lon(), tz=input.timezone(), usar_hora_solar=usar_hora_solar)

    @output
    @render_widget
    def grafico_cartesiano():
        if input.graficas() in ("cartesiana", "ambas"):
            return figura_cartesiana(datos(), input.lat(), input.lon(), tz=input.timezone(), usar_hora_solar=input.horario() == "solar")

    @output
    @render_widget
    def grafico_polar():
        if input.graficas() in ("polar", "ambas"):
            return figura_estereografica(datos(), input.lat(), input.lon(), tz=input.timezone(), usar_hora_solar=input.horario() == "solar")

    @output
    @render.ui
    def mostrar_tabla():
        if input.ver_tabla_check():
            return ui.div(
                ui.h4("Datos solares"),
                ui.output_data_frame("tabla")
            )
        return None

    @output
    @render.data_frame
    def tabla():
        return datos().reset_index().head(100)

    @output
    @render.download
    def descargar_datos():
        def writer():
            buffer=io.StringIO()
            datos().head(100).to_csv(buffer,index=False)
            contenido = buffer.getvalue()
            buffer.close()

            yield contenido.encode('utf-8')
        return writer
    
