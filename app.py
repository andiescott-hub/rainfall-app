import streamlit as st
import pandas as pd
import requests
import time
from io import StringIO
from geopy.geocoders import Nominatim
from datetime import datetime, timedelta

# --- Configuration & Caching ---
API_EMAIL = "andiescott@gmail.com"  # <--- REPLACE THIS WITH YOUR REAL EMAIL

@st.cache_data
def get_silo_data(lat, lon, start_date, end_date):
    # The SILO Data Drill API requires coordinates rounded to the nearest 0.05 degrees
    lat_rounded = round(lat * 20) / 20
    lon_rounded = round(lon * 20) / 20
    
    url = "https://www.longpaddock.qld.gov.au/cgi-bin/silo/DataDrillDataset.php"
    params = {
        "start": start_date.strftime("%Y%m%d"),
        "finish": end_date.strftime("%Y%m%d"),
        "lat": lat_rounded,
        "lon": lon_rounded,
        "format": "csv",
        "username": API_EMAIL,
        "password": "apirequest",
        "comment": "R" # 'R' specifically requests Rain data
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        # SILO returns plain text CSV; we read it into a Pandas DataFrame
        df = pd.read_csv(StringIO(response.text))
        
        # Clean up the dataframe for plotting by targeting only the date column
        if 'YYYY-MM-DD' in df.columns:
            df['YYYY-MM-DD'] = pd.to_datetime(df['YYYY-MM-DD'])
            df.set_index('YYYY-MM-DD', inplace=True)
            
        return df
    else:
        st.error(f"Error fetching data from SILO: HTTP {response.status_code}")
        return None

# --- Main Interface ---

st.title("Historical Australian Rainfall Viewer")
st.markdown("Enter a location to visualize historical daily rainfall data interpolated from the Bureau of Meteorology.")

# --- User Inputs ---
with st.sidebar:
    st.header("Search Parameters")
    # Defaulting to Kilsyth, Victoria
    location_input = st.text_input("Location (e.g., 'Mildura, Victoria')", "Kilsyth, Victoria")
    
    # Quick date filters (Now with Last 7 Days!)
    date_preset = st.selectbox(
        "Date Range", 
        ["Last 7 Days", "Last 30 Days", "Year to Date", "Last 12 Months", "Custom"]
    )
    
    today = datetime.today()
    
    # Logic to calculate the dates based on the dropdown
    if date_preset == "Last 7 Days":
        start_date = today - timedelta(days=7)
        end_date = today
    elif date_preset == "Last 30 Days":
        start_date = today - timedelta(days=30)
        end_date = today
    elif date_preset == "Year to Date":
        start_date = datetime(today.year, 1, 1)
        end_date = today
    elif date_preset == "Last 12 Months":
        start_date = today - timedelta(days=365)
        end_date = today
    else:
        # If "Custom", show the original date pickers
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", datetime(2020, 1, 1))
        with col2:
            end_date = st.date_input("End Date", today)
            
    submit_button = st.button("Fetch Rainfall Data")

# --- Execution Logic ---
if submit_button:
    if start_date >= end_date:
        st.error("Start date must be before the end date.")
    else:
        # 1. Geocoding Phase
        with st.spinner("Resolving location coordinates..."):
            geolocator = Nominatim(user_agent="historical_rainfall_app")
            time.sleep(1) 
            location = geolocator.geocode(location_input)
            
        if location is None:
            st.error("Could not find coordinates for that location. Try being more specific.")
        else:
            st.success(f"Location found: {location.address} (Lat: {location.latitude:.2f}, Lon: {location.longitude:.2f})")
            
            # 2. Data Retrieval Phase
            with st.spinner("Downloading climate data from SILO..."):
                df = get_silo_data(location.latitude, location.longitude, start_date, end_date)
                
            # 3. Visualization Phase
            if df is not None and not df.empty:
                # Check the most common names SILO uses for rainfall
                if 'daily_rain' in df.columns:
                    rain_col = 'daily_rain'
                elif 'Rain' in df.columns:
                    rain_col = 'Rain'
                else:
                    st.error(f"Oops! Couldn't find the rainfall column. The columns SILO gave us are: {', '.join(df.columns)}")
                    st.stop()
                
                st.subheader(f"Daily Rainfall Accumulation ({date_preset})")
                
                # Render the chart
                st.line_chart(df[[rain_col]])
                
                # Show aggregated metrics
                total_rain = df[rain_col].sum()
                max_rain = df[rain_col].max()
                
                m1, m2 = st.columns(2)
                m1.metric("Total Rainfall in Period", f"{total_rain:.1f} mm")
                m2.metric("Maximum Single-Day Rainfall", f"{max_rain:.1f} mm")
                
                with st.expander("View Raw Data"):
                    st.dataframe(df)