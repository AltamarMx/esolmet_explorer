#%%
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pvlib import solarposition
import pytz
from datetime import datetime

#%%
def equation_of_time(times):
    # Aproximación empírica
    b = 2 * np.pi * (times.dayofyear - 81) / 364
    eot = 9.87 * np.sin(2 * b) - 7.53 * np.cos(b) - 1.5 * np.sin(b)
    return pd.Series(eot, index=times, name="equation_of_time")


def obtener_zonas_horarias_gmt():
    import pytz
    from datetime import datetime

    zonas = {}
    for zona in pytz.all_timezones:
        try:
            ahora = datetime.now(pytz.timezone(zona))
            offset = ahora.strftime('%z')  # Ej: "-0600"
            offset_formateado = f"{offset[:3]}:{offset[3:]}"  # -> "-06:00"
            zonas[zona] = f"{zona} (GMT{offset_formateado})"
        except Exception:
            continue  # Si alguna zona lanza error, la ignoramos

    return zonas





# Calcula la posición solar, con opción de usar horario solar verdadero
def calcular_posicion_solar(lat, lon, tz='America/Mexico_City', usar_hora_solar=False):
    times = pd.date_range('2025-01-01 00:00:00', '2026-01-01', freq='h', tz=tz)
    solpos = solarposition.get_solarposition(times, lat, lon)
    solpos = solpos.loc[solpos['apparent_elevation'] > 0, :]

    if usar_hora_solar:
        eot = equation_of_time(times)
        long_std = round(lon / 15) * 15  # Meridiano del huso horario
        correccion_long = 4 * (long_std - lon)
        hora_civil = times.hour + times.minute / 60 + times.second / 3600
        hora_solar = hora_civil + (eot + correccion_long) / 60
        datetime_solar = times + pd.to_timedelta((eot + correccion_long), unit='m')
        solpos['hora_solar_verdadera'] = hora_solar
        solpos['datetime_solar'] = datetime_solar
    return solpos.round(2)

#%%
# Gráfica cartesiana (elevación vs azimut)
def figura_cartesiana(solpos, lat, lon, tz='America/Mexico_City', usar_hora_solar=False):
    # indice = solpos['datetime_solar'] if usar_hora_solar else solpos.index
    if usar_hora_solar:
        indice = pd.DatetimeIndex(solpos['datetime_solar'])
    else:
        indice = solpos.index

    horas = indice.hour

    fig = go.Figure(data=go.Scatter(
        x=solpos['azimuth'],
        y=solpos['apparent_elevation'],
        mode='markers',
        marker=dict(
            size=2,
            color=indice.dayofyear,
            colorscale='Viridis',
            showscale=False
        ),
        text=[f"{t.strftime('%Y-%m-%d %H:%M')} {'(solar)' if usar_hora_solar else '(civil)'}" for t in indice],
        hovertemplate="%{text}<extra></extra>",
        name='Posición solar'
    ))

    for hour in np.unique(horas):
        subset = solpos[horas == hour]
        if not subset.empty:
            pos = subset.loc[subset['apparent_elevation'].idxmax()]
            fig.add_trace(go.Scatter(
                x=[pos['azimuth']],
                y=[pos['apparent_elevation']],
                text=[str(hour)],
                mode='text',
                showlegend=False
            ))

    for date_str in ['2025-03-21', '2025-06-21', '2025-12-21']:
        date = pd.to_datetime(date_str)
        times = pd.date_range(date, date + pd.Timedelta('24h'), freq='5min', tz=tz)
        sol_curve = solarposition.get_solarposition(times, lat, lon)
        sol_curve = sol_curve[sol_curve['apparent_elevation'] > 0]

        fig.add_trace(go.Scatter(
            x=sol_curve['azimuth'],
            y=sol_curve['apparent_elevation'],
            mode='lines',
            name=date_str
        ))

    fig.update_layout(
        width=1000,
        height=700,
        title='Posición Solar (Elevación vs Azimut)',
        xaxis_title='Azimutal (grados)',
        yaxis_title='Elevación solar (grados)',
        legend=dict(
            title='Curvas por fecha',
            orientation='h',
            yanchor='bottom',
            y=-0.3,
            xanchor='center',
            x=0.5
        ),
        template='plotly_white'
    )

    return fig

#%%
# Gráfica estereográfica (zenit vs azimut en coordenadas polares)
def figura_estereografica(solpos, lat, lon, tz='America/Mexico_City', usar_hora_solar=False):
    if usar_hora_solar:
        indice=pd.DatetimeIndex(solpos['datetime_solar'])
    else:
        indice=solpos.index
    
    
    # indice = solpos['datetime_solar'] if usar_hora_solar else solpos.index
    azimuth_rad = np.radians(solpos.azimuth)
    zenith = solpos.apparent_zenith

    scatter = go.Scatterpolar(
        r=zenith,
        theta=np.degrees(azimuth_rad),
        mode='markers',
        marker=dict(
            size=3,
            color=indice.dayofyear,
            colorscale='Viridis',
            showscale=False
        ),
        text=[
            f"{t.strftime('%Y-%m-%d %H:%M')} {'(solar)' if usar_hora_solar else '(civil)'}, "
            f"Azimut: {az:.1f}°, Cénit: {ze:.1f}°"
            for t, az, ze in zip(indice, solpos.azimuth, solpos.apparent_zenith)
        ],
        hovertemplate="%{text}<extra></extra>",
        name='Posición solar horaria'
    )

    lines = []
    for date in pd.to_datetime(['2025-03-21', '2025-06-21', '2025-12-21']):
        times_day = pd.date_range(date, date + pd.Timedelta('24h'), freq='5min', tz=tz)
        solpos_day = solarposition.get_solarposition(times_day, lat, lon)
        solpos_day = solpos_day[solpos_day['apparent_elevation'] > 0]

        lines.append(go.Scatterpolar(
            r=solpos_day.apparent_zenith,
            theta=solpos_day.azimuth,
            mode='lines',
            name=date.strftime('%Y-%m-%d')
        ))

    fig = go.Figure(data=[scatter] + lines)


    horas = indice.hour
    for hour in np.unique(horas):
        subset = solpos[horas == hour]
        if not subset.empty:
            pos = subset.loc[subset['apparent_elevation'].idxmax()]
            fig.add_trace(go.Scatterpolar(
                r=[pos['apparent_zenith']-5],
                theta=[pos['azimuth']],
                text=[str(hour)],
                mode='text',
                textfont=dict(size=12,
                              family='Arial Black'),
                showlegend=False
            ))



    fig.update_layout(
        width=1000,
        height=700,
        title='Posición solar en coordenadas polares',
        legend=dict(
            title='Curvas por fecha',
            orientation='h',
            yanchor='bottom',
            y=-0.3,
            xanchor='center',
            x=0.5
        ),
        polar=dict(
            angularaxis=dict(
                direction="clockwise",
                rotation=90,
                tickmode='array',
                tickvals=[0, 90, 180, 270],
                ticktext=['N', 'E', 'S', 'O']
            ),
            radialaxis=dict(
                angle=0,
                range=[0, 90],
                tickvals=[0, 30, 60, 90],
                ticktext=['90° (cenit)', '60°', '30°', '0° (horizonte)']
            )
        ),
        showlegend=True
    )

    return fig
