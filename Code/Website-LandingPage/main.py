"""
SignFlow - Real-time Sign Language Prediction
Flask application entry point
"""

import os
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth
from sqlalchemy import inspect, text

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
app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')
app.config['GOOGLE_REDIRECT_URI'] = os.environ.get('GOOGLE_REDIRECT_URI')
app.config['WINDOWS_DOWNLOAD_URL'] = os.environ.get(
    'SIGNFLOW_WINDOWS_DOWNLOAD_URL',
    'https://github.com/mano-dev-01/SignFlow/releases/download/v1.0.0/SignFlowSetup.exe',
)
app.config['MACOS_DOWNLOAD_URL'] = os.environ.get(
    'SIGNFLOW_MACOS_DOWNLOAD_URL',
    'https://github.com/mano-dev-01/SignFlow/releases/tag/v.1.0.1',
)
db = SQLAlchemy(app)
oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    google_sub = db.Column(db.String(255), unique=True, nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100))
    plan = db.Column(db.String(20), nullable=False, default='free')
    subscription_status = db.Column(db.String(20), nullable=False, default='inactive')

    def __repr__(self):
        return f'<User {self.email}>'


def ensure_user_columns():
    """Add new user columns for older databases without migrations."""
    inspector = inspect(db.engine)
    columns = {column['name'] for column in inspector.get_columns('user')}

    if 'google_sub' not in columns:
        db.session.execute(text('ALTER TABLE user ADD COLUMN google_sub VARCHAR(255)'))
    if 'plan' not in columns:
        db.session.execute(text("ALTER TABLE user ADD COLUMN plan VARCHAR(20) DEFAULT 'free'"))
    if 'subscription_status' not in columns:
        db.session.execute(text("ALTER TABLE user ADD COLUMN subscription_status VARCHAR(20) DEFAULT 'inactive'"))
    db.session.commit()

# Initialize Database
with app.app_context():
    db.create_all()
    ensure_user_columns()


def current_user():
    user_id = session.get('user', {}).get('id')
    if not user_id:
        return None
    return User.query.get(user_id)


def display_name(full_name):
    if not full_name:
        return 'User'
    return full_name.split()[0]

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
    form_status = session.pop('subscription_form_status', None)
    form_message = session.pop('subscription_form_message', None)
    return render_template(
        'index.html',
        form_status=form_status,
        form_message=form_message,
    )


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
            form_message='Use Google Sign-In to access your account.'
        )

    return render_template('login.html')


@app.route('/auth/google')
def auth_google():
    """Start Google login."""
    if not app.config.get('GOOGLE_CLIENT_ID') or not app.config.get('GOOGLE_CLIENT_SECRET'):
        return render_template(
            'login.html',
            form_status='error',
            form_message='Google Sign-In is not configured yet. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.'
        )

    redirect_uri = app.config.get('GOOGLE_REDIRECT_URI') or url_for('auth_google_callback', _external=True)
    if app.debug:
        redirect_uri = url_for('auth_google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route('/download/windows')
def download_windows():
    return redirect(app.config['WINDOWS_DOWNLOAD_URL'])


@app.route('/download/linux')
def download_linux():
    return redirect('https://github.com/mano-dev-01/SignFlow/tree/main/Code')


@app.route('/download/macos')
def download_macos():
    return redirect(app.config['MACOS_DOWNLOAD_URL'])


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


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))


@app.route('/subscription/upgrade', methods=['POST'])
def subscription_upgrade():
    user = current_user()
    if not user:
        return redirect(url_for('login'))

    user.plan = 'pro'
    user.subscription_status = 'active'
    db.session.commit()

    session['user']['plan'] = user.plan
    session['user']['subscription_status'] = user.subscription_status
    session['subscription_form_status'] = 'success'
    session['subscription_form_message'] = 'Your account is now on the Pro plan (demo mode).'
    return redirect(f"{url_for('index')}#login")


@app.route('/subscription/cancel', methods=['POST'])
def subscription_cancel():
    user = current_user()
    if not user:
        return redirect(url_for('login'))

    user.plan = 'free'
    user.subscription_status = 'inactive'
    db.session.commit()

    session['user']['plan'] = user.plan
    session['user']['subscription_status'] = user.subscription_status
    session['subscription_form_status'] = 'info'
    session['subscription_form_message'] = 'Pro plan canceled (demo mode). You are back on Free.'
    return redirect(f"{url_for('index')}#login")


@app.route('/auth/google/callback')
def auth_google_callback():
    """Finish Google login and create the session."""
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')

        if not user_info:
            user_info_response = google.get('https://openidconnect.googleapis.com/v1/userinfo')
            if user_info_response.ok:
                user_info = user_info_response.json()

        if not user_info and token.get('id_token'):
            user_info = google.parse_id_token(token)
    except Exception as exc:
        app.logger.exception('Google OAuth callback failed: %s', exc)
        return render_template(
            'login.html',
            form_status='error',
            form_message='Google Sign-In failed. Please try again.'
        ), 400

    if not user_info:
        return render_template(
            'login.html',
            form_status='error',
            form_message='Google did not return a user profile.'
        ), 400

    email = user_info.get('email')
    if not email:
        return render_template(
            'login.html',
            form_status='error',
            form_message='Google account did not provide an email address.'
        ), 400

    google_sub = user_info.get('sub')
    user = None
    if google_sub:
        user = User.query.filter_by(google_sub=google_sub).first()
    if not user:
        user = User.query.filter_by(email=email).first()

    if not user:
        user = User(
            google_sub=google_sub,
            email=email,
            name=user_info.get('name'),
            plan='free',
            subscription_status='inactive',
        )
        db.session.add(user)
    else:
        if google_sub and not user.google_sub:
            user.google_sub = google_sub
        user.name = user_info.get('name') or user.name
        if not user.plan:
            user.plan = 'free'
        if not user.subscription_status:
            user.subscription_status = 'inactive'

    db.session.commit()

    session['user'] = {
        'id': user.id,
        'email': user.email,
        'name': user.name,
        'display_name': display_name(user.name),
        'picture': user_info.get('picture'),
        'plan': user.plan,
        'subscription_status': user.subscription_status,
    }
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

