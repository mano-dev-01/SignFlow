"""
SignFlow - Real-time Sign Language Prediction
Flask application entry point
"""

import os
from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

load_dotenv()

from flask import Flask, render_template, request, url_for, session, redirect

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default_secret_key_if_not_set')
app.config['MAX_CONTENT_LENGTH'] = 128 * 1024
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['LIVE_PREDICTION_SERVER_URL'] = os.environ.get(
    'LIVE_PREDICTION_SERVER_URL',
    'https://mano-dev-01-signflow-inference.hf.space',
)
app.config['WINDOWS_DOWNLOAD_URL'] = os.environ.get(
    'SIGNFLOW_WINDOWS_DOWNLOAD_URL',
    'https://github.com/mano-dev-01/SignFlow/releases/download/v1.0.0/SignFlowSetup.exe',
)
db = SQLAlchemy(app)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100))
    picture = db.Column(db.String(255))
    last_login = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.email}>'

# Initialize Database
with app.app_context():
    db.create_all()

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)


def render_placeholder(title, description, detail, cta_label='Return home', cta_href=None):
    if cta_href is None:
        cta_href = url_for('index')
    return render_template(
        'placeholder.html',
        title=title,
        description=description,
        detail=detail,
        cta_label=cta_label,
        cta_href=cta_href
    )


@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
    response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'

    # Relaxed CSP for /live route (MediaPipe CDN + camera + FastAPI server)
    if request.path == '/live':
        response.headers['Permissions-Policy'] = 'microphone=(), geolocation=()'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "img-src 'self' data: blob:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'wasm-unsafe-eval' https://cdn.jsdelivr.net https://storage.googleapis.com; "
            "connect-src 'self' https://cdn.jsdelivr.net https://storage.googleapis.com http: https:; "
            "worker-src blob:; "
            "font-src 'self' data:; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'"
        )
    else:
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; "
            "font-src 'self' data:; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'"
        )
    return response


@app.route('/')
def index():
    """Landing page"""
    return render_template('index.html')


@app.route('/live')
def live():
    """Live sign language detection — mobile camera + landmark streaming"""
    return render_template(
        'live.html',
        live_server_url=app.config['LIVE_PREDICTION_SERVER_URL'],
    )


@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')


@app.route('/download')
def download():
    """Download page"""
    return render_template('download.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact page"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()

        errors = []
        if not name:
            errors.append('Please provide your name.')
        if not email or '@' not in email:
            errors.append('Please provide a valid email address.')
        if not subject:
            errors.append('Please select a subject.')
        if not message or len(message) < 10:
            errors.append('Please include a message of at least 10 characters.')

        if errors:
            return render_template(
                'contact.html',
                form_status='error',
                form_message='Please fix the issues below and try again.',
                form_errors=errors,
                form_data={
                    'name': name,
                    'email': email,
                    'subject': subject,
                    'message': message
                 }
            ), 400

        return render_template(
            'contact.html',
            form_status='success',
            form_message='Thanks for reaching out! We will reply within 48 hours.'
        )

    return render_template('contact.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        return render_template(
            'login.html',
            form_status='info',
            form_message='Sign-in is currently disabled. Please check back soon.'
        )

    return render_template('login.html')


@app.route('/download/windows')
def download_windows():
    return redirect(app.config['WINDOWS_DOWNLOAD_URL'])


@app.route('/download/linux')
def download_linux():
    return redirect('https://github.com/mano-dev-01/SignFlow/tree/main/Code')


@app.route('/download/macos')
def download_macos():
    return render_placeholder(
        'macOS Release',
        'SignFlow for macOS is on the way.',
        'We will add a waitlist and release notifications here as soon as builds are ready.',
        cta_label='Back to Downloads',
        cta_href=url_for('download')
    )


@app.route('/download/android')
def download_android():
    return render_placeholder(
        'Android Download',
        'Your SignFlow Android download will live here.',
        'We will link this to the Play Store listing and APK mirrors when ready.',
        cta_label='Back to Downloads',
        cta_href=url_for('download')
    )


@app.route('/donate/<int:amount>')
def donate(amount):
    return render_placeholder(
        f'Donate ${amount}',
        'Thanks for supporting SignFlow.',
        'We will connect this to a payment processor and receipts in a follow-up.',
        cta_label='Back to Donate',
        cta_href=f"{url_for('index')}#donate"
    )


@app.route('/auth/github')
def auth_github():
    return render_placeholder(
        'GitHub Sign-In',
        'GitHub OAuth will be wired here.',
        'We will add the OAuth flow and account linking when authentication is enabled.',
        cta_label='Back to Sign In',
        cta_href=url_for('login')
    )


@app.route('/auth/google')
def auth_google():
    """Google Sign-In route"""
    redirect_uri = url_for('auth_google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def auth_google_callback():
    """Google Sign-In callback"""
    token = google.authorize_access_token()
    user_info = token.get('userinfo')
    
    if user_info:
        # Persistence Logic
        user = User.query.filter_by(google_id=user_info['sub']).first()
        
        if not user:
            # Create new user
            user = User(
                google_id=user_info['sub'],
                email=user_info['email'],
                name=user_info.get('name'),
                picture=user_info.get('picture')
            )
            db.session.add(user)
        else:
            # Update existing user
            user.name = user_info.get('name')
            user.picture = user_info.get('picture')
            user.last_login = datetime.utcnow()
        
        db.session.commit()
        
        # Store essential info in session
        session['user'] = {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'picture': user.picture
        }
        
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))


@app.route('/docs')
def docs():
    return render_placeholder(
        'Documentation',
        'SignFlow documentation is coming together.',
        'We will publish setup, usage, and troubleshooting guides here.'
    )


@app.route('/roadmap')
def roadmap():
    return render_placeholder(
        'Product Roadmap',
        'Here is where we will track upcoming SignFlow milestones.',
        'We will publish the public roadmap and progress updates here.'
    )


@app.route('/changelog')
def changelog():
    return render_placeholder(
        'Changelog',
        'Release notes and version history will appear here.',
        'We will keep a detailed log of improvements, fixes, and new features.'
    )


@app.route('/accessibility')
def accessibility():
    return render_placeholder(
        'Accessibility',
        'Our accessibility commitments will live here.',
        'We will document caption standards, inclusive design goals, and testing.'
    )
    

@app.route('/status')
def status():
    return render_placeholder(
        'System Status',
        'Service status updates will live here.',
        'We will show uptime, incidents, and maintenance notices in this space.'
    )


@app.route('/newsletter')
def newsletter():
    return render_placeholder(
        'Newsletter',
        'Subscribe to SignFlow updates.',
        'We will add a simple signup form and archive here.'
    )


@app.route('/privacy')
def privacy():  
    return render_placeholder(
        'Privacy Policy',
        'Our privacy policy will live here.',
        'We will detail data handling, telemetry, and user rights.'
    )


@app.route('/terms')
def terms():
    return render_placeholder(
        'Terms of Service',
        'Our terms of service will live here.',
        'We will outline usage guidelines, licensing, and account terms.'
    )


@app.route('/press')
def press():
    return render_placeholder(
        'Press Kit',
        'SignFlow press assets will live here.',
        'We will add brand guidelines, screenshots, and contact info.'
    )


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(error):
    return render_template('500.html'), 500


if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG') == '1'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)

