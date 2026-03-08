from flask import Flask, request, jsonify, session as flask_session, abort
from flask import send_from_directory, redirect, url_for
from flask_cors import CORS
from datetime import datetime, timedelta, date
import requests
import os
import json
import uuid
import hashlib
import hmac
import user_agents
import secrets
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

from config import Config
from models import db, User, MentorProfile, OTPCode, University, Faculty, FacultyStat
from models import Subscription, Session, Payment, Notification, Withdrawal
from models import AuthToken, LoginSession, MentorPoint, MentorCertificate, MentorDocument
from models import News, Material

load_dotenv()

from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config.from_object(Config)

# Session cookie — Render HTTPS uchun
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 86400 * 30  # 30 kun

CORS(app, supports_credentials=True, origins=["http://localhost:5000", "http://127.0.0.1:5000", "*"])
db.init_app(app)

# ── FIX 1: Faqat bir marta, unique endpoint bilan qo'shish ──
class UserAdmin(ModelView):
    column_list = ['id', 'full_name', 'phone', 'telegram_id', 'role', 'is_active', 'created_at']
    column_searchable_list = ['full_name', 'phone', 'telegram_id']
    column_filters = ['role', 'is_active']

class MentorAdmin(ModelView):
    column_list = ['id', 'user_id', 'university', 'faculty', 'is_verified', 'balance', 'created_at']
    column_filters = ['is_verified', 'university']

class UniversityAdmin(ModelView):
    column_list = ['id', 'short_name', 'full_name', 'is_active', 'sort_order']

admin = Admin(app, name="Super Admin Panel", url="/superadmin")
admin.add_view(UserAdmin(User, db.session, name="Foydalanuvchilar", endpoint="super_users"))
admin.add_view(MentorAdmin(MentorProfile, db.session, name="Mentorlar", endpoint="super_mentors"))
admin.add_view(UniversityAdmin(University, db.session, name="Universitetlar", endpoint="super_universities"))
admin.add_view(ModelView(Faculty, db.session, name="Fakultetlar", endpoint="super_faculties"))
admin.add_view(ModelView(Session, db.session, name="Sessiyalar", endpoint="super_sessions"))
admin.add_view(ModelView(Subscription, db.session, name="Obunalar", endpoint="super_subscriptions"))
admin.add_view(ModelView(Payment, db.session, name="To'lovlar", endpoint="super_payments"))

with app.app_context():
    db.create_all()

BOT_TOKEN = Config.BOT_TOKEN
MINI_APP_URL = Config.MINI_APP_URL

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'student_ids'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'avatars'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'materials'), exist_ok=True)

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory('uploads', filename)

@app.route('/')
def index():
    return redirect('/login.html')

@app.route('/health', methods=['GET'])
def health():
    return 'Bot ishlayapti', 200

@app.route('/admin_login.html')
def serve_admin_login_page():
    user_id = flask_session.get('user_id')
    if user_id:
        user = db.session.get(User, user_id)
        if user and user.role in ['admin', 'superadmin']:
            return redirect('/admin.html')
    return send_from_directory('static', 'admin_login.html')

@app.route('/<path:filename>.html')
def serve_html(filename):
    try:
        return send_from_directory('static', filename + '.html')
    except:
        abort(404)

@app.route('/static/<path:filename>')
def serve_static(filename):
    try:
        return send_from_directory('static', filename)
    except:
        abort(404)

@app.route('/<path:filename>')
def serve_static_files(filename):
    if filename.startswith('api/') or filename.startswith('owner/') or filename == 'owner':
        abort(404)

    static_path = os.path.join('static', filename)
    if os.path.isfile(static_path):
        return send_from_directory('static', filename)

    html_path = os.path.join('static', filename + '.html')
    if os.path.isfile(html_path):
        return send_from_directory('static', filename + '.html')

    if filename.startswith('static/'):
        clean_path = filename[7:]
        if os.path.isfile(os.path.join('static', clean_path)):
            return send_from_directory('static', clean_path)

    html_files = [f for f in os.listdir('static') if f.endswith('.html')]
    links = ''.join([f'<li><a href="/{f}" style="color:#00BFA6; text-decoration:none;">📄 {f}</a></li>' for f in html_files])

    return f"""<!DOCTYPE html><html><head><title>ConnectU - Sahifa topilmadi</title><meta charset="UTF-8"><style>body{{background:#040810;color:#EEF2FF;font-family:'Sora',sans-serif;padding:40px 20px;}}.container{{max-width:600px;margin:0 auto;}}h1{{color:#F0A500;font-size:32px;margin-bottom:10px;}}p{{color:#6B7FA0;line-height:1.6;}}ul{{list-style:none;padding:0;}}li{{margin:10px 0;padding:12px;background:#0D1628;border-radius:8px;border-left:3px solid #F0A500;}}a{{color:#00BFA6;text-decoration:none;font-size:16px;}}a:hover{{color:#F0A500;}}.info{{background:#0D1628;padding:20px;border-radius:12px;margin:20px 0;}}</style></head><body><div class="container"><h1>🔍 Sahifa topilmadi</h1><p>So'ralgan fayl: <code style="background:#1A2A4A;padding:4px 8px;border-radius:4px;">{filename}</code></p><div class="info"><h3 style="color:#F0A500;margin-top:0;">📁 Mavjud sahifalar:</h3><ul>{links}</ul></div><p style="text-align:center;margin-top:30px;"><a href="/login.html" style="background:#F0A500;color:#040810;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:600;">🔐 Login sahifasiga o'tish</a></p></div></body></html>""", 404

@app.errorhandler(403)
def forbidden(e):
    return """<html><head><title>403 Forbidden</title></head><body style="background:#040810;color:#EEF2FF;font-family:sans-serif;padding:40px;"><h1 style="color:#F0A500;">403 - Ruxsat yo'q</h1><p>Faylga kirish ruxsati yo'q.</p><p><a href="/login.html" style="color:#00BFA6;">Login sahifasiga o'tish</a></p></body></html>""", 403

@app.errorhandler(404)
def not_found(e):
    return """<html><head><title>404 Not Found</title></head><body style="background:#040810;color:#EEF2FF;font-family:sans-serif;padding:40px;"><h1 style="color:#F0A500;">404 - Sahifa topilmadi</h1><p>So'ralgan fayl mavjud emas.</p><p><a href="/login.html" style="color:#00BFA6;">Login sahifasiga o'tish</a></p></body></html>""", 404

@app.route('/favicon.ico')
def favicon():
    try:
        return send_from_directory('static', 'favicon.ico')
    except:
        return '', 204

@app.route('/apple-touch-icon<path:filename>')
def apple_touch_icon(filename):
    return '', 204

# ── Helpers ──

