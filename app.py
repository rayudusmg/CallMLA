from flask import Flask, request, send_from_directory, Response
import requests
import os
import logging
from dotenv import load_dotenv
import json

# Load environment variables from .env file if it exists
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static')

# Configuration variables
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "your_elevenlabs_api_key")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "your_elevenlabs_voice_id")
# Exotel credentials
EXOTEL_API_KEY = os.environ.get("EXOTEL_API_KEY", "your_exotel_api_key") 
EXOTEL_API_TOKEN = os.environ.get("EXOTEL_API_TOKEN", "your_exotel_api_token")
EXOTEL_SID = os.environ.get("EXOTEL_SID", "your_exotel_sid")
EXOTEL_SUBDOMAIN = os.environ.get("EXOTEL_SUBDOMAIN", "your_exotel_subdomain")
AUDIO_FILENAME = "mla-response.mp3"
AUDIO_DIR = os.path.join("static", "audio")
AUDIO_PATH = os.path.join(AUDIO_DIR, AUDIO_FILENAME)

# Ensure audio directory exists
os.makedirs(AUDIO_DIR, exist_ok=True)

def generate_telugu_audio(text):
    """
    Generate Telugu audio using ElevenLabs API and save it to a file
    
    Args:
        text (str): Telugu text to convert to speech
        
    Returns:
        bool: True if audio generation was successful, False otherwise
    """
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",  # Using multilingual model for Telugu support
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }
    
    try:
        logger.info(f"Generating audio for Telugu text: {text}")
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 200:
            # Save the audio file
            with open(AUDIO_PATH, "wb") as audio_file:
                audio_file.write(response.content)
            logger.info(f"Audio saved to {AUDIO_PATH}")
            return True
        else:
            logger.error(f"Failed to generate audio: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error generating audio: {str(e)}")
        return False

def create_twiml_response(audio_url):
    """
    Create TwiML response with Play tag
    
    Args:
        audio_url (str): Full URL to the audio file
        
    Returns:
        Response: Flask response object with TwiML XML
    """
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{audio_url}</Play>
</Response>"""
    return Response(twiml, mimetype='text/xml')

@app.route('/audio/<path:filename>')
def serve_audio(filename):
    """
    Serve the generated audio file
    
    Args:
        filename (str): Name of the audio file to serve
        
    Returns:
        Response: Flask response with audio file
    """
    return send_from_directory('static/audio', filename)

@app.route('/voice-response', methods=['POST'])
def voice_response():
    """
    Handle incoming Exotel calls and respond with TwiML
    
    Expected POST parameters from Exotel:
    - CallSid: Unique call identifier
    - CallFrom: Caller's phone number
    - CallTo: Called phone number
    - message (optional): Telugu message to convert to speech
    
    Returns:
        Response: TwiML response with Play tag or error message
    """
    try:
        # Log call details
        call_sid = request.form.get('CallSid', 'Unknown')
        call_from = request.form.get('CallFrom', 'Unknown')
        logger.info(f"Received call: SID={call_sid}, From={call_from}")
        
        # Get Telugu message from request or use default
        telugu_message = request.form.get('message', "మీరు ఎవరు చెప్పండి, మీ సమస్య ఏమిటి?")
        
        # Generate audio for the Telugu message
        success = generate_telugu_audio(telugu_message)
        
        if success:
            # Create the full audio URL (including domain)
            audio_url = request.host_url.rstrip('/') + '/audio/' + AUDIO_FILENAME
            logger.info(f"Audio URL: {audio_url}")
            
            # Generate and return TwiML response
            return create_twiml_response(audio_url)
        else:
            # Return error response if audio generation failed
            logger.error("Failed to generate audio, returning error response")
            return Response("Failed to generate audio", status=500, mimetype='text/plain')
    
    except Exception as e:
        logger.exception(f"Error processing voice response: {str(e)}")
        return Response("Internal server error", status=500, mimetype='text/plain')

@app.route('/health', methods=['GET'])
def health_check():
    """
    Simple health check endpoint
    """
    return Response("OK", status=200, mimetype='text/plain')

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Webhook endpoint to receive incoming data from external services
    
    Returns:
        Response: JSON response with status of the webhook processing
    """
    try:
        # Log webhook request
        logger.info("Received webhook request")
        
        # Get JSON data from the request
        data = request.get_json(silent=True) or {}
        
        if not data:
            # Try to get form data if JSON is not available
            data = request.form.to_dict() or {}
            
        logger.info(f"Webhook data received: {data}")
        
        # Process the webhook data here
        # This is where you would add your webhook processing logic
        
        # Return success response
        return Response(
            response=json.dumps({"status": "success", "message": "Webhook received"}),
            status=200, 
            mimetype='application/json'
        )
    
    except Exception as e:
        logger.exception(f"Error processing webhook: {str(e)}")
        return Response(
            response=json.dumps({"status": "error", "message": str(e)}),
            status=500, 
            mimetype='application/json'
        )

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "True").lower() == "true"
    
    logger.info(f"Starting Flask app on port {port}, debug={debug}")
    app.run(host='0.0.0.0', port=port, debug=debug)