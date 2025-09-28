import streamlit as st

def init_voice():
    if 'voice_transcript' not in st.session_state:
        st.session_state.voice_transcript = None

def speak_browser(text, lang='en-IN'):
    js_code = f"""
    <script>
    if ('speechSynthesis' in window) {{
        const utterance = new SpeechSynthesisUtterance('{text}');
        utterance.lang = '{lang}';
        speechSynthesis.speak(utterance);
    }} else {{
        alert('Text-to-Speech not supported.');
    }}
    </script>
    """
    st.components.v1.html(js_code, height=0)

def listen_browser():
    js_code = """
    <button id="listen-btn">🎤 Listen</button>
    <script>
    document.getElementById('listen-btn').onclick = function() {
        if ('webkitSpeechRecognition' in window) {
            const recognition = new webkitSpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'en-IN';  // Or 'ml-IN' for Malayalam
            recognition.onresult = function(event) {
                const transcript = event.results[0][0].transcript;
                // Hack to update Streamlit: Rerun with query param or use localStorage
                localStorage.setItem('voice_transcript', transcript);
                window.parent.location.reload();  // Simple rerun (improve later)
                alert('Heard: ' + transcript);  // Temp feedback
            };
            recognition.onerror = function(event) { alert('Voice error: ' + event.error); };
            recognition.start();
        } else {
            alert('Microphone not supported. Use text input.');
        }
    };
    </script>
    """
    st.components.v1.html(js_code, height=100)
    # On rerun, check localStorage (add to main code: st.session_state.voice_transcript = st.session_state.get('voice_transcript') or localStorage hack)
