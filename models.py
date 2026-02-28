from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
import random
import json

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=True)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    full_name = db.Column(db.String(200), nullable=False, default='Foydalanuvchi')
    username = db.Column(db.String(100))
    avatar_url = db.Column(db.String(500))
    role = db.Column(db.String(20), nullable=False, default='student')
    is_active = db.Column(db.Boolean, default=True)
    password_hash = db.Column(db.String(64), nullable=True)  # 🔥 SHA-256 hash (yangi qator)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
     
    # Relationships - MUHIM: foreign_keys aniq ko'rsatilgan
    mentor_profile = db.relationship('MentorProfile', 
                                    backref='user', 
                                    uselist=False, 
                                    cascade='all, delete-orphan',
                                    foreign_keys='MentorProfile.user_id')
    
    subscriptions = db.relationship('Subscription', 
                                   backref='student', 
                                   cascade='all, delete-orphan',
                                   foreign_keys='Subscription.student_id')
    
    sessions_as_student = db.relationship('Session', 
                                         backref='student', 
                                         cascade='all, delete-orphan',
                                         foreign_keys='Session.student_id')
    
    notifications = db.relationship('Notification', 
                                   backref='user', 
                                   cascade='all, delete-orphan',
                                   foreign_keys='Notification.user_id')
    
    payments = db.relationship('Payment', 
                              backref='user', 
                              cascade='all, delete-orphan',
                              foreign_keys='Payment.user_id')
    
    # Mentor tomonidan verifikatsiya qilinganlar (verified_by uchun)
    verified_mentors = db.relationship('MentorProfile', 
                                      foreign_keys='MentorProfile.verified_by',
                                      backref='verified_by_user')
    
    def to_dict(self):
        return {
            'id': self.id,
            'telegram_id': self.telegram_id,
            'phone': self.phone,
            'full_name': self.full_name,
            'username': self.username,
            'avatar_url': self.avatar_url,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def to_full_dict(self):
        data = self.to_dict()
        if self.mentor_profile:
            data['mentor_profile'] = self.mentor_profile.to_dict()
        return data


class MentorProfile(db.Model):
    __tablename__ = 'mentor_profiles'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    
    # Asosiy ma'lumotlar
    university = db.Column(db.String(200))
    faculty = db.Column(db.String(200))
    year = db.Column(db.Integer)
    bio = db.Column(db.Text)
    gpa = db.Column(db.Numeric(3, 2))
    
    # Hujjatlar
    student_id_url = db.Column(db.String(500))
    student_id_uploaded_at = db.Column(db.DateTime, nullable=True)  # 🔥 Yangi!

    # Verifikatsiya
    is_verified = db.Column(db.Boolean, default=False)
    verified_at = db.Column(db.DateTime)
    verified_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    
    # Statistika
    rating = db.Column(db.Numeric(3, 2), default=5.00)
    total_sessions = db.Column(db.Integer, default=0)
    total_reviews = db.Column(db.Integer, default=0)
    
    # Balans
    balance = db.Column(db.Integer, default=0)
    
    # To'lov kartasi
    card_last4 = db.Column(db.String(4))
    card_holder = db.Column(db.String(200))
    card_token = db.Column(db.String(500))  # Payme/Click token
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - MUHIM: foreign_keys aniq ko'rsatilgan
    certificates = db.relationship('MentorCertificate', 
                                  backref='mentor', 
                                  cascade='all, delete-orphan',
                                  foreign_keys='MentorCertificate.mentor_id')
    
    documents = db.relationship('MentorDocument', 
                               backref='mentor', 
                               cascade='all, delete-orphan',
                               foreign_keys='MentorDocument.mentor_id')
    
    sessions = db.relationship('Session', 
                              backref='mentor', 
                              cascade='all, delete-orphan',
                              foreign_keys='Session.mentor_id')
    
    points = db.relationship('MentorPoint', 
                            backref='mentor', 
                            cascade='all, delete-orphan',
                            foreign_keys='MentorPoint.mentor_id')
    
    withdrawals = db.relationship('Withdrawal', 
                                 backref='mentor', 
                                 cascade='all, delete-orphan',
                                 foreign_keys='Withdrawal.mentor_id')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'university': self.university,
            'faculty': self.faculty,
            'year': self.year,
            'bio': self.bio,
            'gpa': float(self.gpa) if self.gpa else None,
            'is_verified': self.is_verified,
            'rating': float(self.rating) if self.rating else 5.0,
            'total_sessions': self.total_sessions,
            'total_reviews': self.total_reviews,
            'balance': self.balance,
            'card_last4': self.card_last4,
            'card_holder': self.card_holder
        }


