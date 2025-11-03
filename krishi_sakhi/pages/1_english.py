import streamlit as st
import sqlite3  # For DB queries in history
import pandas as pd  # For history table (optional; install: pip install pandas)
import re  # For HTML stripping in msg (safe)
import speech_recognition as sr  # For transcription
import io  # For audio handling
    
try:
    import folium
    from streamlit_folium import st_folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False
    folium = None
    st_folium = None

MAP_AVAILABLE = FOLIUM_AVAILABLE  # For map section

from dotenv import load_dotenv
import os
from huggingface_hub import InferenceClient
import requests
from datetime import datetime

# Custom modules (with fallback warnings)
try:
    from backend.database import save_farmer, get_farmer_data, save_query, get_farmer, update_farmer_token, init_db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    st.error("Create 'backend/database.py' for login/DB features. Using mock mode.")

try:
    from utils.llm import generate_ai_response
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    st.warning("Create 'utils/llm.py' for AI advice. Using sample responses.")

try:
    from utils.voice import init_voice, speak_browser, listen_browser
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False
    st.warning("Create 'utils/voice.py' for voice features. Using text-only.")

# FCM Import (Safe – Set Flag on Success)
FCM_AVAILABLE = False
try:
    from utils.notifications import send_real_notification
    NOTIFICATIONS_AVAILABLE = True
    FCM_AVAILABLE = True  # Enable if import succeeds
except ImportError:
    NOTIFICATIONS_AVAILABLE = False
    FCM_AVAILABLE = False
    send_real_notification = None  # Fallback: No notifications
    st.warning("Notifications module missing. Create utils/notifications.py for Firebase pushes.")

load_dotenv()

@st.cache_resource
def get_hf_client():
    api_key = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
    if not api_key:
        st.error("HF_TOKEN missing in .env. AI unavailable.")
        return None
    return InferenceClient(provider="hf-inference", api_key=api_key)

def generate_ai_response(query, farmer_data, lang_code="en"):
    client = get_hf_client()  # From prior code (InferenceClient)
    if not client:
        return "AI unavailable. Add HF_TOKEN to .env."

    # Use .get() assuming farmer_data is dict
    profile_str = f"Crop: {farmer_data.get('crop', 'general')}, Location: {farmer_data.get('location_ml', 'your area')}, Soil: {farmer_data.get('soil', 'loamy')}, Farm size: {farmer_data.get('farm_size', 2)} acres."

    # System prompt (English base; adjust for lang if needed)
    system_content = "You are Krishi Sakhi, a helpful farming expert for Indian farmers in regions like Kerala. Provide simple, actionable advice in English. Focus on sustainable, practical steps. Structure response with numbered steps if possible."

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": f"Query: {query}. Farmer profile: {profile_str}. Advise based on Indian agriculture context."}
    ]

    try:
        with st.spinner("Generating AI farming advice..."):
            completion = client.chat.completions.create(
                model="HuggingFaceTB/SmolLM3-3B",
                messages=messages,
                max_tokens=200,
                temperature=0.3,
                top_p=0.9
            )
            english_response = completion.choices[0].message.content.strip()

        # Translate if Malayalam selected
        if lang_code == "ml":
            with st.spinner("Translating to Malayalam (Local)..."):
                response = translate_local(english_response, "en", "ml")

            try:
                with st.spinner("Translating to Malayalam..."):
                    # Method 1: API POST (Requires upgraded client)
                    translation_result = client.post(
                        model="Helsinki-NLP/opus-mt-en-ml",
                        json={"inputs": english_response}  # Simple payload for seq2seq
                    )
                    if isinstance(translation_result, list) and len(translation_result) > 0:
                        response = translation_result[0].get('translation_text', english_response)
                    else:
                        raise ValueError("Invalid translation response")
            except AttributeError as attr_e:
                # Fallback if no 'post' (old version)
                st.warning(f"API translation unavailable ({str(attr_e)}). Trying local...")
                response = translate_local(english_response, "en", "ml")
            except Exception as trans_e:
                st.warning(f"Translation error: {str(trans_e)}. Using local fallback.")
                response = translate_local(english_response, "en", "ml")
        else:
            response = english_response

        return response if response else "No advice generated."
    except Exception as e:
        st.error(f"AI Error: {str(e)}")
        return f"AI temporarily unavailable. Sample for '{query}': Use neem oil sprays and monitor fields daily for {farmer_data.get('crop', 'your crop')}."

