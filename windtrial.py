# -*- coding: utf-8 -*-
"""
Created on Fri Oct 14 10:35:25 2022

@author: mritchey
"""

import datetime
import glob
import os
import urllib.request
import branca.colormap as cm
import folium
import numpy as np
import pandas as pd
import plotly.express as px
import rasterio
import rioxarray
import streamlit as st
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
from joblib import Parallel, delayed
from matplotlib import colors as colors
from streamlit_folium import st_folium
from threading import Thread

def download_file_get_data(url,rows, columns):
    file = urllib.request.urlretrieve(url, url[-23:])[0]
    rds = rioxarray.open_rasterio(file)
    wind_mph = rds.rio.reproject("EPSG:4326")[0, rows, columns].values*2.23694
    time = url[-15:-11]
    return [wind_mph, time]

def threading(df_input,func_input):
    starttime=time.time()
    tasks_thread=df_input
    results_thread=[]
    def thread_func(value_input):
        response=func_input(value_input)
        results_thread.append(response)
        return True
    
    threads = []
    for i in range(len(tasks_thread)):
        process = Thread(target=thread_func, args=[tasks_thread[i]])
        process.start()
        threads.append(process)   
        
    for process in threads:
        process.join()
    print(f'Time: {str(round((time.time()-starttime)/60,5))} Minutes') 
    return results_thread

def mapvalue2color(value, cmap):
    if np.isnan(value):
        return (1, 0, 0, 0)
    else:
        return colors.to_rgba(cmap(value), 0.7)



def geocode(address):
    try:
        address2 = address.replace(' ', '+').replace(',', '%2C')
        df = pd.read_json(
            f'https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?address={address2}&benchmark=2020&format=json')
        results = df.iloc[:1, 0][0][0]['coordinates']
        lat, lon = results['y'], results['x']
    except:
        geolocator = Nominatim(user_agent="GTA Lookup")
        geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
        location = geolocator.geocode(address)
        lat, lon = location.latitude, location.longitude
    return lat, lon

@st.cache
def get_grib_data(url, d, t):
    file = urllib.request.urlretrieve(url, f'{d}{t}{type_wind}.grib2')[0]
    return file

@st.cache
def graph_entire_day(d,rows, columns):
    year, month, day = d[:4], d[4:6], d[6:8]
    times = [f'0{str(i)}'[-2:] for i in range(0, 24)]
    urls = [
        f'https://mtarchive.geol.iastate.edu/{year}/{month}/{day}/grib2/ncep/RTMA/{d}{t}00_{type_wind.upper()}.grib2' for t in times]
    
    results = Parallel(n_jobs=4)(
        delayed(download_file_get_data)(i,rows, columns) for i in urls)

    df_all = pd.DataFrame(results, columns=['MPH', 'Time'])
    df_all['MPH'] = df_all['MPH'].round(2)
    df_all['Time'] = pd.to_datetime(d+df_all['Time'], format='%Y%m%d%H%M')
    return df_all


@st.cache
def convert_df(df):
    return df.to_csv(index=0).encode('utf-8')


try:
    for i in glob.glob('*.grib2'):
        os.remove(i)
except:
    pass

st.set_page_config(layout="wide")
col1, col2 = st.columns((2))

address = st.sidebar.text_input(
    "Address", "123 Main Street, Columbus, OH 43215")
d = st.sidebar.date_input(
    "Date",  pd.Timestamp(2022, 9, 28)).strftime('%Y%m%d')

time = st.sidebar.selectbox('Time:', ('12 AM', '6 AM', '12 PM', '6 PM',))
type_wind = st.sidebar.selectbox('Type:', ('Gust', 'Wind'))
entire_day = st.sidebar.radio(
    'Graph Entire Day (Takes a Bit):', ('No', 'Yes'))

if time[-2:] == 'PM' and int(time[:2].strip()) < 12:
    t = datetime.time(int(time[:2].strip())+12, 00).strftime('%H')+'00'
elif time[-2:] == 'AM' and int(time[:2].strip()) == 12:
    t = '0000'
else:
    t = datetime.time(int(time[:2].strip()), 00).strftime('%H')+'00'

year, month, day = d[:4], d[4:6], d[6:8]

url = f'https://mtarchive.geol.iastate.edu/{year}/{month}/{day}/grib2/ncep/RTMA/{d}{t}_{type_wind.upper()}.grib2'
file = get_grib_data(url, d, t)

lat, lon = geocode(address)

rds = rioxarray.open_rasterio(file)
projected = rds.rio.reproject("EPSG:4326")
wind_mph = projected.sel(x=lon, y=lat, method="nearest").values*2.23694

affine = projected.rio.transform()

rows, columns = rasterio.transform.rowcol(affine, lon, lat)

size = 40

projected2 = projected[0, rows-size:rows+size, columns-size:columns+size]

img = projected2.values*2.23694
boundary = projected2.rio.bounds()
left, bottom, right, top = boundary

img[img < 0.0] = np.nan

clat = (bottom + top)/2
clon = (left + right)/2

vmin = np.floor(np.nanmin(img))
vmax = np.ceil(np.nanmax(img))

colormap = cm.LinearColormap(
    colors=['blue', 'lightblue', 'red'], vmin=vmin, vmax=vmax)

m = folium.Map(location=[lat, lon],  zoom_start=9, height=500)

folium.Marker(
    location=[lat, lon],
    popup=f"{wind_mph[0].round(2)} MPH").add_to(m)

folium.raster_layers.ImageOverlay(
    image=img,
    name='Wind Speed Map',
    opacity=.8,
    bounds=[[bottom, left], [top, right]],
    colormap=lambda value: mapvalue2color(value, colormap)
).add_to(m)


folium.LayerControl().add_to(m)
colormap.caption = 'Wind Speed: MPH'
m.add_child(colormap)

with col1:
    st.title('RTMA Model')
    st.write(
        f"{type_wind.title()} Speed: {wind_mph[0].round(2)} MPH at {time} UTC")
    st_folium(m, height=500)


if entire_day == 'Yes':
    df_all = graph_entire_day(d,rows, columns)
    fig = px.line(df_all, x="Time", y="MPH")
    with col2:
        st.title('Analysis')
        st.plotly_chart(fig)

        csv = convert_df(df_all)

        st.download_button(
            label="Download data as CSV",
            data=csv,
            file_name=f'{d}.csv',
            mime='text/csv')
else:
    pass

st.markdown(""" <style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style> """, unsafe_allow_html=True)
