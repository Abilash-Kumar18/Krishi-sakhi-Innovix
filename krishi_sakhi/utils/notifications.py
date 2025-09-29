# utils/notifications.py – Real Firebase FCM Push Notifications
import streamlit as st
import firebase_admin
from firebase_admin import credentials, messaging
from firebase_admin.exceptions import FirebaseError
import os
from dotenv import load_dotenv
from datetime import datetime
import json

load_dotenv()

# Initialize Firebase (Cloud/Local Safe)
@st.cache_resource
def init_firebase():
    try:
        # Cloud secrets first
        creds_dict = st.secrets.get("FIREBASE_CREDENTIALS")
        if not creds_dict:
            # Local fallback: Load from JSON file (add to .gitignore)
            creds_path = os.getenv('FIREBASE_CREDENTIALS_PATH', 'krishi-sakhi-firebase-adminsdk.json')
            if os.path.exists(creds_path):
                creds = credentials.Certificate(creds_path)
            else:
                raise ValueError("No Firebase creds found.")
        else:
            creds = credentials.Certificate(json.loads(creds_dict))
        
        firebase_admin.initialize_app(creds)
        return True
    except Exception as e:
        st.error(f"Firebase init error: {str(e)}. Notifications disabled.")
        return False

def send_fcm_notification(title, body, fcm_token):
    """
    Send push via FCM to device token.
    Returns True if sent.
    """
    if not init_firebase():
        return False
    
    try:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            token=fcm_token,
        )
        response = messaging.send(message)
        st.success(f"Push sent! Message ID: {response}")
        return True
    except FirebaseError as e:
        st.error(f"FCM error: {e} (Check token validity).")
        return False
    except Exception as e:
        st.error(f"Notification send failed: {str(e)}.")
        return False

def send_real_notification(message, alert_type="info", user_profile=None, fcm_token=None):
    """
    Send FCM push.
    - fcm_token: From profile (e.g., browser token).
    """
    if not user_profile or not user_profile.get('fcm_token'):
        st.warning("No FCM token in profile. Register device for push alerts.")
        return False

    fcm_token = fcm_token or user_profile.get('fcm_token')
    name = user_profile.get('name', 'Farmer')
    timestamp = datetime.now().strftime("%d/%m %H:%M")
    subject_prefix = {"info": "Info", "warning": "Alert", "error": "Urgent", "success": "Update"}.get(alert_type, "Note")
    
    title = f"{subject_prefix}: Krishi Sakhi"
    body = f"Hi {name}, {message} ({timestamp})"
    
    success = send_fcm_notification(title, body, fcm_token)
    if success:
        st.success("🔔 Push notification sent to your device!")
    return success

# No tests (clean)
