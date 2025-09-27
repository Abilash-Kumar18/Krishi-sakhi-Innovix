import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# Page config (Malayalam title, wide layout for mobile)
st.set_page_config(
    page_title="Krishi Sakhi - കൃഷി സഖി",
    page_icon="🌱",
    layout="wide"
)

# Initialize session state for profile and pages
if 'profile' not in st.session_state:
    st.session_state.profile = {}
if 'show_profile' not in st.session_state:
    st.session_state.show_profile = False
if 'show_chat' not in st.session_state:
    st.session_state.show_chat = False
if 'weather_data' not in st.session_state:
    st.session_state.weather_data = None

# Function to get coordinates from city name (using Nominatim)
def get_coordinates(city_name):
    url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
    headers = {"User -Agent": "KrishiSakhiApp/1.0 (krishisakhi@example.com)"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            location_data = response.json()
            if location_data:
                location = location_data[0]
                return float(location['lat']), float(location['lon'])
        st.warning("സ്ഥലം കണ്ടെത്താനായില്ല. (City not found. Try exact name.)")
        return None, None
    except Exception as e:
        st.error(f"API തെറ്റ്: {str(e)} (API Error)")
        return None, None

# Function to get weather data (Open-Meteo, 24 hours)
def get_weather_data(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,precipitation_probability,relative_humidity_2m,wind_speed_10m&forecast_days=2&timezone=Asia/Kolkata"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            st.error("കാലാവസ്ഥ ഡാറ്റ ലഭ്യമല്ല. (Weather data unavailable.)")
            return None
    except Exception as e:
        st.error(f"API തെറ്റ്: {str(e)} (API Error)")
        return None

# Title and welcome
st.title("🌱 സ്വാഗതം! Krishi Sakhi - കൃഷി സഖി")
st.markdown("---")

# Welcome section (initial view)
if not st.session_state.show_profile and not st.session_state.show_chat:
    st.header("നിങ്ങളുടെ പ്രൊഫൈൽ സജ്ജീകരിക്കുക")
    st.write("കൃഷി സഹായത്തിനായി നിങ്ങളുടെ വിവരങ്ങൾ പൂരിപ്പിക്കുക. (Fill your farmer profile for personalized advice.)")
    
    # Set Profile Button (no switch_page - toggles view)
    if st.button("പ്രൊഫൈൽ സജ്ജീകരിക്കുക (Set Profile)", use_container_width=True):
        st.session_state.show_profile = True
        st.rerun()  # Refresh to show profile form
    
    st.markdown("---")
    st.write("*ഉദാഹരണം: തൃശ്ശൂർ, ബ്രിൻജാൽ, ചെറു നാട്ടിൻപുറം* (Example: Thrissur, Brinjal, Sandy loam)")

# Profile Setup Section (Enhanced with Personal Data and More Options)
elif st.session_state.show_profile:
    st.header("👨‍🌾 നിങ്ങളുടെ പ്രൊഫൈൽ (Your Profile)")
    
    # Personal Data Section (Name and Age)
    st.subheader("വ്യക്തിഗത വിവരങ്ങൾ (Personal Details)")
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        name = st.text_input("നിങ്ങളുടെ പേര് (Farmer's Name)", placeholder="ഉദാ: രാമൻ (e.g., Raman)")
    with col_p2:
        age = st.slider("പ്രായം (Age)", min_value=18, max_value=80, value=40, step=1)
    
    # Location and Crop (Expanded Options)
    st.subheader("കൃഷി വിവരങ്ങൾ (Farming Details)")
    col1, col2 = st.columns(2)
    
    with col1:
        # More Locations (Kerala Districts/Cities)
        location = st.selectbox(
            "സ്ഥലം (Location)", 
            [
                "തൃശ്ശൂർ (Thrissur)", "കൊച്ചി (Kochi)", "കോഴിക്കോട് (Kozhikode)", 
                "ആലപ്പുഴ (Alappuzha)", "എറണാകുളം (Ernakulam)", "ഇടുക്കി (Idukki)", 
                "കണ്ണൂർ (Kannur)", "കാസർഗോഡ് (Kasaragod)", "കൊല്ലം (Kollam)", 
                "കോട്ടയം (Kottayam)", "മലപ്പുറം (Malappuram)", "പാലക്കാട് (Palakkad)", 
                "പത്തനംതിട്ട (Pathanamthitta)", "തിരുവനന്തപുരം (Thiruvananthapuram)", 
                "വയനാട് (Wayanad)", "മറ്റ് (Other)"
            ]
        )
        # More Crops (Common Kerala Crops)
        crop = st.selectbox(
            "പ്രധാന വിള (Main Crop)", 
            [
                "ബ്രിൻജാൽ (Brinjal)", "പച്ചക്കറി (Vegetables)", "മരം (Trees)", 
                "നെല്ല് (Paddy/Rice)", "തെങ്ങ് (Coconut)", "വാഴപ്പഴം (Banana)", 
                "റബ്ബർ (Rubber)", "കുരുമുളക് (Pepper)", "ആമ (Mango)", 
                "പൈനാപ്പിൾ (Pineapple)", "ഞാൻഡ (Ginger)", "ഏലം (Cardamom)", 
                "ചേമ്പ് (Tapioca)", "കപ്പ (Cotton)", "മറ്റ് (Other)"
            ]
        )
    
    with col2:
        # More Soil Types (Lands/Fields)
        soil = st.selectbox(
            "മണ്ണിന്റെ തരം (Soil Type)", 
            [
                "ചെറു നാട്ടിൻപുറം (Sandy Loam)", "കള്ളമണ്ണ് (Clay)", 
                "ലോമി (Loamy)", "ലാറ്ററൈറ്റ് (Laterite)", "ചുവപ്പ് മണ്ണ് (Red Soil)", 
                "അലൂവിയൽ (Alluvial)", "കറുത്ത മണ്ണ് (Black Soil)", "പീറ്റി (Peaty)", 
                "മറ്റ് (Other)"
            ]
        )
        # New: Field Type Options
        field_type = st.selectbox(
            "ഫീൽഡിന്റെ തരം (Field Type)", 
            [
                "ജലസേചനം (Irrigated)", "മഴാബാധിതം (Rainfed)", 
                "ടെറസ് (Terrace)", "ഉയർന്ന നിലം (Upland)", 
                "താഴ്ന്ന നിലം (Lowland)", "മറ്റ് (Other)"
            ]
        )
        experience = st.slider("കൃഷി അനുഭവം (Years of Experience)", 0, 30, 5)
    
    # Submit Button (with Validation)
    if st.button("പ്രൊഫൈൽ സേവ് ചെയ്യുക (Save Profile)", use_container_width=True):
        if not name.strip():  # Validate name
            st.error("പേര് നൽകുക! (Please enter your name.)")
        else:
            st.session_state.profile = {
                'name': name.strip(),
                'age': age,
                'location': location.split(' (')[0] if ' (' in location else location,  # Extract city name
                'crop': crop.split(' (')[0] if ' (' in crop else crop,
                'soil': soil.split(' (')[0] if ' (' in soil else soil,
                'field_type': field_type.split(' (')[0] if ' (' in field_type else field_type,
                'experience': experience
            }
            st.session_state.show_profile = False
            st.session_state.show_chat = True
            st.success(f"പ്രൊഫൈൽ സേവ് ചെയ്തു, {name}! (Profile saved, {name}!)")
            st.rerun()  # Go to chat
    
    # Back button
    if st.button("അടങ്ങൾ (Back to Welcome)"):
        st.session_state.show_profile = False
        st.rerun()

# Chat Section with Weather (Updated Profile Display)
elif st.session_state.show_chat:
    name = st.session_state.profile.get('name', 'കർഷകൻ')  # Fallback
    location = st.session_state.profile.get('location', 'Thrissur')  # Fallback
    st.header(f"💬 ഹലോ {name}! {st.session_state.profile.get('crop', 'വിള')} വിളയ്ക്കുള്ള ഉപദേശം (Hello {name}! Chat - Advice for {st.session_state.profile.get('crop', 'Crop')})")
    
    # Display saved profile (Enhanced with Name, Age, Field Type)
    st.subheader("നിങ്ങളുടെ പ്രൊഫൈൽ (Your Profile):")
    profile_str = f"പേര്: {st.session_state.profile.get('name', 'N/A')}, പ്രായം: {st.session_state.profile.get('age', 'N/A')} വയസ്സ്, സ്ഥലം: {st.session_state.profile.get('location', 'N/A')}, വിള: {st.session_state.profile.get('crop', 'N/A')}, മണ്ണ്: {st.session_state.profile.get('soil', 'N/A')}, ഫീൽഡ് തരം: {st.session_state.profile.get('field_type', 'N/A')}, അനുഭവം: {st.session_state.profile.get('experience', 0)} വർഷം"
    st.write(profile_str)
    
    # Weather Section
    st.subheader(f"🌤️ {location}യിലെ കാലാവസ്ഥ (Weather in {location})")
    
    if st.button("കാലാവസ്ഥ അപ്ഡേറ്റ് ലഭിക്കുക (Get Weather Update)", use_container_width=True):
        lat, lon = get_coordinates(location)
        if lat and lon:
            st.session_state.weather_data = get_weather_data(lat, lon)
            st.rerun()
    
    if st.session_state.weather_data:
        data = st.session_state.weather_data
        forecast_hours = 24
        times = [datetime.now() + timedelta(hours=i) for i in range(forecast_hours)]
        
        # Prepare DataFrame for charts
        df = pd.DataFrame({"Time": times})
        df["Temperature (°C)"] = data['hourly']['temperature_2m'][:forecast_hours]
        df["Rain Probability (%)"] = data['hourly']['precipitation_probability'][:forecast_hours]
        df["Humidity (%)"] = data['hourly']['relative_humidity_2m'][:forecast_hours]
        df["Wind Speed (km/h)"] = [speed * 3.6 for speed in data['hourly']['wind_speed_10m'][:forecast_hours]]  # Convert m/s to km/h
        
        # Current Weather Summary (first hour)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🌡️ താപനില (Temperature)", f"{df['Temperature (°C)'][0]:.1f}°C")
        with col2:
            st.metric("🌧️ മഴ സാധ്യത (Rain Prob)", f"{df['Rain Probability (%)'][0]}%")
        with col3:
            st.metric("💧 ഈർപ്പം (Humidity)", f"{df['Humidity (%)'][0]}%")
        with col4:
            st.metric("🌬️ കാറ്റ് (Wind)", f"{df['Wind Speed (km/h)'][0]:.1f} km/h")
        
        # Forecast Charts
        st.subheader("അടുത്ത 24 മണിക്കൂറിന്റെ പ്രവചനം (24-Hour Forecast)")
        col_temp, col_rain = st.columns(2)
        with col_temp:
            st.line_chart(df.set_index("Time")["Temperature (°C)"], use_container_width=True)
        with col_rain:
            st.line_chart(df.set_index("Time")["Rain Probability (%)"], use_container_width=True)
        
        # Crop Advice based on Weather (Simple integration)
        if df['Rain Probability (%)'][0] > 50:
            st.warning(f"മഴ സാധ്യത ഉയർന്നു ({df['Rain Probability (%)'][0]}%). {st.session_state.profile.get('crop', 'വിള')}യ്ക്ക് ജലസേചനം കുറയ്ക്കുക. (High rain chance. Reduce irrigation for your crop.)")
        elif df['Temperature (°C)'][0] > 35:
            st.info(f"ഉയർന്ന താപനില ({df['Temperature (°C)'][0]}°C). {st.session_state.profile.get('crop', 'വിള')}യ്ക്ക് നിഴൽ നൽകുക. (High temp. Provide shade for your crop.)")
    
    else:
        st.info("കാലാവസ്ഥ ഡാറ്റ ലഭ്യമല്ല. ബട്ടൺ ക്ലിക്ക് ചെയ്യുക. (No data yet. Click button to fetch.)")
    
    st.markdown("---")
    
    # Chat interface (rule-based example - add your OpenAI if needed)
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("നിങ്ങളുടെ ചോദ്യം ഇവിടെ ടൈപ്പ് ചെയ്യുക (Type your query, e.g., 'മഴ' or 'കീടം')"):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response (rule-based fallback, now personalized with name/age/field_type)
        def generate_bot_response(user_input, profile, weather_data=None):
            name = profile.get('name', 'കർഷകൻ')
            age = profile.get('age', 40)
            user_input_lower = user_input.lower()
            crop = profile.get('crop', '')
            location = profile.get('location', '')
            field_type = profile.get('field_type', '')
            soil = profile.get('soil', '')
            
            if weather_data and 'temperature_2m' in weather_data['hourly']:
                current_temp = weather_data['hourly']['temperature_2m'][0]
                rain_prob = weather_data['hourly']['precipitation_probability'][0]
            else:
                current_temp = 28  # Fallback
                rain_prob = 0
            
            greeting = f"ഹലോ {name}, നിങ്ങളുടെ {age} വയസ്സിലെ അനുഭവത്തോടെ {field_type} ഫീൽഡിന്... (Hello {name}, with your"