class MentorCertificate(db.Model):
    __tablename__ = 'mentor_certificates'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    mentor_id = db.Column(db.String(36), db.ForeignKey('mentor_profiles.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    issuer = db.Column(db.String(200))
    issued_date = db.Column(db.Date)
    file_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MentorDocument(db.Model):
    __tablename__ = 'mentor_documents'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    mentor_id = db.Column(db.String(36), db.ForeignKey('mentor_profiles.id', ondelete='CASCADE'), nullable=False)
    doc_type = db.Column(db.String(20))  # cv, portfolio, transcript, other
    title = db.Column(db.String(200))
    file_url = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    tier = db.Column(db.String(20), nullable=False)  # free, group, basic, elite
    status = db.Column(db.String(20), default='active')  # active, expired, cancelled
    price = db.Column(db.Integer, nullable=False, default=0)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    payment_id = db.Column(db.String(36))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sessions = db.relationship('Session', 
                              backref='subscription', 
                              cascade='all, delete-orphan',
                              foreign_keys='Session.subscription_id')


class Session(db.Model):
    __tablename__ = 'sessions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    mentor_id = db.Column(db.String(36), db.ForeignKey('mentor_profiles.id'), nullable=False)
    subscription_id = db.Column(db.String(36), db.ForeignKey('subscriptions.id'))
    
    session_type = db.Column(db.String(20))  # group, individual, video
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, completed, cancelled, no_show
    scheduled_at = db.Column(db.DateTime)
    duration_min = db.Column(db.Integer, default=60)
    meet_link = db.Column(db.String(500))
    tg_group_id = db.Column(db.BigInteger)
    notes = db.Column(db.Text)
    
    student_rating = db.Column(db.Integer)  # 1-5
    student_review = db.Column(db.Text)
    points_awarded = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Points relationship
    points = db.relationship('MentorPoint', 
                            backref='session', 
                            cascade='all, delete-orphan',
                            foreign_keys='MentorPoint.session_id')


class MentorPoint(db.Model):
    __tablename__ = 'mentor_points'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    mentor_id = db.Column(db.String(36), db.ForeignKey('mentor_profiles.id', ondelete='CASCADE'), nullable=False)
    session_id = db.Column(db.String(36), db.ForeignKey('sessions.id'))
    points = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(20))  # session_completed, bonus, withdrawal, penalty, refund
    balance_after = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Withdrawal(db.Model):
    __tablename__ = 'withdrawals'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    mentor_id = db.Column(db.String(36), db.ForeignKey('mentor_profiles.id', ondelete='CASCADE'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    points_used = db.Column(db.Integer, nullable=False)
    card_last4 = db.Column(db.String(4))
    card_holder = db.Column(db.String(200))
    status = db.Column(db.String(20), default='pending')  # pending, approved, processing, paid, rejected
    admin_note = db.Column(db.Text)
    processed_by = db.Column(db.String(36), db.ForeignKey('users.id'))
    processed_at = db.Column(db.DateTime)
    transaction_ref = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship for processed_by
    processed_by_user = db.relationship('User', 
                                       foreign_keys=[processed_by],
                                       backref='processed_withdrawals')


class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    method = db.Column(db.String(20))  # payme, click, uzcard, humo, free
    status = db.Column(db.String(20), default='pending')  # pending, success, failed, refunded
    provider_tx = db.Column(db.String(200))
    meta = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class University(db.Model):
    __tablename__ = 'universities'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    short_name = db.Column(db.String(50), nullable=False, unique=True)
    full_name = db.Column(db.String(200), nullable=False)
    cover_url = db.Column(db.String(500))
    description = db.Column(db.Text)
    website = db.Column(db.String(200))
    telegram = db.Column(db.String(200))
    instagram = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    faculties = db.relationship('Faculty', 
                               backref='university', 
                               cascade='all, delete-orphan',
                               foreign_keys='Faculty.university_id')
    
    def to_dict(self):
        return {
            'id': self.id,
            'short_name': self.short_name,
            'full_name': self.full_name,
            'cover_url': self.cover_url,
            'description': self.description,
            'website': self.website,
            'telegram': self.telegram,
            'instagram': self.instagram,
            'sort_order': self.sort_order
        }


class Faculty(db.Model):
    __tablename__ = 'faculties'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    university_id = db.Column(db.String(36), db.ForeignKey('universities.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    cover_url = db.Column(db.String(500))
    description = db.Column(db.Text)
    quota = db.Column(db.Integer)
    employment_pct = db.Column(db.Integer)
    avg_salary_mln = db.Column(db.Numeric(4, 1))
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    stats = db.relationship('FacultyStat', 
                           backref='faculty', 
                           cascade='all, delete-orphan',
                           foreign_keys='FacultyStat.faculty_id')
    
    def to_dict(self):
        return {
            'id': self.id,
            'university_id': self.university_id,
            'name': self.name,
            'cover_url': self.cover_url,
            'description': self.description,
            'quota': self.quota,
            'employment_pct': self.employment_pct,
            'avg_salary_mln': float(self.avg_salary_mln) if self.avg_salary_mln else None,
            'sort_order': self.sort_order
        }


class FacultyStat(db.Model):
    __tablename__ = 'faculty_stats'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    faculty_id = db.Column(db.String(36), db.ForeignKey('faculties.id', ondelete='CASCADE'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    min_score = db.Column(db.Integer)
    max_score = db.Column(db.Integer)
    applicants = db.Column(db.Integer)
    quota = db.Column(db.Integer)
    
    __table_args__ = (db.UniqueConstraint('faculty_id', 'year', name='_faculty_year_uc'),)


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text)
    type = db.Column(db.String(20))  # session, payment, system, points, verification
    is_read = db.Column(db.Boolean, default=False)
    meta = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class OTPCode(db.Model):
    __tablename__ = 'otp_codes'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    identifier = db.Column(db.String(50), nullable=False)  # telefon raqam
    code = db.Column(db.String(6), nullable=False)
    source = db.Column(db.String(20), default='bot')  # bot, web
    is_sent = db.Column(db.Boolean, default=False)
    is_used = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @staticmethod
    def generate_code():
        return f"{random.randint(100000, 999999)}"
    
    __table_args__ = (
        db.Index('idx_otp_identifier', 'identifier', 'is_used'),
        db.Index('idx_otp_expires', 'expires_at'),
        db.Index('idx_otp_web_pending', 'source', 'is_sent', 'is_used', 'expires_at'),
    )

# models.py ga qo'shiladigan yangi model

class LoginSession(db.Model):
    """Foydalanuvchi login sessiyalarini kuzatish"""
    __tablename__ = 'login_sessions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    session_id = db.Column(db.String(100), unique=True)
    
    # Qurilma ma'lumotlari
    device_info = db.Column(db.Text)  # User agent, platform
    ip_address = db.Column(db.String(50))
    location = db.Column(db.String(100))  # Taxminiy lokatsiya (ixtiyoriy)
    
    # Login usuli
    login_method = db.Column(db.String(20))  # 'telegram_webapp', 'qr', 'deeplink', 'otp'
    
    # Vaqtlar
    logged_in_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    logged_out_at = db.Column(db.DateTime, nullable=True)
    
    # Aktivlik
    is_active = db.Column(db.Boolean, default=True)
    
    # Xabarnoma yuborilganmi?
    notification_sent = db.Column(db.Boolean, default=False)
    
    user = db.relationship('User', backref=db.backref('login_sessions', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'device_info': json.loads(self.device_info) if self.device_info else {},
            'ip_address': self.ip_address,
            'login_method': self.login_method,
            'logged_in_at': self.logged_in_at.isoformat() if self.logged_in_at else None,
            'last_active_at': self.last_active_at.isoformat() if self.last_active_at else None,
            'is_active': self.is_active
        }

# qoshimcha 

class AuthToken(db.Model):
    """Autentifikatsiya tokenlari (QR va DeepLink uchun)"""
    __tablename__ = 'auth_tokens'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    token = db.Column(db.String(100), unique=True, nullable=False, index=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    source = db.Column(db.String(20), default='deeplink')  # 'deeplink', 'qr'
    is_used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    
    def is_valid(self):
        return not self.is_used and self.expires_at > datetime.utcnow()
    
    def to_dict(self):
        return {
            'id': self.id,
            'token': self.token,
            'source': self.source,
            'is_used': self.is_used,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'used_at': self.used_at.isoformat() if self.used_at else None
        }


class News(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'created_at': self.created_at.isoformat()
        }

class Material(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(255), nullable=False)
    material_type = db.Column(db.String(50), nullable=False) # 'link' or 'file'
    url = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'type': self.material_type,
            'url': self.url,
            'created_at': self.created_at.isoformat()
        }