"""
admin_setup.py — Birinchi admin yaratish skripti.

Ishlatish:
  python admin_setup.py

Yoki interaktiv:
  python admin_setup.py --username admin --password MySecretPass123
"""

import sys
import os
import hashlib

# Loyiha papkasiga import path qo'shish
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, User


def create_admin(username, password, full_name='Admin', role='superadmin'):
    """Admin foydalanuvchi yaratish yoki yangilash"""
    with app.app_context():
        # Mavjud adminni tekshirish
        existing = User.query.filter(
            (User.username == username) | (User.role.in_(['admin', 'superadmin']))
        ).first()

        password_hash = hashlib.sha256(password.encode()).hexdigest()

        if existing:
            print(f"⚠  Admin mavjud: {existing.username} ({existing.role})")
            choice = input("Parolni yangilash? (y/n): ").strip().lower()
            if choice == 'y':
                # password_hash maydoni yo'q bo'lsa, qo'shish
                if not hasattr(existing, 'password_hash') or not hasattr(User, 'password_hash'):
                    print("❌ User modelida password_hash maydoni yo'q!")
                    print("   models.py ga quyidagini qo'shing:")
                    print("   password_hash = db.Column(db.String(64), nullable=True)")
                    return
                existing.password_hash = password_hash
                existing.is_active = True
                db.session.commit()
                print(f"✅ Parol yangilandi: {existing.username}")
            return existing

        # Yangi admin yaratish
        # password_hash maydoni borligini tekshirish
        if not hasattr(User, 'password_hash'):
            print("❌ User modelida password_hash maydoni yo'q!")
            print("\n   models.py ga quyidagini qo'shing (User klassida):")
            print("   password_hash = db.Column(db.String(64), nullable=True)")
            print("\n   Keyin: python admin_setup.py")
            
            # Hozircha .env yordamida ishlash
            print("\n⚡ VAQTINCHALIK YECHIM:")
            print(f"   .env fayliga qo'shing:")
            print(f"   ADMIN_PASSWORD={password}")
            print(f"\n   Va User yaratish uchun:")
            
            # password_hash siz yaratish
            user = User(
                username=username,
                full_name=full_name,
                role=role,
                is_active=True
            )
            db.session.add(user)
            db.session.commit()
            
            # .env ga yozish
            env_path = '.env'
            env_line = f"\nADMIN_PASSWORD={password}\n"
            with open(env_path, 'a') as f:
                f.write(env_line)
            
            print(f"✅ Admin yaratildi: {username} / {password}")
            print(f"✅ .env ga ADMIN_PASSWORD={password} yozildi")
            return user

        user = User(
            username=username,
            full_name=full_name,
            role=role,
            is_active=True,
            password_hash=password_hash
        )
        db.session.add(user)
        db.session.commit()

        print(f"✅ Admin yaratildi!")
        print(f"   Username: {username}")
        print(f"   Parol: {password}")
        print(f"   Rol: {role}")
        return user


def main():
    print("=" * 50)
    print("  ConnectU — Admin yaratish")
    print("=" * 50)

    if '--username' in sys.argv and '--password' in sys.argv:
        idx_u = sys.argv.index('--username')
        idx_p = sys.argv.index('--password')
        username = sys.argv[idx_u + 1]
        password = sys.argv[idx_p + 1]
        full_name = 'Admin'
        if '--name' in sys.argv:
            idx_n = sys.argv.index('--name')
            full_name = sys.argv[idx_n + 1]
    else:
        print("\nAdmin ma'lumotlarini kiriting:")
        username = input("Username (default: admin): ").strip() or 'admin'
        password = input("Parol (min 6 belgi): ").strip()
        if len(password) < 6:
            print("❌ Parol kamida 6 belgi bo'lishi kerak!")
            sys.exit(1)
        full_name = input("To'liq ism (default: Admin): ").strip() or 'Admin'

    create_admin(username, password, full_name)
    print("\n📌 Kirish sahifasi: /admin_login.html")
    print("=" * 50)


if __name__ == '__main__':
    main()