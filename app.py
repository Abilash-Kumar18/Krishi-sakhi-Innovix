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
    headers = {"User-Agent": "KrishiSakhiApp/1.0 (krishisakhi@example.com)"}
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

# Profile Setup Section
elif st.session_state.show_profile:
    st.header("👨‍🌾 നിങ്ങളുടെ പ്രൊഫൈൽ (Your Profile)")
    
    # Form for profile inputs (use columns for better layout)
    col1, col2 = st.columns(2)
    
    with col1:
        location = st.selectbox("സ്ഥലം (Location)", ["തൃശ്ശൂർ (Thrissur)", "കൊച്ചി (Kochi)", "കോഴിക്കോട് (Kozhikode)", "മറ്റ് (Other)"])
        crop = st.selectbox("പ്രധാന വിള (Main Crop)", ["ബ്രിൻജാൽ (Brinjal)", "പച്ചക്കറി (Vegetables)", "മരം (Trees)", "മറ്റ് (Other)"])
    
    with col2:
        soil = st.selectbox("മണ്ണിന്റെ തരം (Soil Type)", ["ചെറു നാട്ടിൻപുറം (Sandy Loam)", "കള്ളമണ്ണ് (Clay)", "മറ്റ് (Other)"])
        experience = st.slider("കൃഷി അനുഭവം (Years of Experience)", 0, 30, 5)
    
    # Submit Button
    if st.button("പ്രൊഫൈൽ സേവ് ചെയ്യുക (Save Profile)", use_container_width=True):
        st.session_state.profile = {
            'location': location.split(' (')[0],  # Extract city name, e.g., "തൃശ്ശൂർ"
            'crop': crop,
            'soil': soil,
            'experience': experience
        }
        st.session_state.show_profile = False
        st.session_state.show_chat = True
        st.success("പ്രൊഫൈൽ സേവ് ചെയ്തു! (Profile saved!)")
        st.rerun()  # Go to chat
    
    # Back button
    if st.button("അടങ്ങൾ (Back to Welcome)"):
        st.session_state.show_profile = False
        st.rerun()

# Chat Section with Weather
elif st.session_state.show_chat:
    location = st.session_state.profile.get('location', 'Thrissur')  # Fallback
    st.header(f"💬 ചാറ്റ് - {st.session_state.profile.get('crop', 'വിള')} വിളയ്ക്കുള്ള ഉപദേശം (Chat - Advice for {st.session_state.profile.get('crop', 'Crop')})")
    
    # Display saved profile
    st.subheader("നിങ്ങളുടെ പ്രൊഫൈൽ (Your Profile):")
    profile_str = f"സ്ഥലം: {st.session_state.profile.get('location', 'N/A')}, വിള: {st.session_state.profile.get('crop', 'N/A')}, മണ്ണ്: {st.session_state.profile.get('soil', 'N/A')}, അനുഭവം: {st.session_state.profile.get('experience', 0)} വർഷം"
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
        
        # Generate response (rule-based fallback, now weather-aware)
        def generate_bot_response(user_input, profile, weather_data=None):
            user_input_lower = user_input.lower()
            crop = profile.get('crop', '')
            location = profile.get('location', '')
            
            if weather_data and 'temperature_2m' in weather_data['hourly']:
                current_temp = weather_data['hourly']['temperature_2m'][0]
                rain_prob = weather_data['hourly']['precipitation_probability'][0]
            else:
                current_temp = 28  # Fallback
                rain_prob = 0
            
            if 'മഴ' in user_input_lower or 'rain' in user_input_lower:
                return f"{location}യിൽ മഴ സാധ്യത {rain_prob}%. {crop} വിളയ്ക്ക് ജലം കുറയ്ക്കുക. (Rain prob {rain_prob}% in {location}. Reduce water for {crop}.)"
            elif 'കീടം' in user_input_lower or 'pest' in user_input_lower:
                return f"{crop}യിൽ കീടങ്ങൾ: നീരാളി സ്പ്രേ (10ml/ലിറ്റർ) ഉപയോഗിക്കുക. {profile.get('soil', '')} മണ്ണിന് അനുയോജ്യം. താപനില {current_temp}°C - കീടങ്ങൾ വർധിക്കാം. (Pests: Neem spray. Temp {current_temp}°C may increase pests.)"
            elif 'വളം' in user_input_lower or 'fertilizer' in user_input_lower:
                return f"{profile.get('soil', 'മണ്ണ്')}യ്ക്ക് ഓർഗാനിക് കമ്പോസ്റ്റ് 2kg/സെന്റ്. മഴ {rain_prob}% - വളം കുറയ്ക്കുക. (Compost 2kg/cent. Rain {rain_prob}% - reduce fertilizer.)"
            else:
                return f"കൂടുതൽ വിശദാംശങ്ങൾ പറയൂ. ഉദാ: 'മഴ' അല്ലെങ്കിൽ 'കീടം'. (Tell more. E.g., 'rain' or 'pest'.)"
        
        with st.chat_message("assistant"):
            response = generate_bot_response(prompt, st.session_state.profile, st.session_state.weather_data)
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
        
        st.rerun()
    
    # Back to profile edit
    if st.button("പ്രൊഫൈൽ എഡിറ്റ് (Edit Profile)"):
        st.session_state.show_chat = False
        st.session_state.show_profile = True
        st.session_state.weather_data = None  # Clear weather on edit
        st.rerun()
