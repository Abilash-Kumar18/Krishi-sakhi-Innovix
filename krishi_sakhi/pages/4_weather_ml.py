# pages/4_weather_ml.py – Standalone Malayalam Weather Page (Mirror of English)
import streamlit as st
import os
import requests
from dotenv import load_dotenv

load_dotenv()  # Load API keys

def get_weather(location, api_key):
    """Fetch weather from OpenWeatherMap API (Same as English)"""
    if not location:
        return None
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        'q': location + ',IN',
        'appid': api_key,
        'units': 'metric',
        'lang': 'hi'  # Hindi for better ML approximation; translate manually
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

def translate_weather_terms(desc):
    """Translate English API desc to Malayalam (Simple dict for mirror)"""
    terms = {
        'clear sky': 'വിശദമായ ആകാശം',
        'few clouds': 'കുറച്ച് മേഘങ്ങൾ',
        'scattered clouds': 'വിതറിയ മേഘങ്ങൾ',
        'broken clouds': 'പൊട്ടിയ മേഘങ്ങൾ',
        'shower rain': 'മഴക്കാലം',
        'rain': 'മഴ',
        'thunderstorm': 'കൊടുങ്കാറ്റ്',
        'snow': 'മഞ്ഞ്',
        'mist': 'മൂടൽമഞ്ഞ്'
    }
    for eng, ml in terms.items():
        if eng in desc.lower():
            return desc.replace(eng, ml, 1).capitalize()  # Partial replace
    return desc.capitalize()  # Fallback to English capitalized

st.set_page_config(page_title="ക്രിഷി സഖി - മലയാളം വെതർ", page_icon="☀️")

st.title("☀️ ക്രിഷി സഖി - മലയാളം വെതർ / Weather")
st.write("നിങ്ങളുടെ സ്ഥലത്തെ കാലാവസ്ഥ അറിയുക. കർഷകർക്ക് ഉപയോഗപ്രദം. / Get local weather for farming.")

# Sidebar (Mirrors Malayalam Profile Page)
st.sidebar.header("👤 ഉപയോക്താവ് / User")
if 'user' in st.session_state and st.session_state.user is not None:
    user = st.session_state['user']
    st.sidebar.write(f"പേര്: {user.get('name', 'അജ്ഞാതൻ')}")
    st.sidebar.write(f"ഫലം: {user.get('crop', 'പൊതു')}")
    st.sidebar.write(f"സ്ഥലം: {user.get('location', 'N/A')}")
else:
    st.sidebar.info("👋 സ്വാഗതം! പ്രൊഫൈൽ സേവ് ചെയ്യുക വ്യക്തിഗത വെതറിന്.")

# Weather Section (Same Logic as English, ML UI)
api_key = os.getenv('OPENWEATHER_API_KEY')
if not api_key:
    st.error("OPENWEATHER_API_KEY .env-ൽ ഇല്ല. openweathermap.org-ൽ നിന്ന് ചേർക്കുക.")
    st.stop()

location = None
if 'user' in st.session_state and st.session_state.user is not None:
    location = st.session_state.user.get('location', None)
else:
    st.warning("⚠️ പ്രൊഫൈൽ പൂർത്തിയാക്കുക വ്യക്തിഗത വെതറിന്.")
    location = st.text_input("സ്ഥലം നൽകുക (e.g., തൃശ്ശൂർ)", placeholder="തൃശ്ശൂർ")

if location:
    with st.spinner("കാലാവസ്ഥ ലോഡ് ചെയ്യുന്നു... / Loading weather..."):
        weather_data = get_weather(location, api_key)
        if weather_data:
            st.success(f"**സ്ഥലം:** {weather_data['city']}, {location}")
            
            # Current Weather Display (Same Columns)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("താപനില / Temperature", f"{weather_data['temp']}°C")
            with col2:
                st.metric("അനുഭവം / Feels Like", f"{weather_data['feels_like']}°C")
            with col3:
                st.metric("ആർദ്രത / Humidity", f"{weather_data['humidity']}%")
            
            # Description & Icon (Translated)
            desc_ml = translate_weather_terms(weather_data['description'])
            st.subheader(f"കാലാവസ്ഥ: {desc_ml}")
            icon_url = f"http://openweathermap.org/img/wn/{weather_data['icon']}.png"
            st.image(icon_url, width=100)
            st.write(f"കാറ്റിന്റെ വേഗത: {weather_data['wind_speed']} m/s / Wind: {weather_data['wind_speed']} m/s")
            
            # Farming Tip (Translated Mirror of English)
            if 'rain' in weather_data['description'].lower() or 'മഴ' in desc_ml.lower():
                st.info("🌧️ **കർഷക ടിപ്പ്:** മഴയുണ്ട് – ജലസേചനം വൈകിപ്പിക്കുക. ഫലങ്ങൾ സംരക്ഷിക്കുക. / Rainy – Delay irrigation.")
            elif weather_data['temp'] > 30:
                st.info("☀️ **കർഷക ടിപ്പ്:** വെയിൽപ്പ – ഫലങ്ങൾക്ക് വെള്ളം കൂടുതൽ നൽകുക. / Hot – More water for crops.")
            else:
                st.info("🌤️ **കർഷക ടിപ്പ്:** നല്ല കാലാവസ്ഥ – കൃഷി പ്രവർത്തനങ്ങൾക്ക് അനുയോജ്യം. / Good for farming.")
            
            # Download Summary (Bilingual)
            summary = f"കാലാവസ്ഥ {location}: {weather_data['temp']}°C, {desc_ml}, {weather_data['humidity']}%. ടിപ്പ്: മുകളിൽ കാണുക. / Weather {location}: {weather_data['temp']}°C, {weather_data['description']}, {weather_data['humidity']}%. Tip: See above."
            if st.button("📥 വെതർ സമ്മറി ഡൗൺലോഡ് (TXT) / Download Summary"):
                filename = f"weather_{user.get('name', 'കർഷകൻ')}_ml.txt"
                st.download_button(
                    label="Download",
                    data=summary.encode('utf-8'),
                    file_name=filename,
                    mime="text/plain"
                )
            
            # Refresh Button
            if st.button("🔄 അപ്ഡേറ്റ് / Refresh"):
                st.rerun()
        else:
            st.error("സ്ഥലം കണ്ടെത്താനായില്ല. കേരള നഗരങ്ങൾ ഉപയോഗിക്കുക (e.g., Kochi).")
else:
    st.info("⚠️ സ്ഥലം നൽകുക അല്ലെങ്കിൽ പ്രൊഫൈൽ പൂർത്തിയാക്കുക.")

# Footer (Bilingual Mirror)
st.markdown("---")
st.markdown("""
**കേരള കർഷകർക്കായി ❤️ ഉണ്ടാക്കിയത്** | OpenWeatherMap വഴി കാലാവസ്ഥ.
""")

# Back/Clear (Mirror)
col_back, col_clear = st.columns(2)
with col_back:
    if st.button("🏠 പ്രൊഫൈൽ/എഐ പേജിലേക്ക് / Back to Profile/AI"):
        st.switch_page("pages/2_malayalam.py")
with col_clear:
    if st.button("എല്ലാം ക്ലിയർ / Clear"):
        st.rerun()
