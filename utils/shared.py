# utils.py – Shared Functions for English & Malayalam Pages
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

def generate_ai_response(query, farmer_data, lang_code="en"):  # Flexible lang param
  client = get_hf_client()
  if not client:
      if lang_code == "ml":
          return "AI ലഭ്യമല്ല. .env-ൽ HF_TOKEN ചേർക്കുക."
      return "AI unavailable. Add HF_TOKEN to .env."

  # Profile string (English for AI consistency; ML for display if needed)
  profile_str = f"Crop: {getattr(farmer_data, 'crop', 'General')}, Location: {getattr(farmer_data, 'location', 'Your area')}, Soil: {getattr(farmer_data, 'soil', 'Loamy')}, Farm Size: {getattr(farmer_data, 'farm_size', 2)} acres."

  system_content = """You are Krishi Sakhi, an AI farming expert for Indian farmers in Kerala. Provide simple, practical advice in English. Focus on sustainable, step-by-step guidance. Structure responses with numbered steps if possible."""
  
  messages = [
      {"role": "system", "content": system_content},
      {"role": "user", "content": f"Query: {query}. Farmer Profile: {profile_str}. Advise in Indian agriculture context."}
  ]

  try:
      with st.spinner("Generating AI farming advice..." if lang_code == "en" else "AI ഫാമിങ് ഉപദേശം ജനറേറ്റ് ചെയ്യുന്നു..."):
          completion = client.chat.completions.create(
              model="HuggingFaceTB/SmolLM3-3B",  # Or your preferred model
              messages=messages,
              max_tokens=300,  # Increased for detailed advice
              temperature=0.3,
              top_p=0.9
          )
          english_response = completion.choices[0].message.content.strip()

      # Translate if lang_code == "ml"
      if lang_code == "ml":
          response = english_response
          try:
              with st.spinner("Translating to Malayalam..." if lang_code == "en" else "മലയാളത്തിലേക്ക് പരിഭാഷപ്പെടുത്തുന്നു..."):
                  translation_result = client.post(
                      model="Helsinki-NLP/opus-mt-en-ml",
                      json={"inputs": english_response}
                  )
                  if isinstance(translation_result, list) and len(translation_result) > 0:
                      response = translation_result[0].get('translation_text', english_response)
                  else:
                      raise ValueError("Invalid API response")
              st.success("Translation successful!" if lang_code == "en" else "പരിഭാഷ വിജയകരം!")
          except Exception as api_e:
              st.warning(f"API translation unavailable ({str(api_e)}). Using local...")
              response = translate_local(english_response, "en", "ml")
      else:
          response = english_response

      return response if response else "No advice generated."
  except Exception as e:
      st.error(f"AI Error: {str(e)}")
      sample = "For pests, use neem oil spray on your crop." if lang_code == "en" else "പേസ്റ്റിന്, നിങ്ങളുടെ ഫലത്തിൽ നീമെണ്ണ സ്പ്രേ ഉപയോഗിക്കുക."
      return sample

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
      st.success("Translation model loaded!" if lang_code == "en" else "പരിഭാഷ മോഡൽ ലോഡ് ചെയ്തു!")
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

def transcribe_audio(audio_file, lang_code="en"):  # Flexible lang
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
              st.info(f"Converted {file_extension.upper()} to WAV." if lang_code == "en" else f"{file_extension.upper()}-നെ WAV-ലേക്ക് മാറ്റി.")
          except CouldntDecodeError:
              st.error(f"Could not decode {file_extension} file. Try WAV." if lang_code == "en" else f"{file_extension} ഫയൽ ഡീകോഡ് ചെയ്യാനായില്ല. WAV ഉപയോഗിക്കുക.")
              return None
          except Exception as conv_e:
              st.error(f"Conversion error: {str(conv_e)}" if lang_code == "en" else f"കൺവേർഷൻ പിശക്: {str(conv_e)}")
              return None
      
      recognizer = sr.Recognizer()
      with sr.AudioFile(wav_bytes) as source:
          recognizer.adjust_for_ambient_noise(source, duration=0.5)
          audio_data = recognizer.record(source)
      
      language = 'en-IN' if lang_code == "en" else 'ml-IN'  # Indian English or Malayalam
      text = recognizer.recognize_google(audio_data, language=language)
      st.success(f"🎤 Transcribed: '{text}'" if lang_code == "en" else f"🎤 പരിഭാഷപ്പെടുത്തി: '{text}'")
      return text.strip()
  except sr.UnknownValueError:
      st.error("Could not understand audio." if lang_code == "en" else "ഓഡിയോ മനസ്സിലായില്ല.")
      return None
  except sr.RequestError as req_e:
      st.error(f"Service error: {str(req_e)}" if lang_code == "en" else f"സേവന പിശക്: {str(req_e)}")
      return None
  except Exception as general_e:
      st.error(f"Audio error: {str(general_e)}" if lang_code == "en" else f"ഓഡിയോ പിശക്: {str(general_e)}")
      return None

