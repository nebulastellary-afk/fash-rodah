from flask import Flask, request, jsonify, send_from_directory
import os
import json
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='.')
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Contact information
CONTACT_INFO = {
    'phone': '+254710347138',
    'email': 'rodahkageha21@gmail.com',
    'service_areas': ['Nairobi', 'Mombasa', 'Kisumu', 'Nakuru', 'Eldoret'],
    'availability': {
        'weekdays': '8:00 AM - 6:00 PM',
        'saturday': '9:00 AM - 4:00 PM',
        'sunday': 'By Appointment'
    }
}

# Rate limiting storage
contact_requests = []

def rate_limit(max_per_hour=10):
    """Decorator to limit contact form submissions"""
    def decorator(f):
        def decorated_function(*args, **kwargs):
            now = datetime.now()
            
            # Clean old requests (older than 1 hour)
            global contact_requests
            contact_requests = [req for req in contact_requests 
                              if (now - req['time']).seconds < 3600]
            
            # Check IP-based rate limiting
            client_ip = request.remote_addr
            ip_requests = [req for req in contact_requests 
                          if req['ip'] == client_ip]
            
            if len(ip_requests) >= max_per_hour:
                return jsonify({
                    'success': False,
                    'message': 'Too many requests. Please try again later.'
                }), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/')
def home():
    """Serve the main HTML file"""
    return send_from_directory('.', 'index.html')

@app.route('/submit', methods=['POST'])
@rate_limit(max_per_hour=5)
def submit_contact():
    """Handle contact form submission"""
    try:
        # Get JSON data from frontend
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data received'
            }), 400
        
        # Extract form data
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        service = data.get('service', '')
        message = data.get('message', '').strip()
        contact_method = data.get('contact_method', 'phone')
        
        logger.info(f"Contact form submission: {name}, {email}, {service}")
        
        # Validate required fields
        if not all([name, email, message, service]):
            return jsonify({
                'success': False,
                'message': 'Please fill in all required fields.'
            }), 400
        
        # Validate email format
        if '@' not in email or '.' not in email:
            return jsonify({
                'success': False,
                'message': 'Please enter a valid email address.'
            }), 400
        
        # Add to rate limiting tracking
        contact_requests.append({
            'ip': request.remote_addr,
            'time': datetime.now(),
            'email': email
        })
        
        # Save submission to file
        save_contact_submission({
            'name': name,
            'email': email,
            'phone': phone,
            'service': service,
            'message': message,
            'contact_method': contact_method,
            'ip': request.remote_addr,
            'timestamp': datetime.now().isoformat(),
            'user_agent': request.headers.get('User-Agent', '')
        })
        
        # Here you could add email sending logic if needed
        # send_email_notification(name, email, phone, service, message)
        
        return jsonify({
            'success': True,
            'message': 'Thank you for your message! We will contact you soon.'
        })
        
    except Exception as e:
        logger.error(f"Error processing contact form: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'There was an error sending your message. Please try again or contact us directly.'
        }), 500

def save_contact_submission(data):
    """Save contact form submission to a JSON file for backup"""
    try:
        filename = 'contact_submissions.json'
        
        # Load existing data
        existing_data = []
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    existing_data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                existing_data = []
        
        # Add new data
        existing_data.append(data)
        
        # Save back to file (limit to last 100 submissions)
        if len(existing_data) > 100:
            existing_data = existing_data[-100:]
        
        with open(filename, 'w') as f:
            json.dump(existing_data, f, indent=2, default=str)
            
        logger.info(f"Contact submission saved to {filename}")
        
    except Exception as e:
        logger.error(f"Error saving contact to file: {str(e)}")

@app.route('/contact-info')
def get_contact_info():
    """API endpoint to get contact information"""
    return jsonify(CONTACT_INFO)

@app.route('/health')
def health_check():
    """Health check endpoint for Render"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'Fash Rodah Portfolio',
        'contact_info': CONTACT_INFO
    })

@app.route('/submissions')
def get_submissions():
    """Get all contact submissions (for admin purposes)"""
    try:
        if os.path.exists('contact_submissions.json'):
            with open('contact_submissions.json', 'r') as f:
                data = json.load(f)
            return jsonify({
                'success': True,
                'count': len(data),
                'submissions': data
            })
        else:
            return jsonify({
                'success': True,
                'count': 0,
                'submissions': []
            })
    except Exception as e:
        logger.error(f"Error reading submissions: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error reading submissions'
        }), 500

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return send_from_directory('.', 'index.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(e)}")
    return jsonify({
        'success': False,
        'message': 'Internal server error'
    }), 500

@app.errorhandler(429)
def too_many_requests(e):
    """Handle rate limiting errors"""
    return jsonify({
        'success': False,
        'message': 'Too many requests. Please try again later.'
    }), 429

if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.environ.get('PORT', 5000))
    
    # Run the app
    app.run(
        host='0.0.0.0',
        port=port,
        debug=os.environ.get('FLASK_ENV') == 'development'
    )
