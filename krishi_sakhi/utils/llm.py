from huggingface_hub import InferenceClient
import os
from dotenv import load_dotenv
load_dotenv()

def generate_ai_response(query, farmer_data):
    client = InferenceClient(token=os.getenv("HUGGINGFACE_API_KEY"))
    if not client.token:
        return "AI unavailable. Add HUGGINGFACE_API_KEY to .env."
    
    profile_str = f"Farmer: {getattr(farmer_data, 'name', 'Unknown')}, Crop: {getattr(farmer_data, 'crop', 'general')}, Location: {getattr(farmer_data, 'location_ml', 'your area')}."
    prompt = f"As a farming expert for Indian farmers, advise on: {query}. {profile_str} Keep simple, actionable, in English."
    
    try:
        response = client.text_generation(prompt, model="gpt2", max_new_tokens=100, temperature=0.7, do_sample=True)
        return response
    except Exception as e:
        return f"AI error: {str(e)}. Sample: Use organic methods for {query}."
