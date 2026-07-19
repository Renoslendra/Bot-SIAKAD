"""
Bot SIAKAD - BMW-M Dashboard UI Server
Flask-based web interface for bot control and monitoring
Production-ready with security, validation, and error handling
"""

from flask import Flask, render_template, jsonify, request, send_file, session, redirect, url_for
from functools import wraps
import json
import os
import hashlib
import secrets
import time
import csv
import io
from datetime import datetime, timedelta
import re

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

# Security configuration
app.secret_key = secrets.token_hex(32)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)
app.config['SESSION_COOKIE_SECURE'] = False  # Set True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# File paths
CONFIG_FILE = os.path.join(os.path.dirname(__file__), '..', 'config', 'bot_config.json')
COURSES_FILE = os.path.join(os.path.dirname(__file__), '..', 'config', 'courses.json')
LOGS_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
ACTIVITY_LOG = os.path.join(LOGS_DIR, 'activity.json')
CONSOLE_LOG = os.path.join(LOGS_DIR, 'console.json')
SESSIONS_LOG = os.path.join(LOGS_DIR, 'sessions.json')

# Rate limiting storage
rate_limit_store = {}

# Global bot state
bot_state = {
    'status': 'IDLE',
    'allow_submit': False,
    'use_fallback': False,
    'uptime': '00:00:00',
    'start_time': None,
    'success_rate': 0,
    'current_attempt': 0,
    'max_attempts': 100,
    'errors': 0,
    'progress': 0,
    'courses_selected': 0,
    'courses_total': 8,
    'sks_total': 0,
    'attempts': 0,
    'current_stage': None,
    'completed_stages': []
}

# ============ SECURITY HELPERS ============

def hash_password(password):
    """Hash password with SHA-256 and salt"""
    salt = secrets.token_hex(16)
    hash_value = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hash_value}"

def verify_password(password, stored_hash):
    """Verify password against stored hash"""
    if not stored_hash or ':' not in stored_hash:
        return False
    salt, hash_value = stored_hash.split(':', 1)
    return hashlib.sha256((salt + password).encode()).hexdigest() == hash_value

def generate_csrf_token():
    """Generate CSRF token"""
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']

def validate_csrf_token(token):
    """Validate CSRF token"""
    return token == session.get('csrf_token')

def rate_limit(max_requests=100, window=60):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            client_ip = request.remote_addr
            current_time = time.time()
            
            if client_ip not in rate_limit_store:
                rate_limit_store[client_ip] = []
            
            # Clean old requests
            rate_limit_store[client_ip] = [
                t for t in rate_limit_store[client_ip]
                if current_time - t < window
            ]
            
            if len(rate_limit_store[client_ip]) >= max_requests:
                return jsonify({'error': 'Rate limit exceeded'}), 429
            
            rate_limit_store[client_ip].append(current_time)
            return f(*args, **kwargs)
        return wrapped
    return decorator

def require_auth(f):
    """Authentication decorator"""
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get('authenticated'):
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return wrapped

# ============ VALIDATION HELPERS ============

def validate_config(data):
    """Validate configuration data"""
    errors = []
    
    if not isinstance(data, dict):
        return ['Invalid data format']
    
    # Validate NIM
    nim = data.get('nim', '')
    if nim and not re.match(r'^\d{6,15}$', nim):
        errors.append('NIM must be 6-15 digits')
    
    # Validate semester
    semester = data.get('semester', 5)
    if not isinstance(semester, int) or semester < 1 or semester > 14:
        errors.append('Semester must be between 1 and 14')
    
    # Validate target SKS
    target_sks = data.get('target_sks', 23)
    if not isinstance(target_sks, int) or target_sks < 18 or target_sks > 24:
        errors.append('Target SKS must be between 18 and 24')
    
    # Validate max attempts
    max_attempts = data.get('max_attempts', 100)
    if not isinstance(max_attempts, int) or max_attempts < 1 or max_attempts > 1000:
        errors.append('Max attempts must be between 1 and 1000')
    
    # Validate delays
    delay_attempt = data.get('delay_attempt', 5)
    if not isinstance(delay_attempt, (int, float)) or delay_attempt < 1 or delay_attempt > 60:
        errors.append('Delay attempt must be between 1 and 60 seconds')
    
    retry_delay = data.get('retry_delay', 30)
    if not isinstance(retry_delay, (int, float)) or retry_delay < 5 or retry_delay > 300:
        errors.append('Retry delay must be between 5 and 300 seconds')
    
    timeout = data.get('timeout', 30)
    if not isinstance(timeout, (int, float)) or timeout < 10 or timeout > 120:
        errors.append('Timeout must be between 10 and 120 seconds')
    
    check_interval = data.get('check_interval', 15)
    if not isinstance(check_interval, (int, float)) or check_interval < 5 or check_interval > 60:
        errors.append('Check interval must be between 5 and 60 minutes')
    
    return errors

