# -*- coding: utf-8 -*-
"""
Created on Thu Oct 27 14:53:14 2022

@author: mritchey
"""

# -*- coding: utf-8 -*-
"""
Created on Fri Oct 14 10:35:25 2022

@author: mritchey
"""

import streamlit as st
from streamlit_folium import st_folium
import pandas as pd
import folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import datetime
import urllib.request 
import rioxarray
import rasterio
import numpy as np
import branca.colormap as cm
from matplotlib import colors as colors
import os
import glob

try:
    for i in glob.glob('*.grib2'): os.remove(i)
except:
    pass

address = st.sidebar.text_input("Address", "123 Main Street, Columbus, OH 43215")
d = st.sidebar.date_input("Date",  pd.Timestamp(2022,9,28)).strftime('%Y%m%d')

time = st.sidebar.selectbox('Time:',('12 AM','6 AM', '12 PM', '6 PM',))
type_wind = st.sidebar.selectbox('Type:',('Gust','Wind'))

if time[-2:]=='PM' and int(time[:2].strip())<12:
   t= datetime.time(int(time[:2].strip())+12, 00).strftime('%H')+'00'
else:
   t= datetime.time(int(time[:2].strip()), 00).strftime('%H')+'00'

year,month,day=d[:4],d[4:6],d[6:8]

url=f'https://mtarchive.geol.iastate.edu/{year}/{month}/{day}/grib2/ncep/RTMA/{d}{t}_{type_wind.upper()}.grib2'
file=urllib.request.urlretrieve(url, f'{d}{t}{type_wind}.grib2')[0]

geolocator = Nominatim(user_agent="GTA Lookup")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

location = geolocator.geocode(address)

lat,lon=location.latitude,location.longitude
map_data = pd.DataFrame({'lat': [lat], 'lon': [lon]})

rds = rioxarray.open_rasterio(file)
projected = rds.rio.reproject("EPSG:4326")
wind_mph=projected.sel(x=lon, y=lat, method="nearest").values*2.23694

st.write(f"{type_wind.title()} Speed: {wind_mph[0].round(2)} MPH")

def mapvalue2color(value, cmap): 

    if np.isnan(value):
        return (1, 0, 0, 0)
    else:
        return colors.to_rgba(cmap(value), 0.7)  
   
affine=projected.rio.transform()

rows,columns=rasterio.transform.rowcol(affine, lon, lat)

size=40

projected2=projected[0,rows-size:rows+size,columns-size:columns+size]

img=projected2.values*2.23694
boundary=projected2.rio.bounds()
left,bottom,right,top=boundary

img[img<0.0] = np.nan

clat = (bottom + top)/2
clon = (left + right)/2

vmin = np.floor(np.nanmin(img))
vmax = np.ceil(np.nanmax(img))

#colormap = cm.linear.RdBu_11.scale(vmin, vmax)

colormap = cm.LinearColormap(colors=['blue','lightblue','red'], vmin=vmin,vmax=vmax)

m = folium.Map(location=[lat, lon],  zoom_start=9,height=500)

folium.Marker(
      location=[lat, lon],
      popup=f"{wind_mph[0].round(2)} MPH").add_to(m)
 
folium.raster_layers.ImageOverlay(
    image=img,
    name='Wind Speed Map',
    opacity=.8,
    bounds= [[bottom,left], [top, right]],
    colormap= lambda value: mapvalue2color(value, colormap)
).add_to(m)


folium.LayerControl().add_to(m)
colormap.caption = 'Wind Speed: MPH'
m.add_child(colormap)

st_folium(m,height=500)

st.markdown(""" <style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style> """, unsafe_allow_html=True)
