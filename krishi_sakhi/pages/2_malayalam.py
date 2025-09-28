# pages/2_malayalam.py – Standalone Malayalam Page (Fixed: Safe User Dict Handling)
import streamlit as st
import os
from dotenv import load_dotenv
import speech_recognition as sr
import io
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError
from huggingface_hub import InferenceClient
from transformers import pipeline
import torch

load_dotenv()  # Load HF_TOKEN

@st.cache_resource
def get_hf_client():
    token = os.getenv('HF_TOKEN')
    if token:
        return InferenceClient(token=token)
    st.error("HF_TOKEN missing in .env file.")
    return None

def generate_ai_response(query, farmer_data, lang_code="ml"):
    # Ensure farmer_data is dict (safety)
    if not isinstance(farmer_data, dict):
        farmer_data = {}
    
    client = get_hf_client()
    if not client:
        return "AI ലഭ്യമല്ല. .env-ൽ HF_TOKEN ചേർക്കുക."

    # Profile string (English for AI consistency)
    profile_str = f"Crop: {farmer_data.get('crop', 'General')}, Location: {farmer_data.get('location', 'Your area')}, Soil: {farmer_data.get('soil', 'Loamy')}, Farm Size: {farmer_data.get('farm_size', 2)} acres."

    system_content = """You are Krishi Sakhi, an AI farming expert for Indian farmers in Kerala. Provide simple, practical advice in English. Focus on sustainable, step-by-step guidance. Structure responses with numbered steps if possible."""
    
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": f"Query: {query}. Farmer Profile: {profile_str}. Advise in Indian agriculture context."}
    ]

    try:
        with st.spinner("AI ഫാമിങ് ഉപദേശം ജനറേറ്റ് ചെയ്യുന്നു..."):
            completion = client.chat.completions.create(
                model="HuggingFaceTB/SmolLM3-3B",
                messages=messages,
                max_tokens=300,
                temperature=0.3,
                top_p=0.9
            )
            english_response = completion.choices[0].message.content.strip()

        # Translate to Malayalam
        response = english_response
        try:
            with st.spinner("മലയാളത്തിലേക്ക് പരിഭാഷപ്പെടുത്തുന്നു..."):
                translation_result = client.post(
                    model="Helsinki-NLP/opus-mt-en-ml",
                    json={"inputs": english_response}
                )
                if isinstance(translation_result, list) and len(translation_result) > 0:
                    response = translation_result[0].get('translation_text', english_response)
                else:
                    raise ValueError("Invalid API response")
            st.success("പരിഭാഷ വിജയകരം!")
        except Exception as api_e:
            st.warning(f"API translation unavailable ({str(api_e)}). Using local...")
            response = translate_local(english_response, "en", "ml")
        return response if response else "No advice generated."
    except Exception as e:
        st.error(f"AI Error: {str(e)}")
        return "പേസ്റ്റിന്, നിങ്ങളുടെ ഫലത്തിൽ നീമെണ്ണ സ്പ്രേ ഉപയോഗിക്കുക."

@st.cache_resource
def load_translator():
    try:
        device = 0 if torch.cuda.is_available() else -1
        translator = pipeline(
            "translation",
            model="Helsinki-NLP/opus-mt-en-ml",
            device=device,
            torch_dtype=torch.float16 if device == 0 else None
        )
        return translator
    except Exception as load_e:
        st.error(f"Model load failed: {str(load_e)}")
        return None

def translate_local(text, src_lang, tgt_lang):
    translator = load_translator()
    if translator is None:
        return text
    try:
        result = translator(text, max_length=400, min_length=10)
        return result[0]['translation_text']
    except Exception as local_e:
        st.warning(f"Local translation error: {str(local_e)}")
        return text

