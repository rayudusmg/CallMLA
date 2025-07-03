from flask import Flask, request, send_from_directory, Response, render_template_string, redirect, url_for
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

# Flask error handlers
@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    logger.error(f"404 Error: {request.url} not found")
    logger.error(f"Request method: {request.method}")
    logger.error(f"Request headers: {dict(request.headers)}")
    return Response("Not Found", status=404, mimetype='text/plain')

@app.errorhandler(405)
def method_not_allowed_error(error):
    """Handle 405 errors"""
    logger.error(f"405 Error: Method {request.method} not allowed for {request.url}")
    logger.error(f"Request headers: {dict(request.headers)}")
    return Response("Method Not Allowed", status=405, mimetype='text/plain')

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"500 Error: Internal server error for {request.url}")
    logger.error(f"Request method: {request.method}")
    logger.error(f"Request headers: {dict(request.headers)}")
    logger.error(f"Error details: {str(error)}")
    logger.exception("Full traceback:")
    return Response("Internal Server Error", status=500, mimetype='text/plain')

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle all uncaught exceptions"""
    logger.error(f"Uncaught exception: {str(e)}")
    logger.error(f"Request URL: {request.url}")
    logger.error(f"Request method: {request.method}")
    logger.error(f"Request headers: {dict(request.headers)}")
    logger.exception("Full traceback:")
    return Response("Internal Server Error", status=500, mimetype='text/plain')

# Request logging middleware
@app.before_request
def log_request_info():
    """Log information about each request"""
    logger.info(f"Request: {request.method} {request.url}")
    logger.info(f"Remote address: {request.remote_addr}")
    logger.info(f"User agent: {request.user_agent}")

@app.after_request
def log_response_info(response):
    """Log information about each response"""
    logger.info(f"Response: {response.status_code} for {request.method} {request.url}")
    return response

@app.route('/')
def index():
    """
    Root endpoint with basic application information
    """
    logger.info("Root endpoint accessed")
    
    try:
        info = {
            "app_name": "CallMLA - Telugu Voice Response System",
            "version": "1.0.0",
            "endpoints": {
                "/voice-response": "POST - Handle incoming Exotel calls",
                "/audio/<filename>": "GET - Serve audio files",
                "/webhook": "POST - Receive webhook data",
                "/health": "GET - Health check",
                "/welcome": "GET - Welcome form",
                "/greet": "POST - Process greeting form"
            },
            "status": "running"
        }
        
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>CallMLA - Telugu Voice Response System</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
                h1 {{ color: #333; }}
                .info {{ background-color: #f5f5f5; padding: 20px; border-radius: 5px; margin-top: 20px; }}
                .endpoint {{ margin: 10px 0; padding: 10px; background-color: #e8f4f8; border-radius: 3px; }}
                .method {{ font-weight: bold; color: #007acc; }}
            </style>
        </head>
        <body>
            <h1>CallMLA - Telugu Voice Response System</h1>
            <div class="info">
                <h2>Application Information</h2>
                <p><strong>Status:</strong> {info['status']}</p>
                <p><strong>Version:</strong> {info['version']}</p>
                
                <h3>Available Endpoints:</h3>
                <div class="endpoint">
                    <span class="method">POST</span> /voice-response - Handle incoming Exotel calls
                </div>
                <div class="endpoint">
                    <span class="method">GET</span> /audio/&lt;filename&gt; - Serve audio files
                </div>
                <div class="endpoint">
                    <span class="method">POST</span> /webhook - Receive webhook data
                </div>
                <div class="endpoint">
                    <span class="method">GET</span> /health - Health check
                </div>
                <div class="endpoint">
                    <span class="method">GET</span> /welcome - Welcome form
                </div>
                <div class="endpoint">
                    <span class="method">POST</span> /greet - Process greeting form
                </div>
            </div>
        </body>
        </html>
        '''
        
        logger.info("Root endpoint rendered successfully")
        return render_template_string(html)
    
    except Exception as e:
        logger.error(f"Error rendering root endpoint: {str(e)}")
        logger.exception("Full traceback:")
        return Response("Error loading application info", status=500, mimetype='text/plain')

def generate_telugu_audio(text):
    """
    Generate Telugu audio using ElevenLabs API and save it to a file
    
    Args:
        text (str): Telugu text to convert to speech
        
    Returns:
        bool: True if audio generation was successful, False otherwise
    """
    logger.info(f"Starting audio generation for Telugu text: '{text}' (length: {len(text)} characters)")
    
    # Validate input
    if not text or not text.strip():
        logger.error("Empty or whitespace-only text provided for audio generation")
        return False
    
    # Validate API credentials
    if not ELEVENLABS_API_KEY or ELEVENLABS_API_KEY == "your_elevenlabs_api_key":
        logger.error("ElevenLabs API key not configured properly")
        return False
    
    if not ELEVENLABS_VOICE_ID or ELEVENLABS_VOICE_ID == "your_elevenlabs_voice_id":
        logger.error("ElevenLabs Voice ID not configured properly")
        return False
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    logger.info(f"Making TTS request to: {url}")
    
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
    
    logger.info(f"Request payload: {json.dumps(data, indent=2)}")
    
    try:
        logger.info("Sending request to ElevenLabs API...")
        response = requests.post(url, json=data, headers=headers, timeout=30)
        
        logger.info(f"ElevenLabs API response status: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            logger.info(f"Audio generation successful, content length: {len(response.content)} bytes")
            
            # Ensure directory exists before saving
            try:
                os.makedirs(AUDIO_DIR, exist_ok=True)
                logger.info(f"Audio directory ensured: {AUDIO_DIR}")
            except Exception as dir_error:
                logger.error(f"Failed to create audio directory: {str(dir_error)}")
                return False
            
            # Save the audio file
            try:
                with open(AUDIO_PATH, "wb") as audio_file:
                    audio_file.write(response.content)
                logger.info(f"Audio file saved successfully to: {AUDIO_PATH}")
                
                # Verify file was created and has content
                if os.path.exists(AUDIO_PATH):
                    file_size = os.path.getsize(AUDIO_PATH)
                    logger.info(f"Audio file verified: {file_size} bytes")
                    if file_size == 0:
                        logger.error("Audio file is empty after saving")
                        return False
                else:
                    logger.error("Audio file was not created")
                    return False
                
            except IOError as io_error:
                logger.error(f"IO error while saving audio file: {str(io_error)}")
                return False
            except Exception as save_error:
                logger.error(f"Unexpected error while saving audio file: {str(save_error)}")
                return False
            
            return True
        else:
            logger.error(f"ElevenLabs API error - Status: {response.status_code}")
            logger.error(f"Response text: {response.text}")
            try:
                error_data = response.json()
                logger.error(f"Error details: {json.dumps(error_data, indent=2)}")
            except:
                logger.error("Could not parse error response as JSON")
            return False
            
    except requests.exceptions.Timeout:
        logger.error("Request to ElevenLabs API timed out")
        return False
    except requests.exceptions.ConnectionError:
        logger.error("Connection error while contacting ElevenLabs API")
        return False
    except requests.exceptions.RequestException as req_error:
        logger.error(f"Request error: {str(req_error)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error generating audio: {str(e)}")
        logger.exception("Full traceback:")
        return False

def create_twiml_response(audio_url):
    """
    Create TwiML response with Play tag
    
    Args:
        audio_url (str): Full URL to the audio file
        
    Returns:
        Response: Flask response object with TwiML XML
    """
    logger.info(f"Creating TwiML response with audio URL: {audio_url}")
    
    # Validate audio URL
    if not audio_url or not audio_url.strip():
        logger.error("Empty or invalid audio URL provided for TwiML response")
        return Response("Invalid audio URL", status=400, mimetype='text/plain')
    
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{audio_url}</Play>
</Response>"""
    
    logger.info(f"Generated TwiML: {twiml}")
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
    logger.info(f"Serving audio file: {filename}")
    
    # Validate filename
    if not filename or not filename.strip():
        logger.error("Empty filename requested for audio serving")
        return Response("Invalid filename", status=400, mimetype='text/plain')
    
    # Check if file exists
    file_path = os.path.join('static/audio', filename)
    if not os.path.exists(file_path):
        logger.error(f"Audio file not found: {file_path}")
        return Response("Audio file not found", status=404, mimetype='text/plain')
    
    try:
        file_size = os.path.getsize(file_path)
        logger.info(f"Serving audio file: {filename} (size: {file_size} bytes)")
        
        if file_size == 0:
            logger.error(f"Audio file is empty: {filename}")
            return Response("Audio file is empty", status=500, mimetype='text/plain')
        
        return send_from_directory('static/audio', filename)
    
    except Exception as e:
        logger.error(f"Error serving audio file {filename}: {str(e)}")
        logger.exception("Full traceback:")
        return Response("Error serving audio file", status=500, mimetype='text/plain')

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
        # Log incoming request details
        logger.info("=" * 50)
        logger.info("INCOMING CALL REQUEST")
        logger.info("=" * 50)
        
        # Log all form data
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request URL: {request.url}")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Form data: {dict(request.form)}")
        
        # Log call details
        call_sid = request.form.get('CallSid', 'Unknown')
        call_from = request.form.get('CallFrom', 'Unknown')
        call_to = request.form.get('CallTo', 'Unknown')
        call_status = request.form.get('CallStatus', 'Unknown')
        
        logger.info(f"Call Details:")
        logger.info(f"  - SID: {call_sid}")
        logger.info(f"  - From: {call_from}")
        logger.info(f"  - To: {call_to}")
        logger.info(f"  - Status: {call_status}")
        
        # Get Telugu message from request or use default
        telugu_message = request.form.get('message', "మీరు ఎవరు చెప్పండి, మీ సమస్య ఏమిటి?")
        logger.info(f"Telugu message to convert: '{telugu_message}'")
        
        # Generate audio for the Telugu message
        logger.info("Starting audio generation process...")
        success = generate_telugu_audio(telugu_message)
        
        if success:
            logger.info("Audio generation successful")
            
            # Create the full audio URL (including domain)
            audio_url = request.host_url.rstrip('/') + '/audio/' + AUDIO_FILENAME
            logger.info(f"Generated audio URL: {audio_url}")
            
            # Verify audio file exists before creating TwiML
            if os.path.exists(AUDIO_PATH):
                file_size = os.path.getsize(AUDIO_PATH)
                logger.info(f"Audio file verified before TwiML creation: {file_size} bytes")
                
                # Generate and return TwiML response
                response = create_twiml_response(audio_url)
                logger.info("TwiML response created successfully")
                logger.info("=" * 50)
                return response
            else:
                logger.error("Audio file does not exist after successful generation")
                return Response("Audio file not found", status=500, mimetype='text/plain')
        else:
            # Return error response if audio generation failed
            logger.error("Audio generation failed")
            logger.error("=" * 50)
            return Response("Failed to generate audio", status=500, mimetype='text/plain')
    
    except KeyError as key_error:
        logger.error(f"Missing required parameter: {str(key_error)}")
        logger.exception("Full traceback:")
        return Response("Missing required parameter", status=400, mimetype='text/plain')
    except Exception as e:
        logger.error(f"Unexpected error processing voice response: {str(e)}")
        logger.exception("Full traceback:")
        logger.error("=" * 50)
        return Response("Internal server error", status=500, mimetype='text/plain')

