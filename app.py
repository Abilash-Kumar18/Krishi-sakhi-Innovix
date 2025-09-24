import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from livekit import api, rtc
import os
import uuid

# Page config
st.set_page_config(
    page_title="Krishi Sakhi - കൃഷി സഖി",
    layout="wide"
)

# Initialize session state
if 'profile' not in st.session_state:
    st.session_state.profile = {}
if 'show_profile' not in st.session_state:
    st.session_state.show_profile = False
if 'show_chat' not in st.session_state:
    st.session_state.show_chat = False
if 'weather_data' not in st.session_state:
    st.session_state.weather_data = None
if 'room_name' not in st.session_state:
    st.session_state.room_name = None
if 'access_token' not in st.session_state:
    st.session_state.access_token = None
if 'messages' not in st.session_state:
    st.session_state.messages = []

# LiveKit Config (use secrets in cloud)
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "wss://your-project.livekit.cloud")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "your_key")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "your_secret")

# Function to generate LiveKit access token
@st.cache_data(ttl=3600)  # Cache for 1 hour
def generate_livekit_token(room_name, participant_name="farmer"):
    lk_api = api.LiveKitAPI(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    
    # Create or get room
    try:
        room = lk_api.room.create_room(
            name=room_name,
            empty_timeout=300,  # Auto-close after 5 mins idle
            max_participants=2  # Farmer + Agent
        )
    except:
        # Room exists, ignore
        pass
    
    # Generate token for participant (publish audio, receive transcriptions)
    token = lk_api.room.create_access_token(
        identity=participant_name,
        name="Krishi Sakhi Farmer",
        room_join=True,
        room=room_name,
        can_publish=True,  # Mic audio
        can_subscribe=True,  # Receive agent responses
        video_grants=api.VideoGrants(
            room_publish=False,
            room_subscribe=False,
            room_create=False
        ),
        metadata="farmer_voice"  # For agent to identify
    )
    return token.to_jwt()

# Other functions (coordinates, weather) remain the same as previous version
def get_coordinates(city_name):
    url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
    headers = {"User -Agent": "KrishiSakhiApp/1.0"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            location_data = response.json()
            if location_data:
                location = location_data[0]
                return float(location['lat']), float(location['lon'])
        st.warning("സ്ഥലം കണ്ടെത്താനായില്ല.")
        return None, None
    except Exception as e:
        st.error(f"API തെറ്റ്: {str(e)}")
        return None, None

def get_weather_data(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,precipitation_probability,relative_humidity_2m,wind_speed_10m&forecast_days=2&timezone=Asia/Kolkata"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            st.error("കാലാവസ്ഥ ഡാറ്റ ലഭ്യമല്ല.")
            return None
    except Exception as e:
        st.error(f"API തെറ്റ്: {str(e)}")
        return None

# Title and sections (welcome, profile) remain the same as previous no-emoji version
st.title("സ്വാഗതം! Krishi Sakhi - കൃഷി സഖി")
st.markdown("---")

if not st.session_state.show_profile and not st.session_state.show_chat:
    st.header("നിങ്ങളുടെ പ്രൊഫൈൽ സജ്ജീകരിക്കുക")
    st.write("കൃഷി സഹായത്തിനായി നിങ്ങളുടെ വിവരങ്ങൾ പൂരിപ്പിക്കുക.")
    
    if st.button("പ്രൊഫൈൽ സജ്ജീകരിക്കുക (Set Profile)", use_container_width=True):
        st.session_state.show_profile = True
        st.rerun()
    
    st.markdown("---")
    st.write("*ഉദാഹരണം: തൃശ്ശൂർ, ബ്രിൻജാൽ, ചെറു നാട്ടിൻപുറം*")

elif st.session_state.show_profile:
    st.header("നിങ്ങളുടെ പ്രൊഫൈൽ (Your Profile)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        location = st.selectbox("സ്ഥലം (Location)", ["തൃശ്ശൂർ (Thrissur)", "കൊച്ചി (Kochi)", "കോഴിക്കോട് (Kozhikode)", "മറ്റ് (Other)"])
        crop = st.selectbox("പ്രധാന വിള (Main Crop)", ["ബ്രിൻജാൽ (Brinjal)", "പച്ചക്കറി (Vegetables)", "മരം (Trees)", "മറ്റ് (Other)"])
    
    with col2:
        soil = st.selectbox("മണ്ണിന്റെ തരം (Soil Type)", ["ചെറു നാട്ടിൻപുറം (Sandy Loam)", "കള്ളമണ്ണ് (Clay)", "മറ്റ് (Other)"])
        experience = st.slider("കൃഷി അനുഭവം (Years of Experience)", 0, 30, 5)
    
    if st.button("പ്രൊഫൈൽ സേവ് ചെയ്യുക (Save Profile)", use_container_width=True):
        st.session_state.profile = {
            'location': location.split(' (')[0],
            'crop': crop.split(' (')[0],
            'soil': soil.split(' (')[0],
            'experience': experience
        }
        st.session_state.show_profile = False
        st.session_state.show_chat = True
        st.success("പ്രൊഫൈൽ സേവ് ചെയ്തു!")
        st.rerun()
    
    if st.button("അടങ്ങൾ (Back to Welcome)"):
        st.session_state.show_profile = False
        st.rerun()

# Chat Section with LiveKit Voice
elif st.session_state.show_chat:
    location = st.session_state.profile.get('location', 'Thrissur')
    st.header(f"ചാറ്റ് - {st.session_state.profile.get('crop', 'വിള')} വിളയ്ക്കുള്ള ഉപദേശം")
    
    st.subheader("നിങ്ങളുടെ പ്രൊഫൈൽ (Your Profile):")
    profile_str = f"സ്ഥലം: {st.session_state.profile.get('location', 'N/A')}, വിള: {st.session_state.profile.get('crop', 'N/A')}, മണ്ണ്: {st.session_state.profile.get('soil', 'N/A')}, അനുഭവം: {st.session_state.profile.get('experience', 0)} വർഷം"
    st.write(profile_str)
    
    # Weather section (same as before)
    st.subheader(f"{location}യിലെ കാലാവസ്ഥ (Weather in {location})")
    
    if st.button("കാലാവസ്ഥ അപ്ഡേറ്റ് ലഭിക്കുക (Get Weather Update)", use_container_width=True):
        lat, lon = get_coordinates(location)
        if lat and lon:
            st.session_state.weather_data = get_weather_data(lat, lon)
            st.rerun()
    
    if st.session_state.weather_data:
        data = st.session_state.weather_data
        forecast_hours = 24
        times = [datetime.now() + timedelta(hours=i) for i in range(forecast_hours)]
        
        df = pd.DataFrame({"Time": times})
        df["Temperature (°C)"] = data['hourly']['temperature_2m'][:forecast_hours]
        df["Rain Probability (%)"] = data['hourly']['precipitation_probability'][:forecast_hours]
        df["Humidity (%)"] = data['hourly']['relative_humidity_2m'][:forecast_hours]
        df["Wind Speed (km/h)"] = [speed * 3.6 for speed in data['hourly']['wind_speed_10m'][:forecast_hours]]
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("താപനില (Temperature)", f"{df['Temperature (°C)'][0]:.1f}°C")
        with col2:
            st.metric("മഴ സാധ്യത (Rain Prob)", f"{df['Rain Probability (%)'][0]}%")
        with col3:
            st.metric("ഈർപ്പം (Humidity)", f"{df['Humidity (%)'][0]}%")
        with col4:
            st.metric("കാറ്റ് (Wind)", f"{df['Wind Speed (km/h)'][0]:.1f} km/h")
        
        st.subheader("അടുത്ത 24 മണിക്കൂറിന്റെ പ്രവചനം (24-Hour Forecast)")
        col_temp, col_rain = st.columns(2)
        with col_temp:
            st.line_chart(df.set_index("Time")["Temperature (°C)"], use_container_width=True)
            st.caption("താപനില (Temperature)")
        with col_rain:
            st.line_chart(df.set_index("Time")["Rain Probability (%)"], use_container_width=True)
            st.caption("മഴ സാധ്യത (Rain Probability)")
        
        if df['Rain Probability (%)'][0] > 50:
            st.warning(f"മഴ സാധ്യത ഉയർന്നു ({df['Rain Probability (%)'][0]}%). {st.session_state.profile.get('crop', 'വിള')}യ്ക്ക് ജലസേചനം കുറയ്ക്കുക.")
        elif df['Temperature (°C)'][0] > 35:
            st.info(f"ഉയർന്ന താപനില ({df['Temperature (°C)'][0]}°C). {st.session_state.profile.get('crop', 'വിള')}യ്ക്ക് നിഴൽ നൽകുക.")
    
    else:
        st.info("കാലാവസ്ഥ ഡാറ്റ ലഭ്യമല്ല. ബട്ടൺ ക്ലിക്ക് ചെയ്യുക.")
    
    st.markdown("---")
    
    # Chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # LiveKit Voice Mode
    st.subheader("Voice Mode with LiveKit (സ്പീക്ക് ചെയ്യുക)")
    
    if st.button("Start Voice Chat (മൈക്ക് ഓൺ)", use_container_width=True):
        if not st.session_state.room_name:
            st.session_state.room_name = f"krishi-room-{uuid.uuid4().hex[:8]}"
        
        st.session_state.access_token = generate_livekit_token(st.session_state.room_name)
        
        # Embed LiveKit JS Client
        livekit_js = f"""
        <script src="https://cdn.jsdelivr.net/npm/livekit-client@2/dist/livekit-client.umd.min.js"></script>
        <script>
        async function initLiveKit() {{
            const room = new LivekitClient.Room();
            const token = '{st.session_state.access_token}';
            const url = '{LIVEKIT_URL}';
            
            // Connect to room
            await room.connect(url, token);
            
            // Enable mic (audio only)
            const audioTrack = await LivekitClient.createLocalAudioTrack({{
                echoCancellation: true,
                noiseSuppression: true
            }});
            room.localParticipant.publishTrack(audioTrack);
            
            // Listen for transcriptions from agent (STT events)
            room.on(LivekitClient.RoomEvent.TrackSubscribed, (track, publication, participant) => {{
                if (publication.kind === 'data' && publication.name === 'transcription') {{
                    track.on(LivekitClient.TrackEvent.DataReceived, (data) => {{
                        const transcript = new TextDecoder().decode(data);
                        // Send transcript to Streamlit chat (simulate input)
                        window.parent.document.querySelector('textarea[placeholder*="query"]').value = transcript;
                        // Or use postMessage for advanced callback
                        console.log('Transcribed: ' + transcript);
                    }});
                }}
            }});
            
            // For TTS: Publish bot audio (if agent sends)
            room.on(LivekitClient.RoomEvent.TrackSubscribed, (track) => {{
                if (track.kind === 'audio' && track.source === 'screen') {{  // Bot TTS track
                    // Auto-play bot audio
                    document.body.appendChild(track.attach());
                }}
            }});
            
            // Error handling
            room.on(LivekitClient.RoomEvent.Disconnected, () => {{
                alert('Voice session ended.');
            }});
            
            // Start agent (STT/TTS via LiveKit Agents API - call your agent endpoint)
            fetch('/agent-start', {{  // Backend endpoint for agent
                method: 'POST',
                body: JSON.stringify({{room: '{st.session_state.room_name}', lang: 'ml-IN'}}),
                headers: {{'Content-Type': 'application/json'}}
            }});
        }}
        initLiveKit().catch(console.error);
        </script>
        <p>Voice chat started. Speak now! (Mic permission required)</p>
        """
        st.components.v1.html(livekit_js, height=200)
    
    # Fallback text input
    prompt = st.chat_input("നിങ്ങളുടെ ചോദ്യം ഇവിടെ ടൈപ്പ് ചെയ്യുക")
