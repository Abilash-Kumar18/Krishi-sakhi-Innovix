import streamlit as st
import json
import openai
from streamlit import secrets  # For cloud secrets
try:
    openai.api_key = st.secrets["OPENAI_API_KEY"]  
except KeyError:
    openai.api_key = None  # Fallback: Disable OpenAI if no secret
    st.warning("OpenAI not configured. Using rule-based responses only.")

# App title and theme
st.set_page_config(page_title="Krishi Sakhi", page_icon="🌱", layout="wide")
st.title("🌱 സ്വാഗതം! ഞാൻ നിങ്ങളുടെ കൃഷി സഖി (Welcome! I'm your Farming Friend)")

# Session state for profile and chat
if 'profile' not in st.session_state:
    st.session_state.profile = {}
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Sidebar navigation
page = st.sidebar.selectbox("പേജ് തിരഞ്ഞെടുക്കുക (Select Page)", ["ഹോം (Home)", "പ്രൊഫൈൽ (Profile)", "ചാറ്റ് (Chat)"])

if page == "ഹോം (Home)":
    st.header("കൃഷി സഖി എങ്ങനെ സഹായിക്കാം? (How can Krishi Sakhi Help?)")
    st.write("നിങ്ങളുടെ വിളകൾ, കീടങ്ങൾ, മഴ എന്നിവയെക്കുറിച്ച് ചോദിക്കൂ. (Ask about crops, pests, rain, etc.)")
    st.button("പ്രൊഫൈൽ സജ്ജീകരിക്കുക (Set Profile)", on_click=lambda: st.switch_page("app.py"))  # Redirect logic

elif page == "പ്രൊഫൈൽ (Profile)":
    st.header("നിങ്ങളുടെ വിശദാംശങ്ങൾ (Your Details)")
    with st.form("profile_form"):
        name = st.text_input("പേര് (Name)")
        location = st.selectbox("സ്ഥലം (Location)", ["തൃശ്ശൂർ", "വയനാട്", "കൊച്ചി", "കാസർഗോഡ്"])
        land_size = st.number_input("നിലം വലിപ്പം (Land Size in cents)", min_value=1.0)
        crop = st.selectbox("പ്രധാന വിള (Main Crop)", ["ബ്രിൻജാൽ (Brinjal)", "നെല്ല് (Rice)", "തെങ്ങ് (Coconut)", "മരച്ചീര (Banana)"])
        soil = st.selectbox("മണ്ണ് തരം (Soil Type)", ["മണൽ (Sandy)", "കളിമണ്ണ് (Loamy)", "കറുത്ത (Clay)"])
        submitted = st.form_submit_button("സേവ് ചെയ്യുക (Save)")
        if submitted:
            st.session_state.profile = {"name": name, "location": location, "land_size": land_size, "crop": crop, "soil": soil}
            st.success("പ്രൊഫൈൽ സേവ് ചെയ്തു! (Profile Saved!)")
            st.rerun()

elif page == "ചാറ്റ് (Chat)":
    if not st.session_state.profile:
        st.warning("ആദ്യം പ്രൊഫൈൽ പൂരിപ്പിക്കുക. (Complete profile first.)")
        st.stop()
    st.header(f"ഹായ് {st.session_state.profile['name']}! എന്താണ് ചോദിക്കാൻ? (Hi! What's your query?)")
    # Chat display (next step)
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User input
    if prompt := st.chat_input("നിങ്ങളുടെ ചോദ്യം ഇവിടെ ടൈപ്പ് ചെയ്യുക (Type your query here)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

    # In your generate_bot_response function, add a check:
    def generate_bot_response(user_input, profile):
        if openai.api_key is None:
            # Fallback to rule-based (your existing rules)
            user_input_lower = user_input.lower()
            # ... (your if-elif rules here, e.g., for 'മഴ', 'കീടം')
            return "Rule-based response: കൂടുതൽ വിശദാംശങ്ങൾ പറയൂ."  # Example fallback
        
        # OpenAI logic (only if key exists)
        else:
            context = f"Farmer profile: {profile}. User query: {user_input}. Respond in simple Malayalam about Kerala farming."
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are Krishi Sakhi, a helpful farming assistant. Respond in Malayalam."},
                        {"role": "user", "content": context}
                    ],
                    max_tokens=150
                )
                return response.choices[0].message.content
            except Exception as e:
                st.error(f"OpenAI error: {e}")
                return "ആശയക്കുഴപ്പം. വീണ്ടും ശ്രമിക്കുക. (Error. Try again.)"