def transcribe_audio(audio_file, lang_code="ml"):
    if audio_file is None:
        return None
    try:
        audio_file.seek(0)
        audio_bytes = audio_file.read()
        audio_file.seek(0)
        file_extension = audio_file.name.lower().split('.')[-1] if audio_file.name else 'wav'
        
        if file_extension in ['wav', 'aiff', 'flac']:
            wav_bytes = io.BytesIO(audio_bytes)
        else:
            try:
                audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format=file_extension)
                audio_segment = audio_segment.set_frame_rate(16000).set_channels(1)
                wav_buffer = io.BytesIO()
                audio_segment.export(wav_buffer, format="wav")
                wav_bytes = io.BytesIO(wav_buffer.getvalue())
                st.info(f"{file_extension.upper()}-നെ WAV-ലേക്ക് മാറ്റി.")
            except CouldntDecodeError:
                st.error(f"{file_extension} ഫയൽ ഡീകോഡ് ചെയ്യാനായില്ല. WAV ഉപയോഗിക്കുക.")
                return None
            except Exception as conv_e:
                st.error(f"കൺവേർഷൻ പിശക്: {str(conv_e)}")
                return None
        
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_bytes) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio_data = recognizer.record(source)
        
        language = 'ml-IN'
        text = recognizer.recognize_google(audio_data, language=language)
        st.success(f"🎤 പരിഭാഷപ്പെടുത്തി: '{text}'")
        return text.strip()
    except sr.UnknownValueError:
        st.error("ഓഡിയോ മനസ്സിലായില്ല.")
        return None
    except sr.RequestError as req_e:
        st.error(f"സേവന പിശക്: {str(req_e)}")
        return None
    except Exception as general_e:
        st.error(f"ഓഡിയോ പിശക്: {str(general_e)}")
        return None

st.set_page_config(page_title="ക്രിഷി സഖി - മലയാളം", page_icon="🌾")

st.title("🌾 ക്രിഷി സഖി - കർഷക സഖി")
st.write("കേരളത്തിലെ കർഷകർക്കായുള്ള AI അധിഷ്ഠിത ഉപദേശം. പ്രൊഫൈൽ പൂർത്തിയാക്കി ചോദ്യങ്ങൾ ചോദിക്കുക.")

# Sidebar (Fixed: Safe Dict Default - No AttributeError)
st.sidebar.header("👤 ഉപയോക്താവ് / User")
user = st.session_state.get('user', {})  # Safe: Always dict
if user:  # Check if non-empty dict
    st.sidebar.write(f"പേര്: {user.get('name', 'അജ്ഞാതൻ')}")
    st.sidebar.write(f"ഫലം: {user.get('crop', 'പൊതു')}")
else:
    st.sidebar.info("👋 സ്വാഗതം, കർഷകാ! പ്രൊഫൈൽ സേവ് ചെയ്യുക വ്യക്തിഗത ഉപദേശത്തിന്.")

# Profile Section (Safe: Form + Display)
st.header("📊 കർഷക പ്രൊഫൈൽ / Farmer Profile")
if not user or st.button("പ്രൊഫൈൽ അപ്ഡേറ്റ് / Update Profile"):  # Safe check
    with st.form("profile_form_ml"):
        name = st.text_input("പേര് / Name", placeholder="രാം", key="name_ml")
        crop_options = ["Rice (അരി)", "Brinjal (വഴുതനങ്ങ)", "Coconut (തെങ്ങ്)", "Rubber", "General"]
        crop = st.selectbox("ഫലം / Crop", crop_options, key="crop_ml")
        location_ml = st.text_input("സ്ഥലം / Location", placeholder="തൃശ്ശൂർ", key="loc_ml")
        soil_options = ["Loamy (കളിമണ്ണ്)", "Sandy (മണൽ)", "Clay (ചെളി)", "Red"]
        soil = st.selectbox("മണ്ണ് തരം / Soil Type", soil_options, key="soil_ml")
        farm_size = st.number_input("ഫാം വലുപ്പം (ഏക്കർ) / Farm Size (Acres)", min_value=0.1, value=2.0, key="size_ml")
        
        submitted = st.form_submit_button("സേവ് / Save")
        if submitted:
            st.session_state['user'] = {  # Always dict
                'name': name,
                'crop': crop.split(' (')[0] if '(' in crop else crop,  # English value
                'location': location_ml,
                'soil': soil.split(' (')[0] if '(' in soil else soil,
                'farm_size': farm_size
            }
            st.success("പ്രൊഫൈൽ സേവ് ചെയ്തു! 🌾")
            st.rerun()  # Refresh to update sidebar