def send_telegram_message(telegram_id, text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {'chat_id': telegram_id, 'text': text, 'parse_mode': 'HTML'}
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return response.json().get('ok', False)
        return False
    except:
        return False

def get_current_user():
    user_id = flask_session.get('user_id')
    if not user_id:
        return None
    return db.session.get(User, user_id)

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    return request.remote_addr or '0.0.0.0'

def get_device_info():
    user_agent_string = request.headers.get('User-Agent', '')
    ua = user_agents.parse(user_agent_string)
    if ua.is_mobile:
        platform = 'mobile'
    elif ua.is_tablet:
        platform = 'tablet'
    elif ua.is_pc:
        platform = 'desktop'
    elif ua.is_bot:
        platform = 'bot'
    else:
        platform = 'unknown'
    return {
        'user_agent': user_agent_string,
        'browser': ua.browser.family,
        'browser_version': ua.browser.version_string,
        'os': ua.os.family,
        'os_version': ua.os.version_string,
        'device': ua.device.family,
        'platform': platform,
        'is_telegram_webapp': request.headers.get('X-Telegram-WebApp') == 'true',
        'language': request.headers.get('Accept-Language', ''),
        'timestamp': datetime.utcnow().isoformat()
    }

def create_login_session(user, method):
    session_id = str(uuid.uuid4())
    old_sessions = LoginSession.query.filter_by(user_id=user.id, is_active=True).all()
    for old_session in old_sessions:
        if old_session.id != session_id and not old_session.notification_sent:
            device_info = json.loads(old_session.device_info) if old_session.device_info else {}
            send_new_login_notification(user, old_session, device_info)
            old_session.notification_sent = True
        old_session.is_active = False

    device_info = get_device_info()
    ip_address = get_client_ip()
    new_session = LoginSession(
        id=str(uuid.uuid4()),
        user_id=user.id,
        session_id=session_id,
        device_info=json.dumps(device_info, ensure_ascii=False),
        ip_address=ip_address,
        login_method=method,
        is_active=True
    )
    db.session.add(new_session)
    flask_session['user_id'] = user.id
    flask_session['role'] = user.role
    flask_session['session_id'] = session_id
    flask_session.permanent = True
    user.active_session_id = session_id
    db.session.commit()
    return new_session

def send_new_login_notification(user, old_session, device_info):
    if not user.telegram_id:
        return
    device_str = "Noma'lum qurilma"
    if device_info:
        if device_info.get('platform') == 'mobile':
            device_str = f"{device_info.get('device', 'Telefon')} ({device_info.get('os', '')})"
        else:
            device_str = f"{device_info.get('browser', 'Brauzer')} ({device_info.get('os', '')})"
    ip = old_session.ip_address or "Noma'lum IP"
    time_str = old_session.logged_in_at.strftime('%d.%m.%Y %H:%M') if old_session.logged_in_at else "Noma'lum vaqt"
    message = (
        f"⚠️ <b>Xavfsizlik xabarnomasi</b>\n\n"
        f"Hisobingizga <b>yangi qurilmadan</b> kirish aniqlandi:\n\n"
        f"📱 <b>Qurilma:</b> {device_str}\n"
        f"🌐 <b>IP:</b> {ip}\n"
        f"⏰ <b>Vaqt:</b> {time_str}\n\n"
        f"Agar bu siz bo'lsangiz, hech narsa qilishingiz shart emas.\n"
        f"Agar bu siz <b>emas</b> bo'lsangiz, darhol adminga xabar bering: @connectu_admin"
    )
    send_telegram_message(user.telegram_id, message)

# ==========================================
# AUTH ENDPOINTS
# ==========================================

@app.route('/api/telegram-login', methods=['POST'])
def telegram_login():
    data = request.json
    init_data_raw = data.get('initData') or data.get('init_data')
    if init_data_raw:
        try:
            from urllib.parse import unquote, parse_qsl
            import json as _json
            params = dict(parse_qsl(unquote(init_data_raw), keep_blank_values=True))
            user_json = params.get('user')
            if not user_json:
                return jsonify({'success': False, 'error': 'initData ichida user topilmadi'}), 400
            tg_user = _json.loads(user_json)
            telegram_id = str(tg_user.get('id', ''))
            full_name = ' '.join(filter(None, [tg_user.get('first_name',''), tg_user.get('last_name','')])).strip()
            username = tg_user.get('username', '')
        except Exception as e:
            return jsonify({'success': False, 'error': f'initData parse xatosi: {str(e)}'}), 400
    elif data.get('telegram_id'):
        telegram_id = str(data.get('telegram_id'))
        full_name = data.get('full_name', 'Foydalanuvchi')
        username = data.get('username', '')
    else:
        return jsonify({'success': False, 'error': 'initData yoki telegram_id kerak'}), 400

    if not telegram_id:
        return jsonify({'success': False, 'error': 'Telegram ID topilmadi'}), 400

    user = User.query.filter_by(telegram_id=telegram_id).first()
    session_replaced = False

    if user:
        session_replaced = LoginSession.query.filter_by(user_id=user.id, is_active=True).count() > 0
        new_session = create_login_session(user, 'telegram_webapp')
    else:
        user = User(
            telegram_id=telegram_id,
            full_name=full_name or 'Foydalanuvchi',
            username=username,
            role='student',
            is_active=True,
        )
        db.session.add(user)
        db.session.flush()
        new_session = create_login_session(user, 'telegram_webapp')

    return jsonify({
        'success': True,
        'user': user.to_full_dict(),
        'session_replaced': session_replaced,
        'session_id': new_session.session_id
    })

@app.route('/api/auth/token', methods=['POST'])
def create_auth_token():
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    data = request.json or {}
    auth_token = AuthToken(
        token=token,
        expires_at=expires_at,
        created_at=datetime.utcnow(),
        source=data.get('source', 'deeplink')
    )
    db.session.add(auth_token)
    db.session.commit()
    bot_username = os.getenv('BOT_USERNAME', 'BaxaSaveBot')
    return jsonify({'success': True, 'token': token, 'bot_username': bot_username, 'expires_in': 300})

@app.route('/api/auth/qr-confirm', methods=['POST'])
def qr_confirm():
    try:
        data = request.json or {}
        token = data.get('token')
        init_data_raw = data.get('initData') or data.get('init_data')
        if not token or not init_data_raw:
            return jsonify({'success': False, 'error': 'token va initData kerak'}), 400
        from urllib.parse import unquote, parse_qsl
        import json as _json
        params = dict(parse_qsl(unquote(init_data_raw), keep_blank_values=True))
        user_json = params.get('user')
        if not user_json:
            return jsonify({'success': False, 'error': 'initData ichida user topilmadi'}), 400
        tg_user = _json.loads(user_json)
        telegram_id = str(tg_user.get('id', ''))
        if not telegram_id:
            return jsonify({'success': False, 'error': 'Telegram ID topilmadi'}), 400
        auth_token = AuthToken.query.filter_by(token=token, is_used=False)\
            .filter(AuthToken.expires_at > datetime.utcnow()).first()
        if not auth_token:
            return jsonify({'success': False, 'error': "Token noto'g'ri yoki muddati o'tgan"}), 400
        user = User.query.filter_by(telegram_id=telegram_id).first()
        if not user:
            first = tg_user.get('first_name', '')
            last = tg_user.get('last_name', '')
            full_name = (first + ' ' + last).strip() or f'User_{telegram_id}'
            user = User(telegram_id=telegram_id, full_name=full_name,
                        username=tg_user.get('username', ''), role='student', is_active=True)
            db.session.add(user)
            db.session.flush()
        auth_token.user_id = user.id
        auth_token.source = 'qr'
        db.session.commit()
        return jsonify({'success': True, 'message': 'Tasdiqlandi!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auth/check', methods=['GET'])
def check_auth_token():
    token = request.args.get('token')
    if not token:
        return jsonify({'success': False, 'error': 'Token kerak'}), 400
    auth_token = AuthToken.query.filter_by(token=token).first()
    if not auth_token:
        return jsonify({'success': False, 'expired': True, 'error': 'Token topilmadi'})
    if auth_token.expires_at < datetime.utcnow():
        return jsonify({'success': False, 'expired': True, 'error': "Token muddati o'tgan"})
    if auth_token.is_used:
        return jsonify({'success': False, 'expired': True, 'error': 'Token allaqachon ishlatilgan'})
    if auth_token.user_id:
        user = db.session.get(User, auth_token.user_id)
        if user:
            method = 'qr' if auth_token.source == 'qr' else 'deeplink'
            session_replaced = LoginSession.query.filter_by(user_id=user.id, is_active=True).count() > 0
            create_login_session(user, method)
            auth_token.is_used = True
            db.session.commit()
            return jsonify({'success': True, 'user': user.to_full_dict(), 'session_replaced': session_replaced})
    return jsonify({'success': False})

@app.route('/api/send-otp', methods=['POST'])
def send_otp():
    try:
        data = request.json
        phone = data.get('phone')
        if not phone:
            return jsonify({'success': False, 'error': 'Telefon raqam kerak'}), 400
        user = User.query.filter_by(phone=phone).first()
        if not user:
            return jsonify({'success': False, 'error': 'Foydalanuvchi topilmadi', 'need_register': True}), 400
        if not user.telegram_id:
            return jsonify({'success': False, 'error': "Telegram profilingiz topilmadi. Avval botga /start bosing.", 'need_register': True}), 400
        OTPCode.query.filter_by(identifier=phone, is_used=False).delete()
        code = OTPCode.generate_code()
        otp = OTPCode(identifier=phone, code=code, source='web', is_sent=False,
                      expires_at=datetime.utcnow() + timedelta(minutes=5))
        db.session.add(otp)
        db.session.commit()
        message = f"🔐 <b>ConnectU — Tasdiqlash kodi:</b>\n\n<code>{code}</code>\n\n⏱ Kod 5 daqiqa amal qiladi.\nBu kodni hech kimga bermang!"
        success = send_telegram_message(user.telegram_id, message)
        if success:
            otp.is_sent = True
            db.session.commit()
            return jsonify({'success': True, 'message': 'Kod Telegram orqali yuborildi'})
        return jsonify({'success': False, 'error': 'Telegram xabar yuborishda xatolik'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    phone = data.get('phone')
    code = data.get('code')
    if not phone or not code:
        return jsonify({'success': False, 'error': 'Telefon va kod kerak'}), 400
    otp = OTPCode.query.filter_by(identifier=phone, code=code, is_used=False)\
        .filter(OTPCode.expires_at > datetime.utcnow()).first()
    if not otp:
        return jsonify({'success': False, 'error': "Noto'g'ri kod yoki muddati o'tgan"}), 400
    otp.is_used = True
    db.session.commit()
    user = User.query.filter_by(phone=phone).first()
    if not user:
        user = User(phone=phone, role='student', full_name='Foydalanuvchi')
        db.session.add(user)
        db.session.commit()
    flask_session['user_id'] = user.id
    flask_session['role'] = user.role
    flask_session.permanent = True
    return jsonify({'success': True, 'user': user.to_dict()})

@app.route('/api/sync-session', methods=['POST'])
def sync_session():
    try:
        existing_user_id = flask_session.get('user_id')
        if existing_user_id:
            user = db.session.get(User, existing_user_id)
            if user and user.is_active:
                return jsonify({'success': True, 'user': user.to_full_dict()})
        data = request.json
        if not data.get('from_login', False):
            return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
        user_id = data.get('user_id')
        phone = data.get('phone')
        if not user_id and not phone:
            return jsonify({'success': False, 'error': "Ma'lumot yetarli emas"}), 400
        user = None
        if user_id:
            user = db.session.get(User, user_id)
        if not user and phone:
            user = User.query.filter_by(phone=phone).first()
        if not user:
            return jsonify({'success': False, 'error': 'Foydalanuvchi topilmadi'}), 404
        if not user.is_active:
            return jsonify({'success': False, 'error': 'Hisob bloklangan'}), 403
        flask_session['user_id'] = user.id
        flask_session['role'] = user.role
        flask_session.permanent = True
        return jsonify({'success': True, 'user': user.to_full_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/login-telegram', methods=['POST'])
def login_telegram():
    data = request.json
    init_data_raw = data.get('initData') or data.get('init_data')
    if init_data_raw:
        try:
            from urllib.parse import unquote, parse_qsl
            import json as _json
            params = dict(parse_qsl(unquote(init_data_raw), keep_blank_values=True))
            user_json = params.get('user')
            if not user_json:
                return jsonify({'success': False, 'error': 'initData ichida user topilmadi'}), 400
            tg_user = _json.loads(user_json)
            telegram_id = str(tg_user.get('id', ''))
            first_name = tg_user.get('first_name', '')
            last_name = tg_user.get('last_name', '')
            username = tg_user.get('username', '')
        except Exception as e:
            return jsonify({'success': False, 'error': f'initData parse xatosi: {str(e)}'}), 400
    else:
        telegram_id = str(data.get('telegram_id', ''))
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        username = data.get('username', '')
    if not telegram_id:
        return jsonify({'success': False, 'error': 'Telegram ID kerak'}), 400
    user = User.query.filter_by(telegram_id=telegram_id).first()
    full_name = f"{first_name} {last_name}".strip()
    if not user:
        user = User(telegram_id=telegram_id, username=username,
                    full_name=full_name or 'Foydalanuvchi', role='student')
        db.session.add(user)
        db.session.commit()
    else:
        user.username = username
        if full_name and user.full_name == 'Foydalanuvchi':
            user.full_name = full_name
        db.session.commit()
    flask_session['user_id'] = user.id
    flask_session['role'] = user.role
    flask_session.permanent = True
    return jsonify({'success': True, 'user': user.to_dict()})

@app.route('/api/confirm-role', methods=['POST'])
def confirm_role():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Kirilmagan'}), 401
    data = request.json
    role = data.get('role')
    phone = data.get('phone')
    if role not in ['student', 'mentor']:
        return jsonify({'success': False, 'error': "Noto'g'ri rol"}), 400
    user.role = role
    if phone and not user.phone:
        user.phone = phone
    if role == 'mentor' and not user.mentor_profile:
        db.session.add(MentorProfile(user_id=user.id))
    db.session.commit()
    flask_session['role'] = user.role
    role_redirects = {'mentor': '/mentor-dashboard.html', 'student': '/abuturyent.html'}
    return jsonify({'success': True, 'user': user.to_dict(),
                    'redirect_url': role_redirects.get(user.role, '/login.html')})

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    if not username or not password:
        return jsonify({'success': False, 'error': 'Login va parol kerak'}), 400
    user = User.query.filter((User.username == username) | (User.phone == username)).first()
    if not user or user.role not in ['admin', 'superadmin']:
        return jsonify({'success': False, 'error': "Login yoki parol noto'g'ri"}), 401
    if not user.is_active:
        return jsonify({'success': False, 'error': 'Hisob bloklangan'}), 403
    expected_hash = getattr(user, 'password_hash', None)
    if expected_hash:
        input_hash = hashlib.sha256(password.encode()).hexdigest()
        if input_hash != expected_hash and password != os.getenv('ADMIN_DEFAULT_PASSWORD', ''):
            return jsonify({'success': False, 'error': "Login yoki parol noto'g'ri"}), 401
    else:
        if password != os.getenv('ADMIN_PASSWORD', 'admin123'):
            return jsonify({'success': False, 'error': "Login yoki parol noto'g'ri"}), 401
    flask_session['user_id'] = user.id
    flask_session['role'] = user.role
    flask_session['is_admin'] = True
    flask_session.permanent = True
    return jsonify({'success': True, 'user': {'id': user.id, 'full_name': user.full_name,
                                               'username': user.username, 'role': user.role}})

@app.route('/api/admin/change-password', methods=['POST'])
def admin_change_password():
    user = get_current_user()
    if not user or user.role not in ['admin', 'superadmin']:
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    data = request.json
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    if not new_password or len(new_password) < 6:
        return jsonify({'success': False, 'error': "Yangi parol kamida 6 belgi bo'lishi kerak"}), 400
    current_hash = getattr(user, 'password_hash', None)
    if current_hash:
        if hashlib.sha256(old_password.encode()).hexdigest() != current_hash:
            return jsonify({'success': False, 'error': "Eski parol noto'g'ri"}), 400
    elif old_password != os.getenv('ADMIN_PASSWORD', 'admin123'):
        return jsonify({'success': False, 'error': "Eski parol noto'g'ri"}), 400
    if hasattr(user, 'password_hash'):
        user.password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        db.session.commit()
    return jsonify({'success': True})

@app.route('/api/me', methods=['GET'])
def get_me():
    user_id = flask_session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Kirilmagan'}), 401
    user = db.session.get(User, user_id)
    if not user:
        flask_session.clear()
        return jsonify({'success': False, 'error': 'Foydalanuvchi topilmadi'}), 401

    user_dict = user.to_full_dict()

    # Mentor profil to'liq ma'lumot
    if user.role == 'mentor' and user.mentor_profile:
        mp = user.mentor_profile
        user_dict['mentor_profile'] = {
            'id': mp.id,
            'university': mp.university,
            'faculty': mp.faculty,
            'year': mp.year,
            'bio': mp.bio,
            'gpa': float(mp.gpa) if mp.gpa else None,
            'is_verified': mp.is_verified,
            'rating': float(mp.rating) if mp.rating else 5.0,
            'total_sessions': mp.total_sessions or 0,
            'total_reviews': mp.total_reviews or 0,
            'balance': mp.balance or 0,
            'card_last4': mp.card_last4,
            'card_holder': mp.card_holder,
            'student_id_url': mp.student_id_url,
        }

    role_redirects = {
        'mentor':     '/mentor-dashboard.html',
        'student':    '/abuturyent.html',
        'admin':      '/admin.html',
        'superadmin': '/admin.html',
    }
    return jsonify({
        'success': True,
        'user': user_dict,
        'redirect_url': role_redirects.get(user.role, '/login.html')
    })

@app.route('/api/debug-session', methods=['GET'])
def debug_session():
    return jsonify({'success': True, 'session': {
        'user_id': flask_session.get('user_id'),
        'role': flask_session.get('role'),
        'session_keys': list(flask_session.keys())
    }})

@app.route('/api/logout', methods=['POST'])
def logout():
    flask_session.clear()
    response = jsonify({'success': True})
    response.delete_cookie(app.config.get('SESSION_COOKIE_NAME', 'session'), path='/')
    response.delete_cookie('cu_session', path='/')
    response.delete_cookie('remember_token', path='/')
    return response

# ==========================================
# BOT ENDPOINTS
# ==========================================

@app.route('/api/bot/verify-login', methods=['POST'])
def bot_verify_login():
    try:
        data = request.json
        token = data.get('token')
        telegram_id = data.get('telegram_id')
        if not token or not telegram_id:
            return jsonify({'success': False, 'error': "Ma'lumot yetarli emas"}), 400
        auth_token = AuthToken.query.filter_by(token=token, is_used=False)\
            .filter(AuthToken.expires_at > datetime.utcnow()).first()
        if not auth_token:
            return jsonify({'success': False, 'error': "Token noto'g'ri yoki muddati o'tgan"})
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        username = data.get('username', '')
        full_name = f"{first_name} {last_name}".strip() or f"User_{telegram_id}"
        user = User.query.filter_by(telegram_id=telegram_id).first()
        if not user:
            user = User(telegram_id=telegram_id, full_name=full_name,
                        username=username, role='student')
            db.session.add(user)
            db.session.flush()
        else:
            user.full_name = full_name
            user.username = username
        auth_token.user_id = user.id
        auth_token.is_used = True
        auth_token.used_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True, 'user': user.to_full_dict(), 'session_replaced': False})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bot/register', methods=['POST'])
def bot_register():
    try:
        data = request.json
        telegram_id = data.get('telegram_id')
        phone = data.get('phone')
        full_name = data.get('full_name')
        role = data.get('role', 'student')
        if not telegram_id or not phone or not full_name:
            return jsonify({'success': False, 'error': "Ma'lumot yetarli emas"}), 400
        user = User.query.filter_by(telegram_id=telegram_id).first()
        if user:
            user.phone = phone
            user.full_name = full_name
            user.username = data.get('username', '')
            if role == 'mentor' and not user.mentor_profile:
                db.session.add(MentorProfile(user_id=user.id,
                    university=data.get('university'), faculty=data.get('faculty'),
                    year=data.get('year'), is_verified=False, created_at=datetime.utcnow()))
        else:
            user = User(telegram_id=telegram_id, phone=phone, full_name=full_name,
                        username=data.get('username', ''), role=role)
            db.session.add(user)
            db.session.flush()
            if role == 'mentor':
                db.session.add(MentorProfile(user_id=user.id,
                    university=data.get('university'), faculty=data.get('faculty'),
                    year=data.get('year'), is_verified=False))
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bot/user/<int:telegram_id>', methods=['GET'])
def bot_get_user(telegram_id):
    user = User.query.filter_by(telegram_id=telegram_id).first()
    if not user:
        return jsonify({'success': False})
    return jsonify({'success': True, 'user': user.to_full_dict()})

@app.route('/api/bot/update-user', methods=['POST'])
def bot_update_user():
    data = request.json
    user = User.query.filter_by(telegram_id=data.get('telegram_id')).first()
    if not user:
        return jsonify({'success': False}), 404
    if 'full_name' in data:
        user.full_name = data['full_name']
    if 'bio' in data and user.mentor_profile:
        user.mentor_profile.bio = data['bio']
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/bot/unsent-otps', methods=['GET'])
def bot_get_unsent_otps():
    if request.headers.get('X-API-Key') != os.getenv('BOT_API_KEY', 'secret-key-123'):
        return jsonify({'success': False}), 403
    otps = OTPCode.query.filter_by(is_sent=False, is_used=False)\
        .filter(OTPCode.expires_at > datetime.utcnow()).limit(10).all()
    result = []
    for otp in otps:
        user = User.query.filter_by(phone=otp.identifier).first()
        if user and user.telegram_id:
            result.append({'id': otp.id, 'code': otp.code, 'telegram_id': user.telegram_id})
    return jsonify({'success': True, 'otps': result})

@app.route('/api/bot/mark-sent', methods=['POST'])
def bot_mark_otp_sent():
    if request.headers.get('X-API-Key') != os.getenv('BOT_API_KEY', 'secret-key-123'):
        return jsonify({'success': False}), 403
    otp = db.session.get(OTPCode, request.json.get('otp_id'))
    if otp:
        otp.is_sent = True
        db.session.commit()
    return jsonify({'success': True})

# ==========================================
# UNIVERSITIES & FACULTIES
# ==========================================

@app.route('/api/universities', methods=['GET', 'POST'])
def handle_universities():
    if request.method == 'GET':
        unis = University.query.filter_by(is_active=True).order_by(University.sort_order).all()
        result = []
        for u in unis:
            u_dict = u.to_dict()
            # Fakultetlarni ham birga qaytaramiz — foydalanuvchi paneli uchun
            faculties = Faculty.query.filter_by(university_id=u.id, is_active=True)\
                .order_by(Faculty.sort_order).all()
            fac_list = []
            for f in faculties:
                f_dict = f.to_dict()
                stats = FacultyStat.query.filter_by(faculty_id=f.id).order_by(FacultyStat.year).all()
                f_dict['stats'] = [{'year': s.year, 'min_score': s.min_score,
                                    'max_score': s.max_score, 'applicants': s.applicants,
                                    'quota': s.quota} for s in stats]
                fac_list.append(f_dict)
            u_dict['faculties'] = fac_list
            result.append(u_dict)
        return jsonify({'success': True, 'universities': result})

    user = get_current_user()
    if not user or user.role not in ['admin', 'superadmin']:
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    data = request.json
    try:
        uni = University(
            short_name=data.get('short_name'), full_name=data.get('full_name'),
            description=data.get('description'), website=data.get('website'),
            telegram=data.get('telegram'), instagram=data.get('instagram'),
            cover_url=data.get('cover_url'), is_active=True, sort_order=data.get('sort_order', 0)
        )
        db.session.add(uni)
        db.session.commit()
        return jsonify({'success': True, 'university': uni.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/universities/<string:uni_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_university(uni_id):
    uni = db.session.get(University, uni_id)
    if not uni:
        abort(404)
    user = get_current_user()
    if request.method == 'GET':
        faculties = Faculty.query.filter_by(university_id=uni_id)\
            .order_by(Faculty.sort_order).all()
        faculties_data = []
        for f in faculties:
            f_dict = f.to_dict()
            stats = FacultyStat.query.filter_by(faculty_id=f.id).order_by(FacultyStat.year).all()
            f_dict['stats'] = [{'year': s.year, 'min_score': s.min_score,
                                 'max_score': s.max_score, 'applicants': s.applicants,
                                 'quota': s.quota} for s in stats]
            faculties_data.append(f_dict)
        uni_dict = uni.to_dict()
        uni_dict['faculties'] = faculties_data
        return jsonify({'success': True, 'university': uni_dict})
    elif request.method == 'PUT':
        if not user or user.role not in ['admin', 'superadmin']:
            return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
        data = request.json
        for field in ['short_name', 'full_name', 'description', 'website', 'telegram', 'instagram', 'cover_url', 'sort_order']:
            if field in data:
                setattr(uni, field, data[field])
        db.session.commit()
        return jsonify({'success': True, 'university': uni.to_dict()})
    else:  # DELETE
        if not user or user.role not in ['admin', 'superadmin']:
            return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
        db.session.delete(uni)
        db.session.commit()
        return jsonify({'success': True})

@app.route('/api/universities/<string:uni_id>/faculties', methods=['GET', 'POST'])
def handle_faculties(uni_id):
    uni = db.session.get(University, uni_id)
    if not uni:
        abort(404)
    user = get_current_user()
    if request.method == 'GET':
        faculties = Faculty.query.filter_by(university_id=uni_id, is_active=True)\
            .order_by(Faculty.sort_order).all()
        return jsonify({'success': True, 'faculties': [f.to_dict() for f in faculties]})
    if not user or user.role not in ['admin', 'superadmin']:
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    data = request.json
    faculty = Faculty(
        university_id=uni_id, name=data.get('name'), description=data.get('description'),
        cover_url=data.get('cover_url'), quota=data.get('quota'),
        employment_pct=data.get('employment_pct'), avg_salary_mln=data.get('avg_salary_mln'),
        sort_order=data.get('sort_order', 0), is_active=True
    )
    db.session.add(faculty)
    db.session.commit()
    return jsonify({'success': True, 'faculty': faculty.to_dict()})

@app.route('/api/faculties/<string:faculty_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_faculty(faculty_id):
    faculty = db.session.get(Faculty, faculty_id)
    if not faculty:
        abort(404)
    user = get_current_user()
    if request.method == 'GET':
        stats = FacultyStat.query.filter_by(faculty_id=faculty_id).order_by(FacultyStat.year).all()
        return jsonify({'success': True, 'faculty': faculty.to_dict(),
                        'stats': [{'id': s.id, 'year': s.year, 'min_score': s.min_score,
                                   'max_score': s.max_score, 'applicants': s.applicants,
                                   'quota': s.quota} for s in stats]})
    elif request.method == 'PUT':
        if not user or user.role not in ['admin', 'superadmin']:
            return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
        data = request.json
        for field in ['name', 'description', 'cover_url', 'quota', 'employment_pct', 'avg_salary_mln', 'sort_order']:
            if field in data:
                setattr(faculty, field, data[field])
        db.session.commit()
        return jsonify({'success': True, 'faculty': faculty.to_dict()})
    else:  # DELETE
        if not user or user.role not in ['admin', 'superadmin']:
            return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
        db.session.delete(faculty)
        db.session.commit()
        return jsonify({'success': True})

@app.route('/api/faculties/<string:faculty_id>/stats', methods=['POST', 'PUT'])
def handle_faculty_stats(faculty_id):
    faculty = db.session.get(Faculty, faculty_id)
    if not faculty:
        abort(404)
    user = get_current_user()
    if not user or user.role not in ['admin', 'superadmin']:
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    data = request.json
    year = data.get('year')
    if not year:
        return jsonify({'success': False, 'error': 'Yil kerak'}), 400
    stat = FacultyStat.query.filter_by(faculty_id=faculty_id, year=year).first()
    if request.method == 'POST':
        if stat:
            return jsonify({'success': False, 'error': 'Bu yil uchun statistika mavjud'}), 400
        stat = FacultyStat(faculty_id=faculty_id, year=year, min_score=data.get('min_score'),
                           max_score=data.get('max_score'), applicants=data.get('applicants'),
                           quota=data.get('quota'))
        db.session.add(stat)
    else:
        if not stat:
            return jsonify({'success': False, 'error': 'Statistika topilmadi'}), 404
        for field in ['min_score', 'max_score', 'applicants', 'quota']:
            if field in data:
                setattr(stat, field, data[field])
    db.session.commit()
    return jsonify({'success': True, 'stat': {'year': stat.year, 'min_score': stat.min_score,
                                              'max_score': stat.max_score, 'applicants': stat.applicants,
                                              'quota': stat.quota}})

# ==========================================
# MENTORS (public)
# ==========================================

@app.route('/api/mentors', methods=['GET'])
def get_mentors():
    university = request.args.get('university')
    query = MentorProfile.query.filter_by(is_verified=True)
    if university:
        query = query.filter_by(university=university)
    mentors = query.limit(50).all()
    result = []
    for m in mentors:
        user = db.session.get(User, m.user_id)
        if user:
            m_dict = m.to_dict()
            m_dict['mentor_profile_id'] = m.id   # frontend uchun
            m_dict['full_name'] = user.full_name
            m_dict['username'] = user.username
            m_dict['avatar_url'] = user.avatar_url
            m_dict['rating'] = float(m.rating) if m.rating else 5.0
            m_dict['total_sessions'] = m.total_sessions or 0
            m_dict['total_reviews'] = m.total_reviews or 0
            result.append(m_dict)
    return jsonify({'success': True, 'mentors': result})

@app.route('/api/mentors/<string:mentor_id>', methods=['GET'])
def get_mentor_detail(mentor_id):
    mentor = db.session.get(MentorProfile, mentor_id)
    if not mentor:
        abort(404)
    user = db.session.get(User, mentor.user_id)
    if not user:
        return jsonify({'success': False, 'error': 'Foydalanuvchi topilmadi'}), 404
    mentor_dict = mentor.to_dict()
    mentor_dict['mentor_profile_id'] = mentor.id
    mentor_dict['full_name'] = user.full_name
    mentor_dict['username'] = user.username
    mentor_dict['avatar_url'] = user.avatar_url
    mentor_dict['bio'] = mentor.bio or ''
    mentor_dict['university'] = mentor.university or ''
    mentor_dict['faculty'] = mentor.faculty or ''
    mentor_dict['year'] = mentor.year
    mentor_dict['gpa'] = float(mentor.gpa) if mentor.gpa else None
    mentor_dict['rating'] = float(mentor.rating) if mentor.rating else 5.0
    mentor_dict['total_sessions'] = mentor.total_sessions or 0
    mentor_dict['total_reviews'] = mentor.total_reviews or 0
    mentor_dict['is_verified'] = mentor.is_verified

    # Oxirgi 5 ta tugallangan sessiya (faqat student ko'ra oladigan ma'lumotlar)
    sessions = Session.query.filter_by(mentor_id=mentor.id, status='completed')\
        .order_by(Session.created_at.desc()).limit(5).all()
    mentor_dict['recent_sessions'] = []
    for s in sessions:
        student = db.session.get(User, s.student_id)
        mentor_dict['recent_sessions'].append({
            'id': s.id,
            'student_name': student.full_name if student else "Noma'lum",
            'scheduled_at': s.scheduled_at.isoformat() if s.scheduled_at else None,
            'student_rating': s.student_rating,
            'student_review': s.student_review
        })

    # Sertifikatlar (abuturyent ko'rishi uchun)
    certs = MentorCertificate.query.filter_by(mentor_id=mentor.id).all()
    mentor_dict['certificates'] = [{
        'title': c.title, 'issuer': c.issuer,
        'date': c.issued_date.isoformat() if c.issued_date else None
    } for c in certs]

    return jsonify({'success': True, 'mentor': mentor_dict})

# ==========================================
# PROFILE
# ==========================================

@app.route('/api/profile', methods=['PUT'])
def update_profile():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Kirilmagan'}), 401
    data = request.json or {}

    # User maydonlari
    if 'full_name' in data and data['full_name'].strip():
        user.full_name = data['full_name'].strip()
    if 'username' in data:
        uname = data['username'].strip().lstrip('@')
        if uname:
            user.username = uname
    if 'avatar_url' in data and data['avatar_url']:
        user.avatar_url = data['avatar_url']

    # Mentor profil maydonlari
    if user.role == 'mentor':
        if not user.mentor_profile:
            mp = MentorProfile(user_id=user.id)
            db.session.add(mp)
            db.session.flush()
        mp = user.mentor_profile
        for field in ['university', 'faculty', 'year', 'bio', 'gpa']:
            if field in data:
                val = data[field]
                if val is not None and str(val).strip() != '':
                    setattr(mp, field, val)
                elif field not in ('year', 'gpa'):
                    setattr(mp, field, val)

    # Student profil qo'shimcha maydonlari (abuturyent)
    if user.role == 'student':
        # Bu maydonlarni User modelida saqlashga urinmaymiz agar yo'q bo'lsa
        pass

    db.session.commit()
    return jsonify({'success': True, 'user': user.to_full_dict()})

@app.route('/api/profile/avatar', methods=['POST'])
def upload_avatar():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Kirilmagan'}), 401
    data = request.json or {}
    avatar_url = data.get('avatar_url', '').strip()
    if not avatar_url:
        return jsonify({'success': False, 'error': 'Avatar URL kerak'}), 400
    user.avatar_url = avatar_url
    db.session.commit()
    return jsonify({'success': True, 'avatar_url': user.avatar_url})

# ==========================================
# SESSIONS
# ==========================================

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Kirilmagan'}), 401

    if user.role == 'student':
        sessions = Session.query.filter_by(student_id=user.id)\
            .order_by(Session.scheduled_at.desc()).limit(50).all()
    elif user.role == 'mentor' and user.mentor_profile:
        sessions = Session.query.filter_by(mentor_id=user.mentor_profile.id)\
            .order_by(Session.scheduled_at.desc()).limit(50).all()
    else:
        sessions = []

    result = []
    for s in sessions:
        mentor_profile = db.session.get(MentorProfile, s.mentor_id)
        mentor_user = db.session.get(User, mentor_profile.user_id) if mentor_profile else None
        student_user = db.session.get(User, s.student_id)

        result.append({
            'id': s.id,
            'session_type': s.session_type,
            'status': s.status,
            'scheduled_at': s.scheduled_at.isoformat() if s.scheduled_at else None,
            'duration_min': s.duration_min,
            'meet_link': s.meet_link,
            'notes': s.notes or '',
            'points_awarded': s.points_awarded or 0,
            'student_rating': s.student_rating,
            'student_review': s.student_review,
            'mentor_name': mentor_user.full_name if mentor_user else None,
            'mentor_avatar': mentor_user.avatar_url if mentor_user else None,
            'student_name': student_user.full_name if student_user else None,
            'student_avatar': student_user.avatar_url if student_user else None,
            'student_phone': student_user.phone if student_user else None,
            'student_university': (student_user.mentor_profile.university
                                   if student_user and student_user.mentor_profile else None),
            'created_at': s.created_at.isoformat() if s.created_at else None,
        })
    return jsonify({'success': True, 'sessions': result})

@app.route('/api/sessions/create', methods=['POST'])
def create_session():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Kirilmagan'}), 401
    data = request.json
    mentor_id = data.get('mentor_id')
    session_type = data.get('session_type', 'individual')
    scheduled_at = data.get('scheduled_at')
    if not mentor_id:
        return jsonify({'success': False, 'error': 'Mentor ID kerak'}), 400
    mentor = db.session.get(MentorProfile, mentor_id)
    if not mentor:
        return jsonify({'success': False, 'error': 'Mentor topilmadi'}), 404
    active_sub = Subscription.query.filter_by(student_id=user.id, status='active').first()
    if not active_sub and session_type != 'free':
        return jsonify({'success': False, 'error': "Faol obuna yo'q"}), 400
    sess = Session(
        student_id=user.id, mentor_id=mentor_id,
        subscription_id=active_sub.id if active_sub else None,
        session_type=session_type, status='pending',
        scheduled_at=datetime.fromisoformat(scheduled_at) if scheduled_at else None
    )
    db.session.add(sess)
    db.session.commit()
    return jsonify({'success': True, 'session_id': sess.id})

@app.route('/api/sessions/<string:session_id>/confirm', methods=['POST'])
def confirm_session(session_id):
    user = get_current_user()
    if not user or user.role != 'mentor':
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    s = db.session.get(Session, session_id)
    if not s:
        abort(404)
    if not user.mentor_profile or s.mentor_id != user.mentor_profile.id:
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    if s.status != 'pending':
        return jsonify({'success': False, 'error': "Sessiya allaqachon o'zgartirilgan"}), 400
    s.status = 'confirmed'
    db.session.commit()
    student = db.session.get(User, s.student_id)
    if student:
        db.session.add(Notification(user_id=student.id, title='✅ Sessiya tasdiqlandi',
            body='Mentoringiz sessiyangizni tasdiqladi.', type='session'))
        db.session.commit()
        if student.telegram_id:
            send_telegram_message(student.telegram_id,
                "✅ <b>Sessiyangiz tasdiqlandi!</b>\nMentor bilan bog'laning.")
    return jsonify({'success': True})

@app.route('/api/sessions/<string:session_id>/reject', methods=['POST'])
def reject_session(session_id):
    user = get_current_user()
    if not user or user.role != 'mentor':
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    s = db.session.get(Session, session_id)
    if not s:
        abort(404)
    if not user.mentor_profile or s.mentor_id != user.mentor_profile.id:
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    if s.status != 'pending':
        return jsonify({'success': False, 'error': "Sessiya allaqachon o'zgartirilgan"}), 400
    s.status = 'cancelled'
    db.session.commit()
    student = db.session.get(User, s.student_id)
    if student and student.telegram_id:
        send_telegram_message(student.telegram_id,
            "❌ <b>Sessiyangiz rad etildi.</b>\nBoshqa mentor tanlashingiz mumkin.")
    return jsonify({'success': True})

# ==========================================
# PAYMENTS & SUBSCRIPTIONS
# ==========================================

@app.route('/api/subscriptions', methods=['GET'])
def get_subscriptions():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Kirilmagan'}), 401
    subs = Subscription.query.filter_by(student_id=user.id).order_by(Subscription.created_at.desc()).all()
    return jsonify({'success': True, 'subscriptions': [{
        'id': s.id, 'tier': s.tier, 'status': s.status, 'price': s.price,
        'started_at': s.started_at.isoformat() if s.started_at else None,
        'expires_at': s.expires_at.isoformat() if s.expires_at else None
    } for s in subs]})

@app.route('/api/subscriptions/create', methods=['POST'])
def create_subscription():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Kirilmagan'}), 401
    data = request.json
    tier = data.get('tier')
    if tier not in ['free', 'group', 'basic', 'elite']:
        return jsonify({'success': False, 'error': "Noto'g'ri tarif"}), 400
    active_sub = Subscription.query.filter_by(student_id=user.id, status='active').first()
    if active_sub:
        active_sub.status = 'cancelled'
    sub = Subscription(student_id=user.id, tier=tier, price=data.get('price', 0),
                       status='pending', expires_at=datetime.utcnow() + timedelta(days=30))
    db.session.add(sub)
    db.session.commit()
    return jsonify({'success': True, 'subscription': {'id': sub.id, 'tier': sub.tier, 'price': sub.price}})

@app.route('/api/subscriptions/<string:sub_id>/activate', methods=['POST'])
def activate_subscription(sub_id):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Kirilmagan'}), 401
    sub = db.session.get(Subscription, sub_id)
    if not sub:
        abort(404)
    if sub.student_id != user.id:
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    sub.status = 'active'
    sub.started_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/payments/create', methods=['POST'])
def create_payment():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Kirilmagan'}), 401
    data = request.json
    amount = data.get('amount')
    method = data.get('method')
    if not amount or not method:
        return jsonify({'success': False, 'error': "Summa va to'lov usuli kerak"}), 400
    payment = Payment(user_id=user.id, amount=amount, method=method,
                      status='pending', meta=data.get('meta', {}))
    db.session.add(payment)
    db.session.commit()
    urls = {}
    if method == 'payme':
        urls['url'] = f"https://checkout.paycom.uz/?amount={amount*100}&order_id={payment.id}"
    elif method == 'click':
        urls['url'] = f"https://my.click.uz/services/pay?amount={amount}&transaction_param={payment.id}"
    return jsonify({'success': True, 'payment': {'id': payment.id, 'amount': payment.amount,
                                                  'status': payment.status, 'urls': urls}})

@app.route('/api/payments/<string:payment_id>/callback', methods=['POST'])
def payment_callback(payment_id):
    payment = db.session.get(Payment, payment_id)
    if not payment:
        abort(404)
    data = request.json
    status = data.get('status')
    if status == 'success':
        payment.status = 'success'
        payment.provider_tx = data.get('transaction')
        if payment.meta and payment.meta.get('subscription_id'):
            sub = db.session.get(Subscription, payment.meta['subscription_id'])
            if sub:
                sub.status = 'active'
                sub.started_at = datetime.utcnow()
    elif status == 'failed':
        payment.status = 'failed'
    db.session.commit()
    return jsonify({'success': True})

# ==========================================
# NOTIFICATIONS
# ==========================================

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Kirilmagan'}), 401
    notifications = Notification.query.filter_by(user_id=user.id)\
        .order_by(Notification.created_at.desc()).limit(20).all()
    return jsonify({'success': True, 'notifications': [{
        'id': n.id, 'title': n.title, 'body': n.body, 'type': n.type,
        'is_read': n.is_read, 'created_at': n.created_at.isoformat()
    } for n in notifications]})

@app.route('/api/notifications/<string:notif_id>/read', methods=['POST'])
def mark_notification_read(notif_id):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Kirilmagan'}), 401
    notif = db.session.get(Notification, notif_id)
    if not notif:
        abort(404)
    if notif.user_id != user.id:
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    notif.is_read = True
    db.session.commit()
    return jsonify({'success': True})

# ==========================================
# STATS (public)
# ==========================================

@app.route('/api/stats', methods=['GET'])
def get_stats():
    return jsonify({'success': True, 'stats': {
        'students': User.query.filter_by(role='student').count(),
        'mentors': MentorProfile.query.filter_by(is_verified=True).count(),
        'sessions': Session.query.count()
    }})

# ==========================================
# MENTOR SPECIFIC
# ==========================================

@app.route('/api/mentor/student-id-status', methods=['GET'])
def mentor_student_id_status():
    user = get_current_user()
    if not user or user.role != 'mentor':
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    mentor = user.mentor_profile
    if not mentor:
        return jsonify({'success': False, 'error': 'Mentor profil topilmadi'}), 404
    days_left = None
    if mentor.created_at:
        deadline = mentor.created_at + timedelta(days=3)
        days_left = max(0, (deadline - datetime.utcnow()).days)
    return jsonify({
        'success': True,
        'is_verified': mentor.is_verified,
        'student_id_url': mentor.student_id_url,
        'days_left': days_left,
        'created_at': mentor.created_at.isoformat() if mentor.created_at else None,
        'verified_at': mentor.verified_at.isoformat() if mentor.verified_at else None
    })

@app.route('/api/mentor/points', methods=['GET'])
def mentor_points():
    user = get_current_user()
    if not user or user.role != 'mentor':
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    mentor = user.mentor_profile
    if not mentor:
        return jsonify({'success': False, 'error': 'Mentor profil topilmadi'}), 404
    reason_map = {
        'session_completed': 'Sessiya yakunlandi',
        'bonus': 'Bonus',
        'withdrawal': 'Pul yechildi',
        'penalty': 'Jarima',
        'refund': 'Qaytarildi'
    }
    points = MentorPoint.query.filter_by(mentor_id=mentor.id)\
        .order_by(MentorPoint.created_at.desc()).limit(100).all()
    return jsonify({'success': True, 'points': [{
        'id': p.id,
        'points': p.points,
        'reason': p.reason,
        'reason_text': reason_map.get(p.reason, p.reason or 'Tranzaksiya'),
        'balance_after': p.balance_after,
        'session_id': p.session_id,
        'created_at': p.created_at.isoformat() if p.created_at else None
    } for p in points]})

@app.route('/api/mentor/certificates', methods=['GET'])
def get_mentor_certificates():
    user = get_current_user()
    if not user or user.role != 'mentor':
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    mentor = user.mentor_profile
    if not mentor:
        return jsonify({'success': False, 'error': 'Mentor profil topilmadi'}), 404
    certs = MentorCertificate.query.filter_by(mentor_id=mentor.id)\
        .order_by(MentorCertificate.created_at.desc()).all()
    return jsonify({'success': True, 'certificates': [{
        'id': c.id, 'title': c.title, 'issuer': c.issuer,
        'date': c.issued_date.isoformat() if c.issued_date else None, 'file_url': c.file_url
    } for c in certs]})

@app.route('/api/mentor/certificates', methods=['POST'])
def add_mentor_certificate():
    user = get_current_user()
    if not user or user.role != 'mentor':
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    mentor = user.mentor_profile
    if not mentor:
        return jsonify({'success': False, 'error': 'Mentor profil topilmadi'}), 404
    data = request.json
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({'success': False, 'error': 'Sertifikat nomi kerak'}), 400
    issued_date = None
    if data.get('date'):
        try:
            issued_date = date.fromisoformat(data['date'])
        except:
            pass
    cert = MentorCertificate(mentor_id=mentor.id, title=title,
                              issuer=data.get('issuer') or None, issued_date=issued_date)
    db.session.add(cert)
    db.session.commit()
    return jsonify({'success': True, 'certificate': {
        'id': cert.id, 'title': cert.title, 'issuer': cert.issuer,
        'date': cert.issued_date.isoformat() if cert.issued_date else None, 'file_url': cert.file_url
    }})

@app.route('/api/mentor/certificates/<string:cert_id>', methods=['DELETE'])
def delete_mentor_certificate(cert_id):
    user = get_current_user()
    if not user or user.role != 'mentor':
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    cert = db.session.get(MentorCertificate, cert_id)
    if not cert:
        abort(404)
    if cert.mentor_id != user.mentor_profile.id:
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    db.session.delete(cert)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/mentor/card', methods=['POST'])
def save_mentor_card():
    user = get_current_user()
    if not user or user.role != 'mentor':
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    mentor = user.mentor_profile
    if not mentor:
        return jsonify({'success': False, 'error': 'Mentor profil topilmadi'}), 404
    data = request.json or {}

    # card_number (to'liq) yoki card_last4 (oxirgi 4) qabul qilamiz
    card_number = data.get('card_number', '').replace(' ', '').replace('-', '')
    card_last4 = data.get('card_last4', '').strip()
    card_holder = data.get('card_holder', '').strip().upper()

    # card_last4 ni card_number dan olish
    if card_number and len(card_number) >= 4:
        card_last4 = card_number[-4:]
    elif not card_last4 or len(card_last4) != 4:
        return jsonify({'success': False, 'error': "Karta raqami noto'g'ri"}), 400

    if not card_holder:
        return jsonify({'success': False, 'error': "Karta egasi nomini kiriting"}), 400

    mentor.card_last4 = card_last4
    mentor.card_holder = card_holder
    db.session.commit()
    return jsonify({'success': True, 'card_last4': card_last4, 'card_holder': card_holder})

@app.route('/api/mentor/withdraw', methods=['POST'])
def mentor_withdraw():
    user = get_current_user()
    if not user or user.role != 'mentor':
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    mentor = user.mentor_profile
    if not mentor:
        return jsonify({'success': False, 'error': 'Mentor profil topilmadi'}), 404
    data = request.json or {}
    amount = int(data.get('amount', 0))
    if amount < 50000:
        return jsonify({'success': False, 'error': "Minimal 50,000 so'm"}), 400
    if amount > (mentor.balance or 0):
        return jsonify({'success': False, 'error': 'Balans yetarli emas'}), 400
    if not mentor.card_last4:
        return jsonify({'success': False, 'error': 'Avval karta raqamini kiriting'}), 400
    existing = Withdrawal.query.filter_by(mentor_id=mentor.id, status='pending').first()
    if existing:
        return jsonify({'success': False, 'error': "Avvalgi so'rovingiz hali ko'rib chiqilmoqda"}), 400

    wd = Withdrawal(
        mentor_id=mentor.id,
        amount=amount,
        points_used=amount,
        card_last4=mentor.card_last4,
        card_holder=mentor.card_holder,
        status='pending'
    )
    db.session.add(wd)
    db.session.commit()

    # Adminlarga Telegram xabari yuborish
    admins = User.query.filter(User.role.in_(['admin', 'superadmin']), User.is_active == True).all()
    for admin in admins:
        if admin.telegram_id:
            msg = (
                f"💸 <b>Yangi pul yechish so'rovi!</b>\n\n"
                f"👤 <b>Mentor:</b> {user.full_name}\n"
                f"📞 <b>Tel:</b> {user.phone or '—'}\n"
                f"💳 <b>Karta:</b> •••• {mentor.card_last4} | {mentor.card_holder or '—'}\n"
                f"💰 <b>Summa:</b> {amount:,} so'm\n"
                f"🆔 <b>ID:</b> {wd.id[:8]}"
            )
            send_telegram_message(admin.telegram_id, msg)

    # Mentorga tasdiq xabari
    if user.telegram_id:
        send_telegram_message(
            user.telegram_id,
            f"✅ <b>Pul yechish so'rovi qabul qilindi!</b>\n\n"
            f"💰 Summa: <b>{amount:,} so'm</b>\n"
            f"💳 Karta: •••• {mentor.card_last4}\n"
            f"⏳ 24 soat ichida ko'rib chiqiladi."
        )

    return jsonify({'success': True, 'withdrawal_id': wd.id})

@app.route('/api/mentor/upload-student-id', methods=['POST'])
def upload_student_id():
    user = get_current_user()
    if not user or user.role != 'mentor':
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    if 'student_id' not in request.files:
        return jsonify({'success': False, 'error': "Fayl yo'q"}), 400
    file = request.files['student_id']
    if not file.filename:
        return jsonify({'success': False, 'error': 'Fayl tanlanmagan'}), 400
    upload_folder = 'uploads/student_ids'
    os.makedirs(upload_folder, exist_ok=True)
    filename = secure_filename(f"student_id_{user.id}.jpg")
    file.save(os.path.join(upload_folder, filename))
    if not user.mentor_profile:
        db.session.add(MentorProfile(user_id=user.id))
        db.session.flush()
    user.mentor_profile.student_id_url = f"/uploads/student_ids/{filename}"
    db.session.commit()
    return jsonify({'success': True, 'url': user.mentor_profile.student_id_url})

@app.route('/api/mentor/documents', methods=['POST'])
def upload_mentor_document():
    user = get_current_user()
    if not user or user.role != 'mentor':
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    mentor = user.mentor_profile
    if not mentor:
        return jsonify({'success': False, 'error': 'Mentor profil topilmadi'}), 404
    if 'document' not in request.files:
        return jsonify({'success': False, 'error': "Fayl yo'q"}), 400
    file = request.files['document']
    doc_type = request.form.get('type', 'other')
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'pdf'
    filename = secure_filename(f"{doc_type}_{user.id}.{ext}")
    folder = 'uploads/documents'
    os.makedirs(folder, exist_ok=True)
    file.save(os.path.join(folder, filename))
    doc = MentorDocument(mentor_id=mentor.id, doc_type=doc_type,
                         title=file.filename, file_url=f'/uploads/documents/{filename}')
    db.session.add(doc)
    db.session.commit()
    return jsonify({'success': True, 'url': doc.file_url})

# ==========================================
# MENTOR DASHBOARD
# ==========================================

@app.route('/api/mentor/dashboard', methods=['GET'])
def mentor_dashboard():
    user = get_current_user()
    if not user or user.role != 'mentor':
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    mentor = user.mentor_profile
    if not mentor:
        return jsonify({'success': False, 'error': 'Mentor profil topilmadi'}), 404

    from sqlalchemy import func

    total_sessions = Session.query.filter_by(mentor_id=mentor.id).count()
    completed = Session.query.filter_by(mentor_id=mentor.id, status='completed').count()
    pending = Session.query.filter_by(mentor_id=mentor.id, status='pending').count()
    confirmed = Session.query.filter_by(mentor_id=mentor.id, status='confirmed').count()
    students = db.session.query(Session.student_id)\
        .filter_by(mentor_id=mentor.id).distinct().count()
    rated = Session.query.filter(Session.mentor_id == mentor.id,
                                 Session.student_rating.isnot(None)).all()
    avg_rating = round(sum(s.student_rating for s in rated) / len(rated), 1) if rated else 0.0

    upcoming = Session.query.filter_by(mentor_id=mentor.id, status='confirmed')\
        .filter(Session.scheduled_at >= datetime.utcnow())\
        .order_by(Session.scheduled_at).limit(5).all()

    # ── FIX 4: datetime.combine to'g'ri ishlatilmoqda ──
    today = datetime.utcnow().date()
    weekly = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        # ── FIX 5: datetime.min/max o'rniga to'g'ri datetime ──
        day_start = datetime(day.year, day.month, day.day, 0, 0, 0)
        day_end = datetime(day.year, day.month, day.day, 23, 59, 59)
        day_pts = db.session.query(func.sum(MentorPoint.points)).filter(
            MentorPoint.mentor_id == mentor.id,
            MentorPoint.points > 0,
            MentorPoint.created_at.between(day_start, day_end)
        ).scalar() or 0
        weekly.append({'date': day.isoformat(), 'points': int(day_pts)})

    pending_list = Session.query.filter_by(mentor_id=mentor.id, status='pending')\
        .order_by(Session.created_at.desc()).limit(10).all()

    def session_to_dict(s):
        student = db.session.get(User, s.student_id)
        return {
            'id': s.id, 'session_type': s.session_type, 'status': s.status,
            'scheduled_at': s.scheduled_at.isoformat() if s.scheduled_at else None,
            'student_name': student.full_name if student else "Noma'lum",
            'student_avatar': student.avatar_url if student else None,
            'student_phone': student.phone if student else None,
            'meet_link': s.meet_link, 'points_awarded': s.points_awarded,
            'duration_min': s.duration_min,
        }

    return jsonify({
        'success': True,
        'stats': {
            'balance': mentor.balance or 0,
            'total_sessions': total_sessions,
            'completed': completed,
            'pending': pending,
            'confirmed': confirmed,
            'students': students,
            'avg_rating': avg_rating,
            'is_verified': mentor.is_verified,
            'card_last4': mentor.card_last4,
            'card_holder': mentor.card_holder,
        },
        'weekly_earnings': weekly,
        'upcoming_sessions': [session_to_dict(s) for s in upcoming],
        'pending_requests': [session_to_dict(s) for s in pending_list],
    })

# ==========================================
# MENTOR VIDEOS
# ==========================================

@app.route('/api/mentor/videos', methods=['GET'])
def get_mentor_videos():
    user = get_current_user()
    if not user or user.role != 'mentor':
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    if not user.mentor_profile:
        return jsonify({'success': False, 'error': 'Mentor profil topilmadi'}), 404

    access = request.args.get('access')  # 'free' | 'premium' | None

    # ── FIX 6: Mavjud maydonlarga qarab filter ──
    try:
        videos_q = Material.query.filter(
            Material.material_type.in_(['video', 'youtube'])
        ).order_by(Material.created_at.desc())
        # Agar mentor_id maydoni mavjud bo'lsa, filter qo'llaymiz
        if hasattr(Material, 'mentor_id'):
            videos_q = videos_q.filter(Material.mentor_id == user.mentor_profile.id)
        videos = videos_q.all()
    except Exception:
        videos = []

    result = []
    for v in videos:
        d = v.to_dict()
        if access:
            v_access = getattr(v, 'access_type', 'free')
            if v_access != access:
                continue
        result.append(d)

    top5 = sorted(result, key=lambda x: x.get('views', 0), reverse=True)[:5]
    total_views = sum(v.get('views', 0) for v in result)
    free_count = sum(1 for v in result if v.get('access_type', 'free') != 'premium')
    premium_count = sum(1 for v in result if v.get('access_type', 'free') == 'premium')

    return jsonify({
        'success': True, 'videos': result, 'top5': top5,
        'stats': {'total': len(result), 'total_views': total_views,
                  'free': free_count, 'premium': premium_count}
    })

@app.route('/api/mentor/videos', methods=['POST'])
def add_mentor_video():
    user = get_current_user()
    if not user or user.role != 'mentor':
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    mentor = user.mentor_profile
    if not mentor:
        return jsonify({'success': False, 'error': 'Mentor profil topilmadi'}), 404
    data = request.get_json(force=True, silent=True) or {}
    title = data.get('title', '').strip()
    url = data.get('url', '').strip()
    if not title or not url:
        return jsonify({'success': False, 'error': 'Sarlavha va URL kerak'}), 400
    mat_type = 'youtube' if ('youtube.com' in url or 'youtu.be' in url) else 'video'
    video = Material(title=title, material_type=mat_type, url=url)
    # Ixtiyoriy maydonlar — faqat mavjud bo'lsa o'rnatiladi
    optional = {
        'description': data.get('description', ''),
        'access_type': data.get('access_type', 'free'),
        'mentor_id': mentor.id,
        'views': 0,
    }
    for attr, val in optional.items():
        if hasattr(video, attr):
            setattr(video, attr, val)
    db.session.add(video)
    db.session.commit()
    return jsonify({'success': True, 'video': video.to_dict()})

@app.route('/api/mentor/videos/<string:video_id>', methods=['DELETE'])
def delete_mentor_video(video_id):
    user = get_current_user()
    if not user or user.role != 'mentor':
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    video = db.session.get(Material, video_id)
    if not video:
        abort(404)
    if hasattr(video, 'mentor_id') and video.mentor_id and \
       user.mentor_profile and video.mentor_id != user.mentor_profile.id:
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    db.session.delete(video)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/mentor/videos/<string:video_id>/view', methods=['POST'])
def increment_video_view(video_id):
    video = db.session.get(Material, video_id)
    if not video:
        abort(404)
    if hasattr(video, 'views'):
        video.views = (video.views or 0) + 1
        db.session.commit()
    return jsonify({'success': True})

# ==========================================
# NEWS & MATERIALS
# ==========================================

@app.route('/api/news', methods=['GET'])
def get_news_filtered():
    target = request.args.get('target')  # 'abuturyent' | 'mentor' | None
    query = News.query.order_by(News.created_at.desc())
    news_list = query.all()
    result = []
    for n in news_list:
        n_dict = n.to_dict()
        # target filter: agar news.target yo'q bo'lsa yoki 'all' bo'lsa hammaga ko'rinadi
        n_target = getattr(n, 'target', None)
        if target and n_target and n_target != 'all' and n_target != target:
            continue
        # Qo'shimcha maydonlar (model da bo'lmasa xavfsiz)
        n_dict['category'] = getattr(n, 'category', 'general') or 'general'
        n_dict['priority'] = getattr(n, 'priority', 'normal') or 'normal'
        n_dict['image_url'] = getattr(n, 'image_url', '') or ''
        n_dict['link'] = getattr(n, 'link', '') or ''
        n_dict['target'] = n_target or 'all'
        result.append(n_dict)
    return jsonify({'success': True, 'news': result})

@app.route('/api/materials', methods=['GET'])
def get_materials():
    mats = Material.query.order_by(Material.created_at.desc()).all()
    result = []
    for m in mats:
        d = m.to_dict()
        # Ixtiyoriy maydonlar (model da bo'lmasa ham xavfsiz)
        d['access_type'] = getattr(m, 'access_type', 'free') or 'free'
        d['access'] = d['access_type']
        d['views'] = getattr(m, 'views', 0) or 0
        d['thumbnail'] = getattr(m, 'thumbnail', '') or ''
        d['description'] = getattr(m, 'description', '') or ''
        # YouTube thumbnail avtomatik
        if not d['thumbnail'] and d.get('url'):
            import re
            ym = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([^&\s]+)', d['url'])
            if ym:
                d['thumbnail'] = f"https://img.youtube.com/vi/{ym.group(1)}/hqdefault.jpg"
        result.append(d)
    return jsonify({'success': True, 'materials': result})

# ==========================================
# ADMIN
# ==========================================

@app.route('/api/admin/stats', methods=['GET'])
def admin_stats():
    admin = get_current_user()
    if not admin or admin.role not in ['admin', 'superadmin']:
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    return jsonify({'success': True, 'stats': {
        'students': User.query.filter_by(role='student').count(),
        'mentors': MentorProfile.query.filter_by(is_verified=True).count(),
        'sessions': Session.query.count(),
        'pending_mentors': MentorProfile.query.filter_by(is_verified=False).count(),
        'pending_withdrawals': Withdrawal.query.filter_by(status='pending').count()
    }})

@app.route('/api/admin/students', methods=['GET'])
def admin_get_students():
    user = get_current_user()
    if not user or user.role not in ['admin', 'superadmin']:
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    students = User.query.filter_by(role='student').all()
    return jsonify({'success': True, 'students': [{
        **s.to_dict(),
        'subscription_tier': getattr(s.subscriptions[0], 'tier', 'free') if s.subscriptions else 'free',
        'total_sessions': len(s.sessions_as_student)
    } for s in students]})

@app.route('/api/admin/mentors', methods=['GET'])
def admin_get_mentors():
    user = get_current_user()
    if not user or user.role not in ['admin', 'superadmin']:
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    mentors = MentorProfile.query.all()
    result = []
    for m in mentors:
        u = db.session.get(User, m.user_id)
        if u:
            result.append({**m.to_dict(), 'full_name': u.full_name, 'phone': u.phone,
                           'telegram_id': u.telegram_id, 'is_active': u.is_active})
    return jsonify({'success': True, 'mentors': result})

@app.route('/api/admin/mentors/pending', methods=['GET'])
def admin_get_pending_mentors():
    user = get_current_user()
    if not user or user.role not in ['admin', 'superadmin']:
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    mentors = MentorProfile.query.filter_by(is_verified=False).limit(20).all()
    result = []
    for m in mentors:
        u = db.session.get(User, m.user_id)
        if u:
            result.append({**m.to_dict(), 'full_name': u.full_name,
                           'phone': u.phone, 'telegram_id': u.telegram_id})
    return jsonify({'success': True, 'mentors': result})

@app.route('/api/admin/mentors/verify', methods=['GET'])
def admin_get_verify_mentors():
    user = get_current_user()
    if not user or user.role not in ['admin', 'superadmin']:
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    mentors = MentorProfile.query.filter(MentorProfile.student_id_url.isnot(None)).all()
    result = []
    for m in mentors:
        u = db.session.get(User, m.user_id)
        if u:
            result.append({
                **m.to_dict(), 'full_name': u.full_name, 'phone': u.phone,
                'telegram_id': u.telegram_id,
                'student_id_uploaded_at': getattr(m, 'student_id_uploaded_at', None) and
                                          m.student_id_uploaded_at.isoformat(),
                'created_at': u.created_at.isoformat()
            })
    return jsonify({'success': True, 'mentors': result})

@app.route('/api/admin/mentors/<string:mentor_id>/verify', methods=['POST'])
def admin_verify_mentor(mentor_id):
    admin = get_current_user()
    if not admin or admin.role not in ['admin', 'superadmin']:
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    mentor = db.session.get(MentorProfile, mentor_id)
    if not mentor:
        abort(404)
    mentor.is_verified = True
    mentor.verified_at = datetime.utcnow()
    mentor.verified_by = admin.id
    db.session.add(Notification(user_id=mentor.user_id, title='✅ Mentor tasdiqlandi!',
        body='Sizning mentoringiz ConnectU platformasida tasdiqlandi. Endi sessiyalar qabul qilishingiz mumkin.',
        type='verification'))
    db.session.commit()
    user = db.session.get(User, mentor.user_id)
    if user and user.telegram_id:
        send_telegram_message(user.telegram_id,
            "🎉 <b>Mentor profilingiz tasdiqlandi!</b>\n\nEndi sessiyalar qabul qila olasiz.")
    return jsonify({'success': True})

@app.route('/api/admin/mentors/<string:mentor_id>/suspend', methods=['POST'])
def admin_suspend_mentor(mentor_id):
    admin = get_current_user()
    if not admin or admin.role not in ['admin', 'superadmin']:
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    mentor = db.session.get(MentorProfile, mentor_id)
    if not mentor:
        abort(404)
    user = db.session.get(User, mentor.user_id)
    if user:
        user.is_active = False
        db.session.commit()
    return jsonify({'success': True})

@app.route('/api/admin/mentors/<string:mentor_id>/documents', methods=['GET'])
def admin_get_mentor_documents(mentor_id):
    admin = get_current_user()
    if not admin or admin.role not in ['admin', 'superadmin']:
        return jsonify({'success': False}), 403
    mentor = db.session.get(MentorProfile, mentor_id)
    if not mentor:
        abort(404)
    return jsonify({'success': True, 'student_id_url': mentor.student_id_url,
                    'is_verified': mentor.is_verified, 'verified_at': mentor.verified_at})

@app.route('/api/admin/sessions', methods=['GET'])
def admin_get_sessions():
    user = get_current_user()
    if not user or user.role not in ['admin', 'superadmin']:
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    sessions = Session.query.order_by(Session.created_at.desc()).limit(50).all()
    result = []
    for s in sessions:
        student = db.session.get(User, s.student_id)
        mentor = db.session.get(MentorProfile, s.mentor_id)
        mentor_user = db.session.get(User, mentor.user_id) if mentor else None
        result.append({
            'id': s.id,
            'student_name': student.full_name if student else None,
            'mentor_name': mentor_user.full_name if mentor_user else None,
            'session_type': s.session_type, 'status': s.status,
            'scheduled_at': s.scheduled_at.isoformat() if s.scheduled_at else None,
            'points_awarded': s.points_awarded,
            'created_at': s.created_at.isoformat()
        })
    return jsonify({'success': True, 'sessions': result})

@app.route('/api/admin/withdrawals', methods=['GET'])
def admin_get_withdrawals():
    user = get_current_user()
    if not user or user.role not in ['admin', 'superadmin']:
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    status = request.args.get('status', 'all')
    query = Withdrawal.query
    if status != 'all':
        query = query.filter_by(status=status)
    withdrawals = query.order_by(Withdrawal.created_at.desc()).all()
    result = []
    for w in withdrawals:
        mentor = db.session.get(MentorProfile, w.mentor_id)
        mentor_user = db.session.get(User, mentor.user_id) if mentor else None
        result.append({
            'id': w.id,
            'mentor_name': mentor_user.full_name if mentor_user else None,
            'mentor_phone': mentor_user.phone if mentor_user else None,
            'mentor_telegram': str(mentor_user.telegram_id) if mentor_user and mentor_user.telegram_id else None,
            'amount': w.amount,
            'points_used': w.points_used,
            'card_last4': w.card_last4,
            'card_holder': w.card_holder,
            'status': w.status,
            'admin_note': w.admin_note,
            'processed_at': w.processed_at.isoformat() if w.processed_at else None,
            'created_at': w.created_at.isoformat() if w.created_at else None
        })
    return jsonify({'success': True, 'withdrawals': result})

@app.route('/api/admin/withdrawals/pending', methods=['GET'])
def admin_get_pending_withdrawals():
    admin = get_current_user()
    if not admin or admin.role not in ['admin', 'superadmin']:
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    withdrawals = Withdrawal.query.filter_by(status='pending')\
        .order_by(Withdrawal.created_at).all()
    result = []
    for w in withdrawals:
        mentor = db.session.get(MentorProfile, w.mentor_id)
        user = db.session.get(User, mentor.user_id) if mentor else None
        result.append({
            'id': w.id,
            'amount': w.amount,
            'points_used': w.points_used,
            'card_last4': w.card_last4,
            'card_holder': w.card_holder,
            'mentor_name': user.full_name if user else None,
            'mentor_phone': user.phone if user else None,
            'mentor_telegram': str(user.telegram_id) if user and user.telegram_id else None,
            'status': w.status,
            'created_at': w.created_at.isoformat() if w.created_at else None
        })
    return jsonify({'success': True, 'withdrawals': result})

@app.route('/api/admin/withdrawals/<string:wd_id>/approve', methods=['POST'])
def admin_approve_withdrawal(wd_id):
    admin = get_current_user()
    if not admin or admin.role not in ['admin', 'superadmin']:
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    wd = db.session.get(Withdrawal, wd_id)
    if not wd:
        abort(404)
    wd.status = 'approved'
    wd.processed_by = admin.id
    wd.processed_at = datetime.utcnow()
    mentor = db.session.get(MentorProfile, wd.mentor_id)
    if mentor:
        mentor.balance = (mentor.balance or 0) - wd.points_used
        db.session.add(MentorPoint(mentor_id=wd.mentor_id, points=-wd.points_used,
                                   reason='withdrawal', balance_after=mentor.balance))
    db.session.commit()
    user = db.session.get(User, mentor.user_id) if mentor else None
    if user:
        db.session.add(Notification(user_id=user.id, title="💰 Withdrawal tasdiqlandi",
            body=f"{wd.amount:,} so'm so'rovingiz tasdiqlandi va tez orada kartangizga o'tkaziladi.",
            type='points'))
        db.session.commit()
    return jsonify({'success': True})

@app.route('/api/admin/withdrawals/<string:wd_id>/reject', methods=['POST'])
def admin_reject_withdrawal(wd_id):
    admin = get_current_user()
    if not admin or admin.role not in ['admin', 'superadmin']:
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    wd = db.session.get(Withdrawal, wd_id)
    if not wd:
        abort(404)
    data = request.json or {}
    wd.status = 'rejected'
    wd.admin_note = data.get('reason', '')
    wd.processed_by = admin.id
    wd.processed_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/admin/broadcast', methods=['POST'])
def admin_broadcast():
    admin = get_current_user()
    if not admin or admin.role not in ['admin', 'superadmin']:
        return jsonify({'success': False, 'error': "Ruxsat yo'q"}), 403
    data = request.json
    title = data.get('title')
    text = data.get('text')
    targets = data.get('targets', ['all'])
    users = User.query.filter_by(is_active=True).all()
    sent_count = 0
    for user in users:
        if 'all' in targets or user.role in targets:
            if user.telegram_id:
                send_telegram_message(user.telegram_id, f"📢 <b>{title}</b>\n\n{text}")
                sent_count += 1
    return jsonify({'success': True, 'sent': sent_count})

@app.route('/api/admin/news', methods=['POST'])
def add_news():
    admin = get_current_user()
    if not admin or admin.role not in ['admin', 'superadmin']:
        return jsonify({'success': False, 'error': 'Ruxsat yoq'}), 403
    data = request.json
    if not data.get('title') or not data.get('content'):
        return jsonify({'success': False, 'error': 'Sarlavha va matn kerak'}), 400
    news = News(title=data['title'], content=data['content'])
    db.session.add(news)
    db.session.commit()
    return jsonify({'success': True, 'news': news.to_dict()})

@app.route('/api/admin/news/<string:news_id>', methods=['DELETE'])
def delete_news(news_id):
    admin = get_current_user()
    if not admin or admin.role not in ['admin', 'superadmin']:
        return jsonify({'success': False, 'error': 'Ruxsat yoq'}), 403
    news = db.session.get(News, news_id)
    if news:
        db.session.delete(news)
        db.session.commit()
    return jsonify({'success': True})

@app.route('/api/admin/materials', methods=['POST'])
def add_material():
    admin = get_current_user()
    if not admin or admin.role not in ['admin', 'superadmin']:
        return jsonify({'success': False, 'error': 'Ruxsat yoq'}), 403
    title = request.form.get('title')
    mat_type = request.form.get('type')
    if not title or not mat_type:
        return jsonify({'success': False, 'error': "Ma'lumot to'liq emas"}), 400
    url = ""
    if mat_type == 'link':
        url = request.form.get('url', '')
        if not url:
            return jsonify({'success': False, 'error': 'Link kiriting'}), 400
    elif mat_type == 'file':
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'Fayl tanlanmagan'}), 400
        file = request.files['file']
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'mp4'
        filename = secure_filename(f"mat_{uuid.uuid4().hex[:8]}.{ext}")
        file.save(os.path.join(UPLOAD_FOLDER, 'materials', filename))
        url = f"/uploads/materials/{filename}"
    mat = Material(title=title, material_type=mat_type, url=url)
    db.session.add(mat)
    db.session.commit()
    return jsonify({'success': True, 'material': mat.to_dict()})

@app.route('/api/admin/materials/<string:mat_id>', methods=['DELETE'])
def delete_material(mat_id):
    admin = get_current_user()
    if not admin or admin.role not in ['admin', 'superadmin']:
        return jsonify({'success': False, 'error': 'Ruxsat yoq'}), 403
    mat = db.session.get(Material, mat_id)
    if mat:
        db.session.delete(mat)
        db.session.commit()
    return jsonify({'success': True})

# ── FIX 7: SQLAlchemy to'g'ri filter sintaksisi ──
def cleanup_unverified_mentors():
    three_days_ago = datetime.utcnow() - timedelta(days=3)
    unverified = MentorProfile.query.filter(
        MentorProfile.is_verified == False,
        MentorProfile.student_id_url.is_(None),   # None tekshiruvi to'g'ri
        MentorProfile.created_at < three_days_ago
    ).all()
    for mentor in unverified:
        user = db.session.get(User, mentor.user_id)
        if user:
            if user.telegram_id:
                send_telegram_message(user.telegram_id,
                    "❌ <b>Profilingiz o'chirildi.</b>\n"
                    "3 kun ichida talabalik guvohnomasini yuklamaganingiz sababli "
                    "mentor profilingiz avtomatik o'chirildi.\n"
                    "Qayta ro'yxatdan o'tishingiz mumkin.")
            db.session.delete(mentor)
            db.session.delete(user)
    db.session.commit()
    return len(unverified)

@app.route('/api/admin/cleanup-mentors', methods=['POST'])
def admin_cleanup_mentors():
    admin = get_current_user()
    if not admin or admin.role not in ['admin', 'superadmin']:
        return jsonify({'success': False}), 403
    count = cleanup_unverified_mentors()
    return jsonify({'success': True, 'deleted': count})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
