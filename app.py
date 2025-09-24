import streamlit as st

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
        location = st.selectbox("സ്ഥലം (Location)", ["തൃശ്ശൂർ", "കൊച്ചി", "കോഴിക്കോട്", "മറ്റ് (Other)"])
        crop = st.selectbox("പ്രധാന വിള (Main Crop)", ["ബ്രിൻജാൽ (Brinjal)", "പച്ചക്കറി (Vegetables)", "മരം (Trees)", "മറ്റ് (Other)"])
    
    with col2:
        soil = st.selectbox("മണ്ണിന്റെ തരം (Soil Type)", ["ചെറു നാട്ടിൻപുറം (Sandy Loam)", "കള്ളമണ്ണ് (Clay)", "മറ്റ് (Other)"])
        experience = st.slider("കൃഷി അനുഭവം (Years of Experience)", 0, 30, 5)
    
    # Submit Button
    if st.button("പ്രൊഫൈൽ സേവ് ചെയ്യുക (Save Profile)", use_container_width=True):
        st.session_state.profile = {
            'location': location,
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

# Chat Section
elif st.session_state.show_chat:
    st.header(f"💬 ചാറ്റ് - {st.session_state.profile.get('crop', 'വിള')} വിളയ്ക്കുള്ള ഉപദേശം (Chat - Advice for {st.session_state.profile.get('crop', 'Crop')})")
    
    # Display saved profile
    st.subheader("നിങ്ങളുടെ പ്രൊഫൈൽ (Your Profile):")
    profile_str = f"സ്ഥലം: {st.session_state.profile.get('location', 'N/A')}, വിള: {st.session_state.profile.get('crop', 'N/A')}, മണ്ണ്: {st.session_state.profile.get('soil', 'N/A')}, അനുഭവം: {st.session_state.profile.get('experience', 0)} വർഷം"
    st.write(profile_str)
    
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
        
        # Generate response (rule-based fallback)
        def generate_bot_response(user_input, profile):
            user_input_lower = user_input.lower()
            crop = profile.get('crop', '')
            location = profile.get('location', '')
            
            if 'മഴ' in user_input_lower or 'rain' in user_input_lower:
                return f"{location}യിൽ ഇന്ന് മഴ സാധ്യത 70%. {crop} വിളയ്ക്ക് ജലം കുറയ്ക്കുക. (Rain 70% in {location}. Reduce water for {crop}.)"
            elif 'കീടം' in user_input_lower or 'pest' in user_input_lower:
                return f"{crop}യിൽ കീടങ്ങൾ: നീരാളി സ്പ്രേ (10ml/ലിറ്റർ) ഉപയോഗിക്കുക. {profile.get('soil', '')} മണ്ണിന് അനുയോജ്യം. (Pests in {crop}: Use neem spray 10ml/liter. Suitable for {profile.get('soil', 'soil')}.)"
            elif 'വളം' in user_input_lower or 'fertilizer' in user_input_lower:
                return f"{profile.get('soil', 'മണ്ണ്')}യ്ക്ക് ഓർഗാനിക് കമ്പോസ്റ്റ് 2kg/സെന്റ്. (Organic compost 2kg/cent for your soil.)"
            else:
                return f"കൂടുതൽ വിശദാംശങ്ങൾ പറയൂ. ഉദാ: 'മഴ' അല്ലെങ്കിൽ 'കീടം'. (Tell more. E.g., 'rain' or 'pest'.)"
        
        with st.chat_message("assistant"):
            response = generate_bot_response(prompt, st.session_state.profile)
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
        
        st.rerun()
    
    # Back to profile edit
    if st.button("പ്രൊഫൈൽ എഡിറ്റ് (Edit Profile)"):
        st.session_state.show_chat = False
        st.session_state.show_profile = True
        st.rerun()
