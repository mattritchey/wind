# -*- coding: utf-8 -*-
"""
Created on Fri Oct 14 10:35:25 2022

@author: mritchey
"""
#streamlit run "C:\Users\mritchey\.spyder-py3\Python Scripts\streamlit 2.py"
import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import datetime
import urllib.request 
import rioxarray

address = st.sidebar.text_input("Adress", "123 Main Street, Columbus, OH 43215")
d = st.sidebar.date_input("Date",  pd.Timestamp(2020,10,29)).strftime('%Y%m%d')
t = st.sidebar.time_input('Time', datetime.time(10, 00)).strftime('%H')+'00'


year,month,day=d[:4],d[4:6],d[6:8]

url=f'https://mtarchive.geol.iastate.edu/{year}/{month}/{day}/grib2/ncep/RTMA/{d}{t}_GUST.grib2'
file=urllib.request.urlretrieve(url, f'{d}{t}.grib2')[0]

# street = st.sidebar.text_input("Street", "123 Main Street")
# city = st.sidebar.text_input("City", "Columbus")
# province = st.sidebar.text_input("State", "OH")
# country = st.sidebar.text_input("Country", "USA")

geolocator = Nominatim(user_agent="GTA Lookup")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
#location = geolocator.geocode(street+", "+city+", "+province+", "+country)
location = geolocator.geocode(address)

lat,lon=location.latitude,location.longitude
map_data = pd.DataFrame({'lat': [lat], 'lon': [lon]})

rds = rioxarray.open_rasterio(file)
projected = rds.rio.reproject("EPSG:4326")
wind_mph=projected.sel(x=lon, y=lat, method="nearest").values*2.23694

st.map(map_data) 
st.write(f"Wind Gust Speed: {wind_mph[0].round(2)} MPH")