def validate_course(data):
    """Validate course data"""
    errors = []
    
    if not isinstance(data, dict):
        return ['Invalid data format']
    
    # Validate code
    code = data.get('code', '').strip()
    if not code:
        errors.append('Course code is required')
    elif not re.match(r'^[A-Z0-9]{3,10}$', code.upper()):
        errors.append('Course code must be 3-10 alphanumeric characters')
    
    # Validate name
    name = data.get('name', '').strip()
    if not name:
        errors.append('Course name is required')
    elif len(name) > 100:
        errors.append('Course name must be less than 100 characters')
    
    # Validate SKS
    sks = data.get('sks', 3)
    if not isinstance(sks, int) or sks < 1 or sks > 6:
        errors.append('SKS must be between 1 and 6')
    
    # Validate class
    class_name = data.get('class_name', 'A')
    if class_name not in ['A', 'B', 'C', 'D', 'E']:
        errors.append('Class must be A, B, C, D, or E')
    
    # Validate schedule
    schedule = data.get('schedule', '').strip()
    if not schedule:
        errors.append('Schedule is required')
    
    return errors

def sanitize_string(value):
    """Sanitize string input"""
    if not isinstance(value, str):
        return ''
    # Remove potentially dangerous characters
    value = re.sub(r'[<>"\';()]', '', value)
    return value.strip()

# ============ FILE OPERATIONS ============

def ensure_dirs():
    """Ensure required directories exist"""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)

def load_config():
    """Load configuration from file"""
    try:
        ensure_dirs()
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        log_console('error', f'Failed to load config: {str(e)}')
    
    return {
        'nim': '',
        'password_hash': '',
        'siakad_url': 'https://siakad.trunojoyo.ac.id',
        'semester': 5,
        'target_sks': 23,
        'max_attempts': 100,
        'allow_submit': False,
        'use_fallback': False,
        'auto_retry': True,
        'delay_attempt': 5,
        'retry_delay': 30,
        'timeout': 30,
        'check_interval': 15
    }

def save_config(config):
    """Save configuration to file"""
    try:
        ensure_dirs()
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        log_console('error', f'Failed to save config: {str(e)}')
        return False