# Add this helper function (Local translation – Below generate_ai_response or at top)
@st.cache_resource  # Loads model once (downloads ~300MB first time)
def load_translator():
    from transformers import pipeline
    return pipeline("translation", model="Helsinki-NLP/opus-mt-en-ml")

def translate_local(text, src_lang, tgt_lang):
    try:
        translator = load_translator()
        result = translator(text, max_length=300)
        return result[0]['translation_text']
    except Exception as local_e:
        st.error(f"Local translation failed: {str(local_e)}. Install transformers: pip install transformers")
        return text  # Ultimate fallback: English
    
API_KEY = os.getenv("OPENWEATHER_API_KEY")
st.session_state.language = 'en'
if VOICE_AVAILABLE:
    init_voice()

# Single Session State Init (No Dupe)
if 'fcm_token' not in st.session_state:
    st.session_state.fcm_token = None
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.farmer_id = None
    st.session_state.user = {}  # Dict for consistency
    st.session_state.voice_transcript = None
    st.session_state.ai_response = None
    if DB_AVAILABLE:
        init_db()  # Ensure tables exist

# CSS for UI
st.markdown("""
<style>
    .big-text { font-size: 28px !important; font-weight: bold; color: green; }
    .section-img { width: 100%; max-width: 400px; border-radius: 10px; }
    button { font-size: 20px; height: 50px; padding: 10px; }
    .stButton > button { background-color: #4CAF50; color: white; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# Clean Sidebar: User Profile Only + Logout
with st.sidebar:
    st.header("👤 User Profile")
    user = st.session_state.get('user', {})  # Ensure dict
    if user and len(user) > 0:
        st.write(f"**Name:** {user.get('name', 'Unknown')}")
        st.write(f"**Crop:** {user.get('crop', 'General')}")
        st.write(f"**FCM Token:** {'Set' if user.get('fcm_token') else 'Not Set'}")
        if FCM_AVAILABLE and user.get('fcm_token'):
            st.success("🔔 Push Notifications: Ready")
        else:
            st.info("Add FCM token for push alerts.")
    else:
        st.info("👋 Welcome! Login to start.")

    # Logout (Keep at bottom)
    if st.session_state.logged_in:
        st.write(f"Logged in as: {st.session_state.username}")
        if st.button("🚪 Logout", key='logout_btn'):
            for key in ['logged_in', 'username', 'farmer_id', 'user', 'fcm_token', 'voice_transcript', 'ai_response']:
                if key in st.session_state:
                    del st.session_state[key]
            st.success("Logged out successfully!")
            st.rerun()
    else:
        st.info("Login to access personalized features.")

# Images
FARMER_IMG = "https://images.unsplash.com/photo-1559827260-dc66d52bef19?ixlib=rb-4.0.3&auto=format&fit=crop&w=400"

def get_weather(location):
    if not API_KEY or API_KEY == "your_key":
        return "Weather API key needed. Sign up at openweathermap.org and add to .env."
    url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={API_KEY}&units=metric"
    try:
        response = requests.get(url)
        data = response.json()
        if response.status_code == 200:
            temp = data['main']['temp']
            condition = data['weather'][0]['description']
            humidity = data['main']['humidity']
            # Auto-send alert if rainy (example – Fixed sanitize)
            if 'rain' in condition.lower() and st.session_state.get('fcm_token') and FCM_AVAILABLE:
                user = st.session_state.get('user', {})
                success = send_real_notification(
                    f"Rainy weather in {location}! Protect crops from waterlogging. Temp: {temp}°C, Humidity: {humidity}%",
                    "warning", user
                )
                if success:
                    st.sidebar.success("🌧️ Rain alert sent!")
            return f"🌤️ Temperature: {temp}°C | Condition: {condition.capitalize()} | Humidity: {humidity}%"
        else:
            return "Weather data unavailable. Check location spelling."
    except Exception as e:
        return f"Error fetching weather: {str(e)}"

# 🔔 Notifications Setup (Moved from Sidebar – Simple Manual)
if st.session_state.logged_in:
    with st.expander("🔔 Setup Push Notifications (Firebase)"):  # Collapsible to avoid clutter
        st.info("For push alerts: 1. Allow notifications in browser. 2. Get FCM token from console (F12 > Run Firebase JS from docs). 3. Paste below.")
        
        pasted_token = st.text_input(
            "Paste FCM Token:", 
            value=st.session_state.get('fcm_token', ''), 
            placeholder="e.g., fallback_mock_123 or real token from console",
            key='token_input'
        )
        if st.button("Save Token to Profile", key='save_token'):
            if pasted_token.strip():
                st.session_state.fcm_token = pasted_token.strip()
                # Update user dict
                if 'user' in st.session_state:
                    st.session_state.user['fcm_token'] = pasted_token.strip()
                st.success(f"✅ Token saved: {pasted_token[:20]}...")
                st.rerun()
            else:
                st.warning("Paste a valid token.")
        
        # Test Button (Simple)
        if st.button("🧪 Test Notification", key='test_notif'):
            token = st.session_state.get('fcm_token')
            if token and FCM_AVAILABLE:
                user = st.session_state.get('user', {})
                success = send_real_notification("🧪 Test Alert", "info", user)  # Use your function
                if success:
                    st.success("Push sent! Check device/browser.")
                else:
                    st.error("Send failed – Check token/setup.")
            else:
                st.warning("No token or FCM unavailable. Setup first.")

# Login Section
st.markdown("<p class='big-text'>👨‍🌾 Welcome to Krishi Sakhi! Login</p>", unsafe_allow_html=True)  # Fixed: markdown for HTML
st.image(FARMER_IMG, caption="Enter your details for personalized farming advice.")
if not st.session_state.logged_in:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Personal Info")  # Plain subheader – No HTML
        username = st.text_input("Username (Unique ID)", placeholder="e.g., raman123", key='login_user')
        name = st.text_input("Full Name", placeholder="e.g., Raman", key='login_name')
        phone = st.text_input("Phone Number", placeholder="e.g., 9876543210", key='login_phone')
        age = st.slider("Age", 18, 80, 40, key='login_age')
        gender = st.selectbox("Gender", ["Male", "Female", "Other"], key='login_gender')
    
    with col2:
        st.subheader("Farming Info")  # Plain subheader
        location_ml = st.selectbox("Location (District)", ["Thrissur", "Kochi", "Kozhikode", "Other"], key='login_loc')
        crop = st.selectbox("Main Crop", ["Paddy/Rice", "Brinjal", "Vegetables", "Other"], key='login_crop')
        soil = st.selectbox("Soil Type", ["Loamy", "Clay", "Sandy Loam", "Other"], key='login_soil')
        field_type = st.selectbox("Field Type", ["Irrigated", "Rainfed", "Other"], key='login_field')
        farm_size = st.slider("Farm Size (Acres)", 0.0, 50.0, 2.0, key='login_size')
        irrigation_type = st.selectbox("Irrigation", ["Drip", "Flood", "Rainfed", "Other"], key='login_irr')
        experience = st.slider("Experience (Years)", 0, 30, 5, key='login_exp')
        pests_history = st.text_area("Pests History (Optional)", placeholder="e.g., Aphids on brinjal", key='login_pests', height=60)
        yield_goals = st.text_area("Yield Goals (Optional)", placeholder="e.g., Increase yield by 20%", key='login_goals', height=60)
    
    if st.button("Login & Save Profile", use_container_width=True, key='login_btn'):
        if username and name and phone:
            lat, lon = 10.5276, 76.2144  # Default: Thrissur (update with geocode API later)
            data = {
                'username': username, 'name': name, 'age': age, 'gender': gender, 'phone': phone,
                'fcm_token': st.session_state.get('fcm_token', ''),  # Add this
                'location_ml': location_ml, 'location_en': location_ml,
                'lat': lat, 'lon': lon, 'crop': crop, 'soil': soil, 'field_type': field_type,
                'farm_size': farm_size, 'irrigation_type': irrigation_type, 'experience': experience,
                'pests_history': pests_history, 'yield_goals': yield_goals
            }
            if DB_AVAILABLE:
                saved_farmer = save_farmer(data)
                if saved_farmer:
                    st.session_state.farmer_id = saved_farmer.id
                    st.session_state.username = username
                    st.session_state.user = get_farmer_data(username)  # Assume returns dict
                    st.session_state.logged_in = True
                    st.success(f"✅ Welcome {name}! Profile saved. Your {crop} farm in {location_ml} is ready for advice.")
                    # Update FCM token in DB if available
                    if st.session_state.fcm_token:
                        update_farmer_token(saved_farmer.id, st.session_state.fcm_token)
                    # Send welcome notification
                    if FCM_AVAILABLE and st.session_state.get('fcm_token'):
                        send_real_notification("Welcome to Krishi Sakhi! Your profile is saved. Get personalized farming alerts.", "success", st.session_state.user)
                    st.rerun()
                else:
                    st.error("Username already exists. Choose a unique one.")
            else:
                # Mock login – Use dict
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.user = data  # Dict for consistency
                st.success(f"✅ Mock login for {name}. (Create database.py for real save.)")
                # Send welcome notification
                if FCM_AVAILABLE and st.session_state.get('fcm_token'):
                    send_real_notification("Welcome to Krishi Sakhi! Your profile is saved. Get personalized farming alerts.", "success", st.session_state.user)
                st.rerun()
        else:
            st.warning("Please fill name, username, and phone.")

# Post-Login Sections
if st.session_state.logged_in:
    user = st.session_state.get('user', {})  # Dict
    st.header(f"🌾 Hi {user.get('name', 'Farmer')}! Your Farm: {user.get('crop', 'General')} in {user.get('location_ml', 'Your Area')} | Size: {user.get('farm_size', 2.0)} Acres")

    # Weather Section
    st.header("☁️ Weather Forecast")
    location = st.text_input("Enter Location (e.g., Kochi)", value=user.get('location_ml', ''), key='weather_loc')
    if location:
        weather = get_weather(location)
        st.info(weather)
        if st.button("🔔 Send Weather Alert", key='weather_alert'):
            if st.session_state.get('fcm_token') and FCM_AVAILABLE:
                success = send_real_notification(
                    f"Current weather in {location}: {weather}",
                    "info", user
                )
                if success:
                    st.success("Weather push sent!")
                else:
                    st.error("Send failed.")
            else:
                st.warning("No token or FCM unavailable.")

    # AI Section
    st.header("🗣️ Ask Krishi Sakhi")
    st.write("Enter or speak your farming query for expert AI advice (e.g., 'Pest control for rice in rainy season').")

    # Step 1: Initialize query_text (Fixes NameError – Always defined)
    query_text = ""  # Start empty; will be set by text/voice

    # Step 2: Language selector (Before inputs)
    selected_lang = st.selectbox(
        "Language / ഭാഷ", 
        ["English", "Malayalam / മലയാളം"], 
        key="ai_lang"
    )
    lang_code = "ml" if selected_lang == "Malayalam / മലയാളം" else "en"
    st.write(f"Selected: {selected_lang}")

    # Step 3: Voice Input (Processes first; sets query_text if successful)
    st.subheader("🎤 Voice Query (Optional)")
    st.write("Upload an audio file (WAV/MP3) of your question. Speak in English or Malayalam.")
    audio_file = st.file_uploader("Choose audio file", type=['wav', 'mp3', 'm4a'], key="audio_upload")

    # Transcription helper function (Inline for simplicity)
    def transcribe_audio(audio_file):
        if audio_file:
            try:
                # Reset file pointer
                audio_file.seek(0)
                recognizer = sr.Recognizer()
                audio_bytes = io.BytesIO(audio_file.read())
                with sr.AudioFile(audio_bytes) as source:
                    audio_data = recognizer.record(source)
                # Transcribe (en-IN for Indian English; ml-IN for Malayalam)
                text = recognizer.recognize_google(audio_data, language='en-IN')  # Change to 'ml-IN' if needed
                st.success(f"🎤 Transcribed: {text}")
                return text
            except sr.UnknownValueError:
                st.error("Could not understand audio. Please try text input.")
                return None
            except sr.RequestError:
                st.error("Transcription service unavailable (check internet). Use text input.")
                return None
            except Exception as e:
                st.error(f"Audio processing error: {str(e)}. Ensure file is clear.")
                return None
        return None

    # Process voice if uploaded (Sets query_text)
    if audio_file is not None:
        transcribed = transcribe_audio(audio_file)
        if transcribed:
            query_text = transcribed  # Override with voice
        else:
            query_text = ""  # Reset if failed

    # Step 4: Text Input (Fallback/Primary – Always after voice)
    st.subheader("⌨️ Text Query")
    query_text = st.text_input(
        "Your Question:",
        value=query_text if query_text else "",  # Preserve voice if set
        placeholder="What to do about pests in my brinjal crop?",
        key="ai_query"  # Unique key
    )

    # Step 5: Process & Display (Now safe – query_text always defined)
    if query_text.strip():  # Use .strip() to ignore whitespace-only
        # Fetch user data
        user = st.session_state.get('user', {})  # Dict
        if not user:
            st.warning("⚠️ Please complete your profile first for personalized advice.")
            st.info("Go to profile section and set crop, location, etc.")
        else:
            # Generate response (With lang_code)
            ai_response = generate_ai_response(query_text, user, lang_code)
            
            # Display
            st.success(f"**AI Advice ({selected_lang}):**")
            st.write(ai_response)
            
            # Notification Trigger (Firebase Push)
            if FCM_AVAILABLE and st.session_state.get('fcm_token'):
                summary = ai_response[:100].replace('\n', ' ')  # Short body
                success = send_real_notification(f"AI Advice for '{query_text[:30]}...': {summary}", "info", user)
                if success:
                    st.success("🔔 Advice also sent as push notification!")
            
            # Step 6: Download (Only if response exists)
            if ai_response:
                filename = f"krishi_sakhi_advice_{user.get('name', 'farmer')}_{lang_code}.txt"
                st.download_button(
                    label="📥 Download Advice (TXT)",
                    data=ai_response.encode('utf-8'),  # Handles Malayalam Unicode
                    file_name=filename,
                    mime="text/plain",
                    help="Save for offline use or printing."
                )

    # Optional: Clear button (At end of section)
    if st.button("Clear All (Query & Audio)"):
        st.rerun()  # Reloads page, clears inputs

    # Map Section (If Available)
    st.header("🗺️ Your Farm Map")
    if MAP_AVAILABLE:
        lat = user.get('lat', 10.5276)  # Default: Thrissur lat
        lon = user.get('lon', 76.2144)  # Default: Thrissur lon
        farm_size = user.get('farm_size', 2.0)  # Default 2 acres
        
        try:
            # Create base map centered on farm
            m = folium.Map(location=[lat, lon], zoom_start=12, tiles='OpenStreetMap')
            
            # Add marker for farm location
            folium.Marker(
                [lat, lon], 
                popup=f"<b>{user.get('crop', 'Farm')} Farm</b><br>Location: {user.get('location_ml', 'Your Area')}<br>Size: {farm_size} acres<br>Soil: {user.get('soil', 'Loamy')}",
                tooltip="Click for farm details",
                icon=folium.Icon(color='green', icon='leaf')  # Green leaf icon for agriculture
            ).add_to(m)
            
            # Add circle to represent farm area (approximate radius: 1 acre ≈ 70m radius circle)
            radius_m = farm_size * 70 * 2  # Rough estimate for visualization (adjust as needed)
            folium.Circle(
                [lat, lon],
                radius=radius_m,
                popup=f"Farm Boundary ({farm_size} acres)<br>Irrigation: {user.get('irrigation_type', 'Drip')}",
                tooltip="Farm Area",
                color='blue',
                fill=True,
                fillColor='lightblue',
                fillOpacity=0.3
            ).add_to(m)
            
            # Add layer control (optional: toggle marker/circle)
            folium.LayerControl().add_to(m)
            
            # Render map in Streamlit
            st_folium(m, width=700, height=500)
            
        except Exception as e:
            st.error(f"Map rendering error: {str(e)}. Install folium and check coordinates.")
            st.info(f"Placeholder: Your farm is in {user.get('location_ml', 'your location')} – Use Google Maps for now.")
    else:
        st.info(f"Map feature requires 'streamlit-folium'. Install it to visualize your {user.get('location_ml', 'location')} farm.")
        # Placeholder image
        st.image("https://images.unsplash.com/photo-1441974231531-c6227db76b6e?ixlib=rb-4.0.3&auto=format&fit=crop&w=700&h=400", caption="Sample Kerala Farm View")

    # Query History (If DB Available – Show Past Interactions)
    if DB_AVAILABLE and 'farmer_id' in st.session_state and st.session_state.farmer_id:
        st.header("📋 Your Past Queries")
        try:
            # Fetch from DB (add this function to backend/database.py if needed)
            conn = sqlite3.connect('krishi.db')
            df = pd.read_sql_query("SELECT query, response, created_at FROM queries WHERE farmer_id = ? ORDER BY created_at DESC LIMIT 5", conn, params=(st.session_state.farmer_id,))
            conn.close()
            if not df.empty:
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No past queries yet. Ask something to start building your history!")
        except ImportError:
            st.warning("Pandas not installed for history table. pip install pandas")
        except Exception as e:
            st.error(f"History fetch error: {e}")

# Footer (Optional: App Info)
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>🌱 Krishi Sakhi: AI-Powered Farmer Assistant | Built with Streamlit & Firebase</p>
    <p>For issues: Check console (F12) or add API keys to .env</p>
</div>
""", unsafe_allow_html=True)
