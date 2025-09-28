import streamlit as st
import sqlite3  # For DB queries in history
import pandas as pd  # For history table (optional; install: pip install pandas)
import re  # For HTML stripping in msg (safe)
import speech_recognition as sr  # For transcription
import io  # For audio handling
    
try:
    from streamlit_folium import folium_static
    import folium
    MAP_AVAILABLE = True
except ImportError:
    MAP_AVAILABLE = False
    st.warning("Install 'streamlit-folium' and 'folium' for maps: pip install streamlit-folium folium")

from dotenv import load_dotenv
import os
from huggingface_hub import InferenceClient
import requests
import json  # For FCM config
import streamlit.components.v1 as components
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

# FCM Import (Moved to top – Safe if file missing)
FCM_AVAILABLE = False
try:
    from utils.notifications import send_fcm_notification
    FCM_AVAILABLE = True
except ImportError:
    st.warning("Create 'utils/notifications.py' for push alerts. Mock mode.")

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

    profile_str = f"Crop: {getattr(farmer_data, 'crop', 'general')}, Location: {getattr(farmer_data, 'location_ml', 'your area')}, Soil: {getattr(farmer_data, 'soil', 'loamy')}, Farm size: {getattr(farmer_data, 'farm_size', 2)} acres."

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
        return f"AI temporarily unavailable. Sample for '{query}': Use neem oil sprays and monitor fields daily for {getattr(farmer_data, 'crop', 'your crop')}."

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
    st.session_state.user = None
    st.session_state.voice_transcript = None
    st.session_state.ai_response = None
    if DB_AVAILABLE:
        init_db()  # Ensure tables exist

# Real Firebase Config (REPLACE WITH YOUR VALUES from Firebase Console > Project Settings)
FIREBASE_CONFIG = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.getenv("FIREBASE_APP_ID")
}
VAPID_KEY = os.getenv("VAPID_KEY")
# Validate (Optional – Remove after test)
if not all([FIREBASE_CONFIG.get("apiKey"), VAPID_KEY]):
    st.error("Missing Firebase keys in .env – Check setup.")  # From Cloud Messaging > Web push certificates

# FCM JS with Default SW Registration + Local Mock Mode (No Blob/Protocol Error)
FCM_JS = f"""
<script src="https://www.gstatic.com/firebasejs/9.0.0/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/9.0.0/firebase-messaging-compat.js"></script>
<script>
    const firebaseConfig = {json.dumps(FIREBASE_CONFIG)};
    firebase.initializeApp(firebaseConfig);
    const messaging = firebase.messaging();
    
    // Check if Localhost (Mock Mode for Streamlit Local – Skips SW for No 404)
    const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    
    if (!isLocalhost) {{
        // Production/Deploy: Register default SW (File served at /firebase-messaging-sw.js)
        if ('serviceWorker' in navigator) {{
            navigator.serviceWorker.register('/firebase-messaging-sw.js')
                .then(function(registration) {{
                    console.log('SW registered: ', registration);
                }})
                .catch(function(error) {{
                    console.error('SW registration failed: ', error);
                }});
        }}
    }} else {{
        console.log('Localhost mode: Skipping SW registration (use mock token).');
    }}
    
    // Request FCM Token (With Mock Fallback – Unified to fallback_mock_)
    window.requestFCM = function() {{
        Notification.requestPermission().then(function(permission) {{
            if (permission === 'granted') {{
                if (isLocalhost) {{
                    // Mock Token for Local Testing (Simulates Real – Unified name)
                    const mockToken = 'fallback_mock_' + Date.now();  // Matches your token
                    console.log('Fallback Mock Token (Local): ', mockToken);
                    localStorage.setItem('fcm_token', mockToken);
                    alert('✅ Mock Token Saved (Local Mode)! Full: ' + mockToken + '. Alerts will simulate.');
                    return;
                }}
                
                // Real Token (Deploy/Local with File)
                messaging.getToken({{vapidKey: '{VAPID_KEY}'}})
                    .then(function(token) {{
                        console.log('Real FCM Token: ', token);
                        localStorage.setItem('fcm_token', token);
                        alert('✅ Real Token Saved! Check console for full token.');
                    }})
                    .catch(function(err) {{
                        console.error('Real Token Error: ', err);
                        // Fallback to Mock on Error
                        const mockToken = 'fallback_mock_' + Date.now();
                        localStorage.setItem('fcm_token', mockToken);
                        console.log('Fallback Mock Token: ', mockToken);
                        alert('⚠️ Real Token Failed (404?). Using Mock: ' + mockToken);
                    }});
            }} else {{
                alert('❌ Notification permission denied.');
            }}
        }});
    }};
    
    // View Token Helper
    window.viewToken = function() {{
        const token = localStorage.getItem('fcm_token');
        if (token) {{
            console.log('Current Token: ', token);
            alert('Token Logged in Console (F12). Starts with: ' + token.substring(0, 20) + '...');
        }} else {{
            alert('No token. Click Grant first.');
        }}
    }};
</script>
<div id="fcm-section">
    <p><strong>FCM Setup (Notifications)</strong></p>
    <button onclick="requestFCM()">🔔 Grant Permission & Get Token</button>
    <br><small>On localhost: Uses mock (simulates). Deploy for real pushes.</small>
    <br><button onclick="viewToken()">🔍 View Token in Console</button>
</div>
"""

