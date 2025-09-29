# pages/3_weather_en.py – Standalone English Weather Page (Base Structure)
import streamlit as st
import os
import requests
from dotenv import load_dotenv

load_dotenv()  # Load API keys

def get_weather(location, api_key):
    """Fetch weather from OpenWeatherMap API"""
    if not location:
        return None
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        'q': location + ',IN',  # Indian city
        'appid': api_key,
        'units': 'metric',  # Celsius
        'lang': 'en'  # English labels
    }
    try:
        response = requests.get(base_url, params=params)
        if response.status_code == 200:
            data = response.json()
            return {
                'city': data['name'],
                'temp': data['main']['temp'],
                'feels_like': data['main']['feels_like'],
                'humidity': data['main']['humidity'],
                'description': data['weather'][0]['description'],
                'icon': data['weather'][0]['icon'],
                'wind_speed': data['wind']['speed']
            }
        else:
            st.error(f"API Error: {response.status_code} - Location not found?")
            return None
    except Exception as e:
        st.error(f"Weather fetch error: {str(e)}")
        return None

st.set_page_config(page_title="Krishi Sakhi - Weather (English)", page_icon="☀️")

st.title("☀️ Krishi Sakhi - Weather")
st.write("Get local weather for farming decisions. Uses your profile location.")

# Sidebar (Mirrors English Profile Page: Safe User Display)
st.sidebar.header("👤 User")
if 'user' in st.session_state and st.session_state.user is not None:
    user = st.session_state['user']
    st.sidebar.write(f"Name: {user.get('name', 'Unknown')}")
    st.sidebar.write(f"Crop: {user.get('crop', 'General')}")
    st.sidebar.write(f"Location: {user.get('location', 'N/A')}")  # Key for weather
else:
    st.sidebar.info("👋 Welcome! Save profile (in English/Malayalam page) for location-based weather.")

# Weather Section (Safe Profile Check)
api_key = os.getenv('OPENWEATHER_API_KEY')
if not api_key:
    st.error("OPENWEATHER_API_KEY missing in .env file. Get it from openweathermap.org.")
    st.stop()

location = None
if 'user' in st.session_state and st.session_state.user is not None:
    location = st.session_state.user.get('location', None)
else:
    st.warning("⚠️ Complete profile (English/Malayalam page) for personalized weather.")
    location = st.text_input("Enter Location (e.g., Thrissur)", placeholder="Thrissur")

if location:
    with st.spinner("Loading weather..."):
        weather_data = get_weather(location, api_key)
        if weather_data:
            st.success(f"**Location:** {weather_data['city']}, {location}")
            
            # Current Weather Display (Columns - Mirrors Profile)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Temperature", f"{weather_data['temp']}°C")
            with col2:
                st.metric("Feels Like", f"{weather_data['feels_like']}°C")
            with col3:
                st.metric("Humidity", f"{weather_data['humidity']}%")
            
            # Description & Icon
            st.subheader(f"Weather: {weather_data['description'].capitalize()}")
            icon_url = f"http://openweathermap.org/img/wn/{weather_data['icon']}.png"
            st.image(icon_url, width=100)
            st.write(f"Wind Speed: {weather_data['wind_speed']} m/s")
            
            # Farming Tip (English - Based on Weather)
            if 'rain' in weather_data['description'].lower():
                st.info("🌧️ **Farming Tip:** Rainy – Delay irrigation. Protect crops.")
            elif weather_data['temp'] > 30:
                st.info("☀️ **Farming Tip:** Hot – Provide more water to your crops.")
            else:
                st.info("🌤️ **Farming Tip:** Good weather – Suitable for farming activities.")
            
            # Download Summary (Mirrors AI Download)
            summary = f"Weather for {location}: Temp {weather_data['temp']}°C, {weather_data['description']}, Humidity {weather_data['humidity']}%. Tip: {st.info.__doc__ or 'See above'}"
            if st.button("📥 Download Weather Summary (TXT)"):
                filename = f"weather_{user.get('name', 'Farmer')}_en.txt"
                st.download_button(
                    label="Download",
                    data=summary.encode('utf-8'),
                    file_name=filename,
                    mime="text/plain"
                )
            
            # Refresh Button (Mirrors Clear)
            if st.button("🔄 Refresh"):
                st.rerun()
        else:
            st.error("Location not found. Use Kerala cities (e.g., Kochi, Thrissur).")
else:
    st.info("⚠️ Enter location or complete profile.")

# Footer (Mirrors English Pages)
st.markdown("---")
st.markdown("**Built with ❤️ for Kerala farmers** | Weather via OpenWeatherMap.")

# Back/Clear (Mirrors Structure)
col_back, col_clear = st.columns(2)
with col_back:
    if st.button("🏠 Back to Profile/AI"):
        st.switch_page("pages/1_english.py")
with col_clear:
    if st.button("Clear"):
        st.rerun()