@app.route('/health', methods=['GET'])
def health_check():
    """
    Simple health check endpoint
    """
    logger.info("Health check endpoint accessed")
    
    import datetime
    
    # Check if all required environment variables are set
    health_status = {
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "checks": {
            "elevenlabs_api_key": "configured" if ELEVENLABS_API_KEY and ELEVENLABS_API_KEY != "your_elevenlabs_api_key" else "not_configured",
            "elevenlabs_voice_id": "configured" if ELEVENLABS_VOICE_ID and ELEVENLABS_VOICE_ID != "your_elevenlabs_voice_id" else "not_configured",
            "audio_directory": "exists" if os.path.exists(AUDIO_DIR) else "missing",
            "audio_directory_writable": "writable" if os.access(AUDIO_DIR, os.W_OK) else "not_writable"
        }
    }
    
    # Log health check results
    logger.info(f"Health check results: {json.dumps(health_status, indent=2)}")
    logger.info("Health check completed")
    
    return Response("OK", status=200, mimetype='text/plain')

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Webhook endpoint to receive incoming data from external services
    
    Returns:
        Response: JSON response with status of the webhook processing
    """
    try:
        # Log webhook request details
        logger.info("=" * 50)
        logger.info("WEBHOOK REQUEST RECEIVED")
        logger.info("=" * 50)
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request URL: {request.url}")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Content type: {request.content_type}")
        
        # Get JSON data from the request
        data = request.get_json(silent=True) or {}
        
        if not data:
            # Try to get form data if JSON is not available
            data = request.form.to_dict() or {}
            logger.info("No JSON data found, trying form data")
            
        logger.info(f"Webhook data received: {json.dumps(data, indent=2)}")
        
        # Validate if we have any data
        if not data:
            logger.warning("No data received in webhook request")
            return Response(
                response=json.dumps({"status": "warning", "message": "No data received"}),
                status=200, 
                mimetype='application/json'
            )
        
        # Process the webhook data here
        # This is where you would add your webhook processing logic
        logger.info("Processing webhook data...")
        
        # Return success response
        success_response = {"status": "success", "message": "Webhook received", "data_keys": list(data.keys())}
        logger.info(f"Webhook processing completed: {json.dumps(success_response, indent=2)}")
        logger.info("=" * 50)
        
        return Response(
            response=json.dumps(success_response),
            status=200, 
            mimetype='application/json'
        )
    
    except json.JSONDecodeError as json_error:
        logger.error(f"JSON decode error in webhook: {str(json_error)}")
        return Response(
            response=json.dumps({"status": "error", "message": "Invalid JSON data"}),
            status=400, 
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Unexpected error processing webhook: {str(e)}")
        logger.exception("Full traceback:")
        logger.error("=" * 50)
        return Response(
            response=json.dumps({"status": "error", "message": str(e)}),
            status=500, 
            mimetype='application/json'
        )

@app.route('/welcome', methods=['GET'])
def welcome_form():
    """
    Display a form asking for the user's name
    
    Returns:
        str: HTML page with a form
    """
    logger.info("Welcome form accessed")
    
    try:
        html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Welcome Page</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }
                h1 {
                    color: #333;
                }
                form {
                    background-color: #f5f5f5;
                    padding: 20px;
                    border-radius: 5px;
                    margin-top: 20px;
                }
                input[type="text"] {
                    width: 100%;
                    padding: 10px;
                    margin: 10px 0;
                    border: 1px solid #ddd;
                    border-radius: 3px;
                    box-sizing: border-box;
                }
                input[type="submit"] {
                    background-color: #4CAF50;
                    color: white;
                    padding: 10px 15px;
                    border: none;
                    border-radius: 3px;
                    cursor: pointer;
                }
                input[type="submit"]:hover {
                    background-color: #45a049;
                }
            </style>
        </head>
        <body>
            <h1>Welcome to our Application</h1>
            <form action="/greet" method="post">
                <label for="name">Please enter your name:</label>
                <input type="text" id="name" name="name" required>
                <input type="submit" value="Submit">
            </form>
        </body>
        </html>
        '''
        logger.info("Welcome form HTML rendered successfully")
        return render_template_string(html)
    
    except Exception as e:
        logger.error(f"Error rendering welcome form: {str(e)}")
        logger.exception("Full traceback:")
        return Response("Error loading welcome page", status=500, mimetype='text/plain')

@app.route('/greet', methods=['POST'])
def greet_user():
    """
    Handle form submission and display a welcome message with the user's name
    
    Returns:
        str: HTML page with a welcome message
    """
    try:
        name = request.form.get('name', 'Friend')
        logger.info(f"Greeting user: {name}")
        
        # Validate name
        if not name or not name.strip():
            logger.warning("Empty name provided in greet form")
            name = "Friend"
        
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Welcome {name}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    text-align: center;
                }}
                h1 {{
                    color: #333;
                }}
                .welcome-message {{
                    background-color: #f5f5f5;
                    padding: 20px;
                    border-radius: 5px;
                    margin-top: 20px;
                    font-size: 18px;
                }}
                .button {{
                    display: inline-block;
                    background-color: #4CAF50;
                    color: white;
                    padding: 10px 15px;
                    text-decoration: none;
                    border-radius: 3px;
                    margin-top: 20px;
                }}
                .button:hover {{
                    background-color: #45a049;
                }}
            </style>
        </head>
        <body>
            <h1>Welcome!</h1>
            <div class="welcome-message">
                Hello, <strong>{name}</strong>! We're glad you're here.
            </div>
            <a href="/welcome" class="button">Go Back</a>
        </body>
        </html>
        '''
        logger.info(f"Greeting page rendered successfully for user: {name}")
        return render_template_string(html)
    
    except Exception as e:
        logger.error(f"Error processing greet request: {str(e)}")
        logger.exception("Full traceback:")
        return Response("Error processing greeting", status=500, mimetype='text/plain')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "True").lower() == "true"
    
    # Log application startup information
    logger.info("=" * 60)
    logger.info("FLASK APPLICATION STARTUP")
    logger.info("=" * 60)
    logger.info(f"Starting Flask app on port {port}, debug={debug}")
    logger.info(f"Audio directory: {AUDIO_DIR}")
    logger.info(f"Audio file path: {AUDIO_PATH}")
    logger.info(f"ElevenLabs API Key configured: {'Yes' if ELEVENLABS_API_KEY and ELEVENLABS_API_KEY != 'your_elevenlabs_api_key' else 'No'}")
    logger.info(f"ElevenLabs Voice ID configured: {'Yes' if ELEVENLABS_VOICE_ID and ELEVENLABS_VOICE_ID != 'your_elevenlabs_voice_id' else 'No'}")
    logger.info(f"Exotel API Key configured: {'Yes' if EXOTEL_API_KEY and EXOTEL_API_KEY != 'your_exotel_api_key' else 'No'}")
    logger.info(f"Exotel API Token configured: {'Yes' if EXOTEL_API_TOKEN and EXOTEL_API_TOKEN != 'your_exotel_api_token' else 'No'}")
    logger.info(f"Exotel SID configured: {'Yes' if EXOTEL_SID and EXOTEL_SID != 'your_exotel_sid' else 'No'}")
    logger.info(f"Exotel Subdomain configured: {'Yes' if EXOTEL_SUBDOMAIN and EXOTEL_SUBDOMAIN != 'your_exotel_subdomain' else 'No'}")
    
    # Check if audio directory exists and is writable
    if os.path.exists(AUDIO_DIR):
        if os.access(AUDIO_DIR, os.W_OK):
            logger.info(f"Audio directory is writable: {AUDIO_DIR}")
        else:
            logger.error(f"Audio directory is not writable: {AUDIO_DIR}")
    else:
        logger.warning(f"Audio directory does not exist, will be created: {AUDIO_DIR}")
    
    logger.info("=" * 60)
    
    try:
        app.run(host='0.0.0.0', port=port, debug=debug)
    except Exception as e:
        logger.error(f"Failed to start Flask application: {str(e)}")
        logger.exception("Full traceback:")
        raise