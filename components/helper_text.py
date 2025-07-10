from shiny.ui import modal_show, modal, modal_button
from htmltools import TagList, tags


# Función para mostrar el modal de documentación
def info_modal():
    modal_show(
        modal(
            # Título
            tags.strong(tags.h3("Documentación de ESOLMET Explorer")),
            # Descripción general
            tags.p(
                "Esta aplicación web permite cargar, validar, visualizar y procesar archivos CSV con datos de ESOLMET. "
            ),

            # guía rápida de uso
            tags.h4("Guía rápida para usar la app"),
            tags.ol(
                tags.li(
                    tags.strong("Seleccionar archivo CSV:"),
                    tags.p(
                        "En el panel \"Paso 1\", haz clic en \"Selecciona el archivo CSV\" para cargar datos desde tu computadora. "
                        "El sistema identificará automáticamente el encoding y limpiará el archivo."
                    )
                ),
                tags.li(
                    tags.strong("Explorar columnas y tipos:"),
                    tags.p(
                        "Una vez cargado el archivo, en Paso 1 se mostrará la tabla de columnas con su tipo de dato detectado. "
                        "Verifica que corresponda a lo esperado (float)."
                    )
                ),
                tags.li(
                    tags.strong("Visualizar gráficos interactivos:"),
                    tags.p(
                        "En Paso 1, en la sección de gráfico, podrás ver cada variable como puntos interactivos. "
                        "Haz zoom y desplázate para explorar rango de fechas y valores."
                    )
                ),
                tags.li(
                    tags.strong("Revisar pruebas de integridad:"),
                    tags.p(
                        "En Paso 1 se despliega una tabla con íconos que indican: si el archivo es CSV, codificación UTF-8, "
                        "sin duplicados, sin valores NaT y si los tipos de columnas coinciden con lo esperado (float)."
                    ),
                    tags.ul(
                        tags.li("Extensión .csv correcta."),
                        tags.li("Codificación UTF-8 válida."),
                        tags.li("Sin valores NaT en columnas de fecha."),
                        tags.li("Sin duplicados en filas."),
                        tags.li("Columnas con tipo float cuando corresponde.")
                    )
                ),
                tags.li(
                    tags.strong("Analizar radiación durante la noche:"),
                    tags.p(
                        "En el panel \"Paso 2\", la app extrae registros de radiación cuando la altitud solar ≤ 0, "
                        "mostrando únicamente las columnas dni, ghi, dhi, uv y la altitud solar."
                    )
                ),
                tags.li(
                    tags.strong("Exportar datos a DuckDB:"),
                    tags.p(
                        "En el panel \"Paso 3\", haz clic en \"Cargar en base de datos\" para transformar los datos a formato largo "
                        "y almacenarlos en una tabla 'lecturas'."
                    )
                ),
                tags.li(
                    tags.strong("Eliminar base de datos existente:"),
                    tags.p(
                        "En el mismo panel, haz clic en \"Eliminar base de datos\" para borrar el archivo 'esolmet.db'."
                    )
                )
            ),
            fade=False,
            size="xl",
            easy_close=True,
            footer=modal_button("Cerrar")
        )
    )