# Display Profile (Fixed: Safe Columns)
user = st.session_state.get('user', {})  # Re-fetch safe
if user:
    st.subheader("നിങ്ങളുടെ പ്രൊഫൈൽ / Your Profile")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**പേര്:** {user.get('name', 'N/A')}")
        st.write(f"**ഫലം:** {user.get('crop', 'N/A')}")
    with col2:
        st.write(f"**സ്ഥലം:** {user.get('location', 'N/A')}")
        st.write(f"**മണ്ണ്:** {user.get('soil', 'N/A')}")
        st.write(f"**ഫാം വലുപ്പം:** {user.get('farm_size', 0)} ഏക്കർ")
else:
    st.info("⚠️ പ്രൊഫൈൽ പൂർത്തിയാക്കുക വ്യക്തിഗത ഉപദേശത്തിന്.")

# AI Section (Already Safe)
st.header("🗣️ ക്രിഷി സഖി ചോദിക്കുക / Ask Krishi Sakhi")
st.write("കൃഷി ചോദ്യം ടൈപ്പ് ചെയ്യുക അല്ലെങ്കിൽ സ്പീക്ക് ചെയ്യുക (ഉദാ: 'അരിക്ക് പേസ്റ്റ് കൺട്രോൾ') / Type or speak a farming question.")

query_text = ""

# Voice Input
st.subheader("🎤 ശബ്ദ ചോദ്യം / Voice Query (Optional)")
audio_file = st.file_uploader(
    "ഓഡിയോ ഫയൽ തിരഞ്ഞെടുക്കുക / Choose Audio File", 
    type=['wav', 'mp3', 'm4a', 'ogg'], 
    key="audio_ml",
    help="1MB max, 10-30s clips. Phone recorder OK."
)
if audio_file and audio_file.size > 1_000_000:
    st.error("ഫയൽ വലുതാണ് (>1MB). ഹ്രസ്വമായ ഓഡിയോ ഉപയോഗിക്കുക.")
    audio_file = None

if audio_file is not None:
    transcribed = transcribe_audio(audio_file, "ml")
    if transcribed:
        query_text = transcribed

# Text Input
st.subheader("⌨️ ടെക്സ്റ്റ് ചോദ്യം / Text Query")
query_text = st.text_input(
    "നിങ്ങളുടെ ചോദ്യം / Your Question:",
    value=query_text,
    placeholder="അരിക്ക് പേസ്റ്റ് കൺട്രോൾ എങ്ങനെ? / How to control pests in rice?",
    key="query_ml"
)

# Process Query (Safe User)
if query_text.strip():
    user = st.session_state.get('user', {})  # Safe default
    if not user:
        st.warning("⚠️ പ്രൊഫൈൽ പൂർത്തിയാക്കുക / Complete profile for better advice.")
    ai_response = generate_ai_response(query_text, user, "ml")
    st.success("**AI ഉപദേശം (മലയാളം) / AI Advice:**")
    st.write(ai_response)
    
    # Download (Safe Filename)
    if ai_response:
        filename = f"krishi_sakhi_advice_{user.get('name', 'കർഷകൻ')}_ml.txt"
        st.download_button(
            label="📥 ഉപദേശം ഡൗൺലോഡ് / Download Advice (TXT)",
            data=ai_response.encode('utf-8'),
            file_name=filename,
            mime="text/plain"
        )

# Clear Button (Resets UI; Keeps Profile)
if st.button("എല്ലാം ക്ലിയർ / Clear All"):
    st.rerun()

# Optional: Reset Profile Button (If String Issue Persists)
if st.button("പ്രൊഫൈൽ റീസെറ്റ് / Reset Profile (Debug)"):
    if 'user' in st.session_state:
        del st.session_state['user']
    st.success("പ്രൊഫൈൽ റീസെറ്റ് ചെയ്തു! പുതിയത് സേവ് ചെയ്യുക.")
    st.rerun()

# Footer
st.markdown("---")
st.markdown("""
**കേരള കർഷകർക്കായി ❤️ ഉണ്ടാക്കിയത്** | Hugging Face & Streamlit വഴി AI ഉപദേശം.
""")
