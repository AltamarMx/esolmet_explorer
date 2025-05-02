from shiny import App, ui, render
import shinyswatch  
from components.explorador import panel_explorador, panel_estadistica
from components.panels import panel_documentacion, panel_trayectoriasolar, panel_fotovoltaica, panel_eolica, panel_confort
from utils.data_processing import load_esolmet_data
from utils.graficadores import graficado_Is_matplotlib
#import plotly.express as px

#No voy a usar plotly por el momento hasta no tener idea de los datos
# Agregue una linea nueva

esolmet = load_esolmet_data()

app_ui = ui.page_fluid(
    ui.navset_card_tab(
        ui.nav_panel(
            "ESOLMET",
            ui.navset_card_tab(
                panel_explorador(),
                panel_estadistica(),
                id="esolmet_subtabs"
            )
        ),
        ui.nav_panel(
            'HERRAMIENTAS',
            ui.navset_card_tab(
                panel_trayectoriasolar(),
                panel_fotovoltaica(),
                panel_eolica(),
                panel_confort(),
                id="herramientas"
            )
        ),
    ),
    theme=shinyswatch.theme.spacelab
)


def server(input, output, session):

    @render.plot(alt='Irradiancia')
    def plot_matplotlib():
        return graficado_Is_matplotlib(esolmet, input.fechas())


app = App(app_ui, server)