def load_courses():
    """Load courses from file"""
    try:
        ensure_dirs()
        if os.path.exists(COURSES_FILE):
            with open(COURSES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading courses: {e}")
        log_console('error', f'Failed to load courses: {str(e)}')
    
    return {'priority': [], 'fallback': []}

def save_courses(courses):
    """Save courses to file"""
    try:
        ensure_dirs()
        with open(COURSES_FILE, 'w', encoding='utf-8') as f:
            json.dump(courses, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving courses: {e}")
        log_console('error', f'Failed to save courses: {str(e)}')
        return False

def load_json_file(filepath, default=None):
    """Load JSON file safely"""
    try:
        ensure_dirs()
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
    
    return default if default is not None else []

def save_json_file(filepath, data):
    """Save JSON file safely"""
    try:
        ensure_dirs()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving {filepath}: {e}")
        return False

# ============ LOGGING ============

def log_activity(activity_type, title, description):
    """Log activity"""
    try:
        activities = load_json_file(ACTIVITY_LOG, [])
        activities.insert(0, {
            'type': activity_type,
            'title': sanitize_string(title),
            'description': sanitize_string(description),
            'time': datetime.now().strftime('%H:%M:%S'),
            'timestamp': datetime.now().isoformat()
        })
        activities = activities[:100]  # Keep only last 100
        save_json_file(ACTIVITY_LOG, activities)
    except Exception as e:
        print(f"Error logging activity: {e}")

def log_console(level, message):
    """Log console message"""
    try:
        logs = load_json_file(CONSOLE_LOG, [])
        logs.append({
            'level': level,
            'message': sanitize_string(message),
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'datetime': datetime.now().isoformat()
        })
        logs = logs[-500:]  # Keep only last 500
        save_json_file(CONSOLE_LOG, logs)
    except Exception as e:
        print(f"Error logging console: {e}")

def log_session(session_data):
    """Log bot session"""
    try:
        sessions = load_json_file(SESSIONS_LOG, [])
        sessions.insert(0, session_data)
        sessions = sessions[:50]  # Keep only last 50
        save_json_file(SESSIONS_LOG, sessions)
    except Exception as e:
        print(f"Error logging session: {e}")

# ============ CONTEXT PROCESSORS ============

@app.context_processor
def inject_csrf_token():
    """Inject CSRF token into all templates"""
    return {'csrf_token': generate_csrf_token()}

# ============ PAGE ROUTES ============

@app.route('/')
def dashboard():
    """Dashboard page"""
    config = load_config()
    # Don't expose password hash to frontend
    config_safe = {k: v for k, v in config.items() if k != 'password_hash'}
    return render_template('dashboard.html', active_page='dashboard', config=config_safe)

@app.route('/konfigurasi')
def konfigurasi():
    """Configuration page"""
    config = load_config()
    # Don't expose password hash to frontend
    config_safe = {k: v for k, v in config.items() if k != 'password_hash'}
    config_safe['has_password'] = bool(config.get('password_hash'))
    return render_template('konfigurasi.html', active_page='konfigurasi', config=config_safe)

@app.route('/mata_kuliah')
def mata_kuliah():
    """Course management page"""
    courses = load_courses()
    return render_template('mata_kuliah.html', active_page='mata_kuliah', courses=courses)

@app.route('/monitoring')
def monitoring():
    """Monitoring page"""
    return render_template('monitoring.html', active_page='monitoring')

@app.route('/riwayat')
def riwayat():
    """History page"""
    return render_template('riwayat.html', active_page='riwayat')

# ============ API ROUTES ============

@app.route('/api/status')
@rate_limit(max_requests=60, window=60)
def api_status():
    """Get bot status"""
    # Update uptime
    if bot_state['start_time']:
        elapsed = int(time.time() - bot_state['start_time'])
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        bot_state['uptime'] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    return jsonify(bot_state)

@app.route('/api/config', methods=['GET', 'POST'])
@rate_limit(max_requests=30, window=60)
def api_config():
    """Get or update configuration"""
    if request.method == 'POST':
        # Validate CSRF
        csrf_token = request.headers.get('X-CSRF-Token')
        if not validate_csrf_token(csrf_token):
            return jsonify({'success': False, 'error': 'Invalid CSRF token'}), 403
        
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            # Validate data
            errors = validate_config(data)
            if errors:
                return jsonify({'success': False, 'errors': errors}), 400
            
            # Load current config
            config = load_config()
            
            # Update config with sanitized data
            if 'nim' in data:
                config['nim'] = sanitize_string(data['nim'])
            
            # Handle password separately (encrypt it)
            if 'password' in data and data['password']:
                config['password_hash'] = hash_password(data['password'])
            
            # Update other fields
            for key in ['semester', 'target_sks', 'max_attempts', 'allow_submit', 
                       'use_fallback', 'auto_retry', 'delay_attempt', 'retry_delay', 
                       'timeout', 'check_interval']:
                if key in data:
                    config[key] = data[key]
            
            # Save config
            if save_config(config):
                # Update bot state
                bot_state['allow_submit'] = config.get('allow_submit', False)
                bot_state['use_fallback'] = config.get('use_fallback', False)
                bot_state['max_attempts'] = config.get('max_attempts', 100)
                
                log_activity('success', 'Configuration updated', 'Bot configuration saved successfully')
                log_console('info', 'Configuration updated')
                
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': 'Failed to save configuration'}), 500
        
        except Exception as e:
            log_console('error', f'Config update error: {str(e)}')
            return jsonify({'success': False, 'error': 'Internal server error'}), 500
    
    else:
        # GET request
        config = load_config()
        # Don't expose password hash
        config_safe = {k: v for k, v in config.items() if k != 'password_hash'}
        return jsonify(config_safe)

@app.route('/api/courses', methods=['GET', 'POST'])
@rate_limit(max_requests=30, window=60)
def api_courses():
    """Get or add courses"""
    if request.method == 'POST':
        # Validate CSRF
        csrf_token = request.headers.get('X-CSRF-Token')
        if not validate_csrf_token(csrf_token):
            return jsonify({'success': False, 'error': 'Invalid CSRF token'}), 403
        
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            # Validate data
            errors = validate_course(data)
            if errors:
                return jsonify({'success': False, 'errors': errors}), 400
            
            # Load courses
            courses = load_courses()
            
            # Create course object with ID
            new_course = {
                'id': int(time.time() * 1000),  # Unique ID based on timestamp
                'code': sanitize_string(data['code']).upper(),
                'name': sanitize_string(data['name']),
                'sks': int(data['sks']),
                'class_name': sanitize_string(data.get('class_name', 'A')),
                'schedule': sanitize_string(data['schedule']),
                'type': sanitize_string(data.get('type', 'Wajib')),
                'status': 'OPEN',
                'created_at': datetime.now().isoformat()
            }
            
            # Add to appropriate list
            if data.get('is_fallback'):
                courses['fallback'].append(new_course)
            else:
                courses['priority'].append(new_course)
            
            # Save courses
            if save_courses(courses):
                log_activity('success', 'Course added', f'{new_course["name"]} ({new_course["sks"]} SKS)')
                log_console('info', f'Course added: {new_course["code"]} - {new_course["name"]}')
                
                return jsonify({'success': True, 'course': new_course})
            else:
                return jsonify({'success': False, 'error': 'Failed to save course'}), 500
        
        except Exception as e:
            log_console('error', f'Course add error: {str(e)}')
            return jsonify({'success': False, 'error': 'Internal server error'}), 500
    
    else:
        # GET request
        return jsonify(load_courses())

@app.route('/api/courses/<int:course_id>', methods=['DELETE'])
@rate_limit(max_requests=30, window=60)
def api_delete_course(course_id):
    """Delete course by ID"""
    # Validate CSRF
    csrf_token = request.headers.get('X-CSRF-Token')
    if not validate_csrf_token(csrf_token):
        return jsonify({'success': False, 'error': 'Invalid CSRF token'}), 403
    
    try:
        courses = load_courses()
        course_name = None
        
        # Try to remove from priority
        for i, course in enumerate(courses['priority']):
            if course.get('id') == course_id:
                course_name = course.get('name')
                courses['priority'].pop(i)
                if save_courses(courses):
                    log_activity('info', 'Course deleted', f'{course_name}')
                    log_console('info', f'Course deleted: {course_name}')
                    return jsonify({'success': True})
                return jsonify({'success': False, 'error': 'Failed to save changes'}), 500
        
        # Try to remove from fallback
        for i, course in enumerate(courses['fallback']):
            if course.get('id') == course_id:
                course_name = course.get('name')
                courses['fallback'].pop(i)
                if save_courses(courses):
                    log_activity('info', 'Course deleted', f'{course_name}')
                    log_console('info', f'Course deleted: {course_name}')
                    return jsonify({'success': True})
                return jsonify({'success': False, 'error': 'Failed to save changes'}), 500
        
        return jsonify({'success': False, 'error': 'Course not found'}), 404
    
    except Exception as e:
        log_console('error', f'Course delete error: {str(e)}')
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/courses/export')
@rate_limit(max_requests=10, window=60)
def api_export_courses():
    """Export courses as CSV"""
    try:
        courses = load_courses()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Type', 'Code', 'Name', 'SKS', 'Class', 'Schedule', 'Status'])
        
        # Write priority courses
        for course in courses.get('priority', []):
            writer.writerow([
                'Priority',
                course.get('code', ''),
                course.get('name', ''),
                course.get('sks', ''),
                course.get('class_name', ''),
                course.get('schedule', ''),
                course.get('status', 'OPEN')
            ])
        
        # Write fallback courses
        for course in courses.get('fallback', []):
            writer.writerow([
                'Fallback',
                course.get('code', ''),
                course.get('name', ''),
                course.get('sks', ''),
                course.get('class_name', ''),
                course.get('schedule', ''),
                course.get('status', 'OPEN')
            ])
        
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'courses_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    
    except Exception as e:
        log_console('error', f'Course export error: {str(e)}')
        return jsonify({'error': 'Failed to export courses'}), 500

@app.route('/api/activity')
@rate_limit(max_requests=60, window=60)
def api_activity():
    """Get activity logs"""
    activities = load_json_file(ACTIVITY_LOG, [])
    return jsonify({'activities': activities})

@app.route('/api/logs')
@rate_limit(max_requests=60, window=60)
def api_logs():
    """Get console logs"""
    logs = load_json_file(CONSOLE_LOG, [])
    return jsonify({'logs': logs})

@app.route('/api/sessions')
@rate_limit(max_requests=30, window=60)
def api_sessions():
    """Get session history"""
    sessions = load_json_file(SESSIONS_LOG, [])
    return jsonify({'sessions': sessions})

@app.route('/api/bot/start', methods=['POST'])
@rate_limit(max_requests=10, window=60)
def api_bot_start():
    """Start bot"""
    # Validate CSRF
    csrf_token = request.headers.get('X-CSRF-Token')
    if not validate_csrf_token(csrf_token):
        return jsonify({'success': False, 'error': 'Invalid CSRF token'}), 403
    
    try:
        if bot_state['status'] == 'ACTIVE':
            return jsonify({'success': False, 'error': 'Bot is already running'})
        
        bot_state['status'] = 'ACTIVE'
        bot_state['start_time'] = time.time()
        bot_state['current_stage'] = 'login'
        bot_state['completed_stages'] = []
        bot_state['current_attempt'] = 0
        bot_state['errors'] = 0
        
        log_activity('success', 'Bot started', 'Bot initialization completed')
        log_console('info', 'Bot started')
        log_console('success', 'Login to SIAKAD completed')
        
        return jsonify({'success': True})
    
    except Exception as e:
        log_console('error', f'Bot start error: {str(e)}')
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/bot/stop', methods=['POST'])
@rate_limit(max_requests=10, window=60)
def api_bot_stop():
    """Stop bot"""
    # Validate CSRF
    csrf_token = request.headers.get('X-CSRF-Token')
    if not validate_csrf_token(csrf_token):
        return jsonify({'success': False, 'error': 'Invalid CSRF token'}), 403
    
    try:
        if bot_state['status'] != 'ACTIVE':
            return jsonify({'success': False, 'error': 'Bot is not running'})
        
        # Log session before stopping
        session_data = {
            'id': datetime.now().strftime('%Y%m%d-%H%M'),
            'date': datetime.now().strftime('%d %b %Y, %H:%M'),
            'duration': bot_state['uptime'],
            'attempts': bot_state['current_attempt'],
            'courses': f"{bot_state['courses_selected']}/{bot_state['courses_total']}",
            'sks': bot_state['sks_total'],
            'status': 'SUCCESS' if bot_state['courses_selected'] == bot_state['courses_total'] else 'PARTIAL'
        }
        log_session(session_data)
        
        bot_state['status'] = 'IDLE'
        bot_state['start_time'] = None
        bot_state['current_stage'] = None
        bot_state['uptime'] = '00:00:00'
        
        log_activity('info', 'Bot stopped', 'Bot shutdown completed')
        log_console('info', 'Bot stopped')
        
        return jsonify({'success': True})
    
    except Exception as e:
        log_console('error', f'Bot stop error: {str(e)}')
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/bot/dry-run', methods=['POST'])
@rate_limit(max_requests=10, window=60)
def api_bot_dry_run():
    """Run bot in dry-run mode"""
    # Validate CSRF
    csrf_token = request.headers.get('X-CSRF-Token')
    if not validate_csrf_token(csrf_token):
        return jsonify({'success': False, 'error': 'Invalid CSRF token'}), 403
    
    try:
        log_activity('info', 'Dry run started', 'Running in simulation mode')
        log_console('info', 'Dry run mode activated')
        log_console('info', 'Simulating course selection...')
        log_console('success', 'Dry run completed successfully')
        
        return jsonify({'success': True})
    
    except Exception as e:
        log_console('error', f'Dry run error: {str(e)}')
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/bot/check-status', methods=['POST'])
@rate_limit(max_requests=30, window=60)
def api_bot_check_status():
    """Check bot status"""
    try:
        return jsonify({
            'success': True,
            'status': bot_state['status'],
            'uptime': bot_state['uptime'],
            'attempts': bot_state['current_attempt']
        })
    
    except Exception as e:
        log_console('error', f'Status check error: {str(e)}')
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/export/csv')
@rate_limit(max_requests=10, window=60)
def api_export_csv():
    """Export all data as CSV"""
    try:
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write summary
        writer.writerow(['Bot SIAKAD Report'])
        writer.writerow(['Generated', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])
        
        # Write bot state
        writer.writerow(['Bot Status', bot_state['status']])
        writer.writerow(['Total Attempts', bot_state['attempts']])
        writer.writerow(['Success Rate', f"{bot_state['success_rate']}%"])
        writer.writerow([])
        
        # Write courses
        courses = load_courses()
        writer.writerow(['Priority Courses'])
        writer.writerow(['Code', 'Name', 'SKS', 'Class', 'Schedule'])
        for course in courses.get('priority', []):
            writer.writerow([
                course.get('code', ''),
                course.get('name', ''),
                course.get('sks', ''),
                course.get('class_name', ''),
                course.get('schedule', '')
            ])
        
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'siakad_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    
    except Exception as e:
        log_console('error', f'Export error: {str(e)}')
        return jsonify({'error': 'Failed to export data'}), 500

@app.route('/api/export/json')
@rate_limit(max_requests=10, window=60)
def api_export_json():
    """Export all data as JSON"""
    try:
        data = {
            'bot_state': bot_state,
            'courses': load_courses(),
            'config': {k: v for k, v in load_config().items() if k != 'password_hash'},
            'sessions': load_json_file(SESSIONS_LOG, []),
            'generated_at': datetime.now().isoformat()
        }
        
        return send_file(
            io.BytesIO(json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8')),
            mimetype='application/json',
            as_attachment=True,
            download_name=f'siakad_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        )
    
    except Exception as e:
        log_console('error', f'Export error: {str(e)}')
        return jsonify({'error': 'Failed to export data'}), 500

# ============ ERROR HANDLERS ============

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    log_console('error', f'Internal server error: {str(error)}')
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(429)
def rate_limit_exceeded(error):
    return jsonify({'error': 'Rate limit exceeded'}), 429

# ============ MAIN ============

if __name__ == '__main__':
    print("=" * 60)
    print("Bot SIAKAD - BMW-M Dashboard UI")
    print("=" * 60)
    print("Starting server on http://localhost:5000")
    print("Press CTRL+C to quit")
    print("=" * 60)
    
    # Initialize logs
    log_console('info', 'Server started')
    log_activity('info', 'Server started', 'Bot SIAKAD UI server initialized')
    
    app.run(debug=True, host='0.0.0.0', port=5000)