# CSS for UI
st.markdown("""
<style>
    .big-text { font-size: 28px !important; font-weight: bold; color: green; }
    .section-img { width: 100%; max-width: 400px; border-radius: 10px; }
    button { font-size: 20px; height: 50px; padding: 10px; }
    .stButton > button { background-color: #4CAF50; color: white; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# Sidebar: Language, Voice Test, FCM (Fixed Persistent Embed)
with st.sidebar:
    # Sidebar (Fixed: Safe Dict Default - Mirrors Malayalam)
    st.sidebar.header("👤 User")
    user = st.session_state.get('user', {})  # Safe: Always dict (fixes AttributeError)
    if user and isinstance(user, dict) and len(user) > 0:  # Check non-empty dict
        st.sidebar.write(f"Name: {user.get('name', 'Unknown')}")
        st.sidebar.write(f"Crop: {user.get('crop', 'General')}")
    else:
        st.sidebar.info("👋 Welcome, Farmer! Save profile for personalized advice.")
        
    if VOICE_AVAILABLE and st.button("🔊 Test Voice", key='voice_test'):
        speak_browser("Hello Farmer! I am Krishi Sakhi. How can I help with your crops?", selected_lang)
    
    st.subheader("🔔 Notifications Setup")
    
    # Grant Button (Triggers Embed + Optional Auto-Request)
    if st.button("Grant FCM Permission & Get Token", key='grant_fcm'):
        st.session_state.fcm_embedded = True  # Set flag
        st.rerun()  # Rerun to show embed
    
    # Persistent Embed (Only if Flagged – Re-renders on Rerun)
    if st.session_state.get('fcm_embedded', False):
        # Fallback Config if Env Missing (Prevents JS Syntax Error)
        safe_config = FIREBASE_CONFIG.copy()
        for key in safe_config:
            if not safe_config[key]:
                safe_config[key] = ""  # Empty string for JS
        
        # Updated FCM_JS (With Debug + Auto-Option)
        fcm_js_updated = f"""
        <script src="https://www.gstatic.com/firebasejs/9.0.0/firebase-app-compat.js"></script>
        <script src="https://www.gstatic.com/firebasejs/9.0.0/firebase-messaging-compat.js"></script>
        <script>
            console.log("FCM JS Loaded – Debug Start");
            const firebaseConfig = {json.dumps(safe_config)};
            try {{
                firebase.initializeApp(firebaseConfig);
                const messaging = firebase.messaging();
                console.log("Firebase Initialized OK");
            }} catch (err) {{
                console.error("Firebase Init Error: ", err);
            }}
            
            // Check if Localhost (Mock Mode for Streamlit Local – Skips SW for No 404)
            const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
            console.log("Is Localhost: ", isLocalhost);
            
            if (!isLocalhost) {{
                // Production/Deploy: Register default SW (File served at /firebase-messaging-sw.js)
                if ('serviceWorker' in navigator) {{
                    navigator.serviceWorker.register('/firebase-messaging-sw.js')
                        .then(function(registration) {{
                            console.log('SW registered: ', registration);
                        }})
                        .catch(function(error) {{
                            console.error('SW registration failed: ', error);
                        }});
                }}
            }} else {{
                console.log('Localhost mode: Skipping SW registration (use mock token).');
            }}
            
            // Request FCM Token (With Mock Fallback – Unified to fallback_mock_)
            window.requestFCM = function() {{
                console.log("requestFCM Called – Requesting Permission");
                Notification.requestPermission().then(function(permission) {{
                    console.log("Permission: ", permission);
                    if (permission === 'granted') {{
                        if (isLocalhost) {{
                            // Mock Token for Local Testing (Simulates Real – Unified name)
                            const mockToken = 'fallback_mock_' + Date.now();  // Matches your token
                            console.log('Fallback Mock Token (Local): ', mockToken);
                            localStorage.setItem('fcm_token', mockToken);
                            alert('✅ Mock Token Saved (Local Mode)! Full: ' + mockToken + '. Alerts will simulate.');
                            // Optional: Auto-capture to Streamlit (via postMessage or poll – Advanced)
                            return mockToken;
                        }}
                        
                        // Real Token (Deploy/Local with File)
                        messaging.getToken({{vapidKey: '{VAPID_KEY or ''}'}})
                            .then(function(token) {{
                                console.log('Real FCM Token: ', token);
                                localStorage.setItem('fcm_token', token);
                                alert('✅ Real Token Saved! Check console for full token.');
                            }})
                            .catch(function(err) {{
                                console.error('Real Token Error: ', err);
                                // Fallback to Mock on Error
                                const mockToken = 'fallback_mock_' + Date.now();
                                localStorage.setItem('fcm_token', mockToken);
                                console.log('Fallback Mock Token: ', mockToken);
                                alert('⚠️ Real Token Failed (404?). Using Mock: ' + mockToken);
                            }});
                    }} else {{
                        console.log("Permission Denied");
                        alert('❌ Notification permission denied. Reload and try again.');
                    }}
                }});
            }};
            
            // View Token Helper
            window.viewToken = function() {{
                const token = localStorage.getItem('fcm_token');
                if (token) {{
                    console.log('Current Token: ', token);
                    alert('Token Logged in Console (F12). Starts with: ' + token.substring(0, 20) + '...');
                }} else {{
                    alert('No token. Click Grant first.');
                }}
            }};
            
            // Optional: Auto-Trigger if Permission Already Granted (Uncomment for Auto)
            // if (Notification.permission === 'granted') {{ requestFCM(); }}
            
            console.log("FCM JS Loaded – Ready (Click Inner Button)");
        </script>
        <div id="fcm-section" style="padding: 10px; border: 1px solid #ccc; border-radius: 5px; background: #f9f9f9;">
            <p><strong>FCM Setup (Notifications)</strong></p>
            <button onclick="requestFCM()" style="background: #4CAF50; color: white; padding: 10px; border: none; border-radius: 5px;">🔔 Grant Permission & Get Token</button>
            <br><small>On localhost: Uses mock (simulates). Deploy for real pushes. <br>Console logs above.</small>
            <br><button onclick="viewToken()" style="background: #2196F3; color: white; padding: 8px; border: none; border-radius: 5px;">🔍 View Token in Console</button>
        </div>
        """
        components.html(fcm_js_updated, height=250)  # Increased height for visibility
        st.info("🔔 Click the inner 'Grant Permission' button above to get mock token (local). Check F12 Console for logs.")
    else:
        st.info("Click 'Grant FCM' above to enable notifications setup.")

    # Rest of Sidebar (Token Capture – Unchanged)
    st.subheader("🔄 Token Capture")

    # Manual Capture Button & Input
    pasted_token = st.text_input(
        "Paste Token from Alert/Console (e.g., fallback_mock_1759042701886):", 
        value="", 
        key='token_input_field'
    )
    if st.button("Capture Token", key='capture_token_btn'):  # Simplified – No if around input
        if pasted_token and pasted_token.strip():
            st.session_state.fcm_token = pasted_token.strip()
            st.success(f"✅ Token Captured: {pasted_token[:20]}... (Ready for alerts!)")
            st.rerun()  # Refresh to update status
        else:
            st.warning("Paste the full token above.")

    # Status Display (Consolidated)
    st.subheader("Token Status")
    if st.session_state.get('fcm_token'):
        st.success(f"🎉 Active Token: {st.session_state.fcm_token[:20]}...")
        st.write(f"Debug: {st.session_state.fcm_token}")  # Full for dev
    else:
        st.warning("No token – Click inner Grant button, allow, paste here.")
      
    # Force Set (Unchanged)
    if st.button("Force Set Mock Token", key='force_set'):
        st.session_state.fcm_token = "fallback_mock_1759042701886"
        st.success("Forced! Now test alert.")
        st.rerun()
        
    # Test Button (Unchanged – Fixed Earlier)
    if st.button("🧪 Test Captured Token Alert", key='test_captured'):
        token = st.session_state.get('fcm_token')
        if token:
            if FCM_AVAILABLE:
                success, msg = send_fcm_notification(token, "🧪 Token Test", f"Success! Token: {token[:20]}... works for alerts. 🌱")
            else:
                success, msg = True, "Mock alert simulated (No notifications.py – FCM disabled)."
            msg_str = str(msg).strip() if msg else "Unknown error"
            msg_clean = re.sub(r'<[^>]*>', '', msg_str)
            msg_display = msg_clean[:100] + "..." if len(msg_clean) > 100 else msg_clean
            if success:
                st.success(msg_display)
            else:
                st.error(msg_display)
        else:
            st.warning("Capture first.")

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
                success, msg = send_fcm_notification(
                    st.session_state.fcm_token,
                    "🌧️ Rain Alert",
                    f"Rainy weather in {location}! Protect your crops from waterlogging. Temp: {temp}°C, Humidity: {humidity}%",
                    lang='en'
                )
                # Sanitize for display
                msg_str = str(msg).strip() if msg else "Unknown error"
                msg_clean = re.sub(r'<[^>]*>', '', msg_str)
                msg_display = msg_clean[:100] + "..." if len(msg_clean) > 100 else msg_clean
                if success:
                    st.sidebar.success("Alert sent!")
                else:
                    st.sidebar.error(msg_display)
            return f"🌤️ Temperature: {temp}°C | Condition: {condition.capitalize()} | Humidity: {humidity}%"
        else:
            return "Weather data unavailable. Check location spelling."
    except Exception as e:
        return f"Error fetching weather: {str(e)}"

# Capture Voice Transcript (From localStorage hack in voice.py)
if st.button("Process Voice Input", key='process_voice'):  # Call after speaking
    process_js = """
    <script>
    const transcript = localStorage.getItem('voice_transcript');
    if (transcript) {
        alert('Transcript: ' + transcript);
        localStorage.removeItem('voice_transcript');
    } else {
        alert('No voice input detected. Speak first.');
    }
    </script>
    """
    components.html(process_js, height=0)
    st.rerun()

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
                'fcm_token': st.session_state.fcm_token, 'location_ml': location_ml, 'location_en': location_ml,
                'lat': lat, 'lon': lon, 'crop': crop, 'soil': soil, 'field_type': field_type,
                'farm_size': farm_size, 'irrigation_type': irrigation_type, 'experience': experience,
                'pests_history': pests_history, 'yield_goals': yield_goals
            }
            if DB_AVAILABLE:
                saved_farmer = save_farmer(data)
                if saved_farmer:
                    st.session_state.farmer_id = saved_farmer.id
                    st.session_state.username = username
                    st.session_state.user = get_farmer_data(username)
                    st.session_state.logged_in = True
                    st.success(f"✅ Welcome {name}! Profile saved. Your {crop} farm in {location_ml} is ready for advice.")
                    # Update FCM token in DB if available
                    if st.session_state.fcm_token:
                        update_farmer_token(saved_farmer.id, st.session_state.fcm_token)
                    st.rerun()
                else:
                    st.error("Username already exists. Choose a unique one.")
            else:
                # Mock login
                st.session_state.logged_in = True
                st.session_state.user = type('MockUser ', (object,), {
                    'name': name, 'crop': crop, 'location_ml': location_ml, 'farm_size': farm_size,
                    'soil': soil, 'irrigation_type': irrigation_type, 'lat': lat, 'lon': lon, 'id': 1
                })()
                st.success(f"✅ Mock login for {name}. (Create database.py for real save.)")
                st.rerun()
        else:
            st.warning("Please fill name, username, and phone.")

# Post-Login Sections
if st.session_state.logged_in:
    user = st.session_state.user
    st.header(f"🌾 Hi {user.name}! Your Farm: {getattr(user, 'crop', 'General')} in {getattr(user, 'location_ml', 'Your Area')} | Size: {getattr(user, 'farm_size', 2.0)} Acres")

    # Weather Section
    st.header("☁️ Weather Forecast")
    location = st.text_input("Enter Location (e.g., Kochi)", value=getattr(user, 'location_ml', ''), key='weather_loc')
    if location:
        weather = get_weather(location)
        st.info(weather)
        if st.button("🔔 Send Weather Alert", key='weather_alert'):
            if st.session_state.fcm_token and FCM_AVAILABLE:
                success, msg = send_fcm_notification(
                    st.session_state.fcm_token,
                    "Weather Update",
                    f"Current weather in {location}: {weather}",
                    lang='en'
                )
                # Sanitize msg (Fix for exception)
                msg_str = str(msg).strip() if msg else "Unknown error"
                msg_clean = re.sub(r'<[^>]*>', '', msg_str)
                msg_display = msg_clean[:100] + "..." if len(msg_clean) > 100 else msg_clean
                if success:
                    st.success(msg_display)
                else:
                    st.error(msg_display)
            else:
                st.warning("Grant FCM permission or check setup. (Mock if no notifications.py)")

       # AI Section (Insert here – After sidebar/profile, e.g., after st.header("📊 Farmer Profile"))
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

    # Transcription helper function (Add this as a function above, or inline)
    def transcribe_audio(audio_file):
        if audio_file:
            try:
                import speech_recognition as sr
                import io
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
            except ImportError:
                st.error("Install speechrecognition: pip install speechrecognition pyaudio")
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
        user = st.session_state.get('user', {})  # Adapt to your session state (e.g., farmer_data)
        if not user:
            st.warning("⚠️ Please complete your profile first for personalized advice.")
            st.info("Go to profile section and set crop, location, etc.")
        else:
            # Generate response (From prior code – With lang_code)
            ai_response = generate_ai_response(query_text, user, lang_code)
            
            # Display
            st.success(f"**AI Advice ({selected_lang}):**")
            st.write(ai_response)
            
            # Step 6: Download (Only if response exists)
            if ai_response:
                filename = f"krishi_sakhi_advice_{getattr(user, 'name', 'farmer')}_{lang_code}.txt"
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
    if MAP_AVAILABLE:
        st.header("🗺️ Your Farm Map")
        lat = getattr(user, 'lat', 10.5276)  # Default: Thrissur lat
        lon = getattr(user, 'lon', 76.2144)  # Default: Thrissur lon
        farm_size = getattr(user, 'farm_size', 2.0)  # Default 2 acres
        
        try:
            # Create base map centered on farm
            m = folium.Map(location=[lat, lon], zoom_start=12, tiles='OpenStreetMap')
            
            # Add marker for farm location
            folium.Marker(
                [lat, lon], 
                popup=f"<b>{getattr(user, 'crop', 'Farm')} Farm</b><br>Location: {getattr(user, 'location_ml', 'Your Area')}<br>Size: {farm_size} acres<br>Soil: {getattr(user, 'soil', 'Loamy')}",
                tooltip="Click for farm details",
                icon=folium.Icon(color='green', icon='leaf')  # Green leaf icon for agriculture
            ).add_to(m)
            
            # Add circle to represent farm area (approximate radius: 1 acre ≈ 70m radius circle)
            radius_m = farm_size * 70 * 2  # Rough estimate for visualization (adjust as needed)
            folium.Circle(
                [lat, lon],
                radius=radius_m,
                popup=f"Farm Boundary ({farm_size} acres)<br>Irrigation: {getattr(user, 'irrigation_type', 'Drip')}",
                tooltip="Farm Area",
                color='blue',
                fill=True,
                fillColor='lightblue',
                fillOpacity=0.3
            ).add_to(m)
            
            # Add layer control (optional: toggle marker/circle)
            folium.LayerControl().add_to(m)
            
            # Render map in Streamlit
            folium_static(m, width=700, height=500)
            
        except Exception as e:
            st.error(f"Map rendering error: {str(e)}. Install folium and check coordinates.")
            st.info(f"Placeholder: Your farm is in {getattr(user, 'location_ml', 'your location')} – Use Google Maps for now.")
    else:
        st.header("🗺️ Your Farm Map (Coming Soon)")
        st.info(f"Map feature requires 'streamlit-folium'. Install it to visualize your {getattr(user, 'location_ml', 'location')} farm.")
        # Placeholder image
        st.image("https://images.unsplash.com/photo-1441974231531-c6227db76b6e?ixlib=rb-4.0.3&auto=format&fit=crop&w=700&h=400", caption="Sample Kerala Farm View")

    # Query History (If DB Available – Show Past Interactions)
    if DB_AVAILABLE and hasattr(user, 'id'):
        st.header("📋 Your Past Queries")
        try:
            # Fetch from DB (add this function to backend/database.py if needed)
            conn = sqlite3.connect('krishi.db')
            df = pd.read_sql_query("SELECT query, response, created_at FROM queries WHERE farmer_id = ? ORDER BY created_at DESC LIMIT 5", conn, params=(user.id,))
            conn.close()
            if not df.empty:
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No past queries yet. Ask something to start building your history!")
        except ImportError:
            st.warning("Pandas not installed for history table. pip install pandas")
        except Exception as e:
            st.error(f"History fetch error: {e}")

# Logout (In Sidebar for Easy Access)
with st.sidebar:
    if st.session_state.logged_in:
        st.header("👤 Profile")
        st.write(f"Logged in as: {st.session_state.username}")
        if st.button("🚪 Logout", key='logout_btn'):
            for key in ['logged_in', 'username', 'farmer_id', 'user', 'fcm_token', 'voice_transcript', 'ai_response']:
                if key in st.session_state:
                    del st.session_state[key]
            st.success("Logged out successfully!")
            st.rerun()
    else:
        st.info("Login to access personalized features.")

# Footer (Optional: App Info)
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>🌱 Krishi Sakhi: AI-Powered Farmer Assistant | Built with Streamlit & Firebase</p>
    <p>For issues: Check console (F12) or add API keys to .env</p>
</div>
""", unsafe_allow_html=True)
