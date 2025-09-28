import firebase_admin
from firebase_admin import credentials, messaging
from dotenv import load_dotenv
import os
load_dotenv()

def send_fcm_notification(token, title, body, lang='en'):
    if "fallback_mock" in str(token):
        mock_msg = f"Mock alert simulated: {title} - {body[:50]}..."
        print(f"🔔 MOCK: {title} to {token} | Body: {body}")
        return True, mock_msg  # Plain string
    
    # Real send (init if needed)
    try:
        if not firebase_admin._apps:
            cred_path = os.getenv('FIREBASE_KEY_JSON_PATH', 'firebase_key.json')
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            token=token,
        )
        response = messaging.send(message)
        real_msg = f"Real notification sent (ID: {response})"  # str(response) if needed
        print(f"✅ REAL: {title} | Response: {response}")
        return True, real_msg  # Plain string
    
    except Exception as e:
        error_msg = f"Send failed: {str(e)}"
        print(f"❌ ERROR: {error_msg}")
        return False, error_msg  # Plain string
