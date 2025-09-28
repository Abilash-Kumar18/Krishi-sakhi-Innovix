# app.py – Main Multi-Page App Entry (Fixed for Session State)
import streamlit as st
if 'user' in st.session_state:
    st.write(f"Debug: Session user type = {type(st.session_state['user'])}, value = {st.session_state['user']}")
# Page Config (Applies to all pages)
st.set_page_config(
    page_title="Krishi Sakhi - Farmer AI Assistant",
    page_icon="🌾",
    layout="wide",  # Optional: Wider layout for forms
    initial_sidebar_state="expanded"
)

# Global Title/Header (Shows on all pages)
st.title("🌾 Krishi Sakhi - AI കർഷക സഹായി")
st.markdown("---")  # Horizontal line separator

# Optional: Global Sidebar (Shared across pages – E.g., app info)
with st.sidebar:
    st.header("📖 About / വിവരണം")
    st.write("AI-powered farming advice for Indian farmers (Kerala focus).")
    st.write("ഇന്ത്യൻ കർഷകർക്കായുള്ള AI അധിഷ്ഠിത കൃഷി ഉപദേശം (കേരളം ശ്രദ്ധ കേന്ദ്രീകരിച്ച്).")
    
    # Optional: Version or Credits
    st.info("Version 1.0 | Built with Streamlit & HuggingFace")
    
    # Safe User Display (Fixed: Check if user exists)
    if 'user' in st.session_state and st.session_state.user is not None:
        st.success(f"👋 Logged in: {st.session_state.user.get('name', 'Farmer')}")
    else:
        st.info("👋 Welcome, Farmer! Save your profile on the next page to get personalized advice.")
        # Optional: Reminder button (reruns to prompt profile)
        if st.button("🚀 Go to Profile"):
            st.switch_page("pages/1_english.py")  # Or 2_malayalam.py

# End of app.py – Streamlit auto-loads /pages files below this
# No more code needed! Sidebar will show: "1_english", "2_malayalam" automatically.

