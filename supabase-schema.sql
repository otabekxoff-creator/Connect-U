-- ═══════════════════════════════════════════════════════════
--  ConnectU — Supabase Database Schema
--  Versiya: 1.0
--  Bot, MiniApp, Mentor Panel, Admin Panel — hammasi shu DB
-- ═══════════════════════════════════════════════════════════

-- UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─────────────────────────────────────────────
-- 1. USERS (abituriyentlar va mentorlar)
-- ─────────────────────────────────────────────
CREATE TABLE users (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  telegram_id   BIGINT UNIQUE,
  phone         TEXT UNIQUE,
  full_name     TEXT NOT NULL,
  username      TEXT,
  avatar_url    TEXT,
  role          TEXT NOT NULL DEFAULT 'student'
                  CHECK (role IN ('student','mentor','admin','superadmin')),
  is_active     BOOLEAN DEFAULT true,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- 2. MENTOR PROFILES (mentorlar uchun qo'shimcha)
-- ─────────────────────────────────────────────
CREATE TABLE mentor_profiles (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id         UUID UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  university      TEXT,
  faculty         TEXT,
  year            INTEGER,
  bio             TEXT,
  student_id_url  TEXT,       -- talaba guvohnomasi (Supabase Storage)
  gpa             NUMERIC(3,2),
  is_verified     BOOLEAN DEFAULT false,
  verified_at     TIMESTAMPTZ,
  verified_by     UUID REFERENCES users(id),
  rating          NUMERIC(3,2) DEFAULT 5.00,
  total_sessions  INTEGER DEFAULT 0,
  total_reviews   INTEGER DEFAULT 0,

  -- Karta/to'lov ma'lumotlari (shifrlangan saqlanadi)
  card_number     TEXT,       -- faqat oxirgi 4 raqam ko'rsatiladi
  card_holder     TEXT,
  card_token      TEXT,       -- Payme/Click token (to'liq)

  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- 3. MENTOR CERTIFICATES
-- ─────────────────────────────────────────────
CREATE TABLE mentor_certificates (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  mentor_id   UUID REFERENCES mentor_profiles(id) ON DELETE CASCADE,
  title       TEXT NOT NULL,
  issuer      TEXT,
  issued_date DATE,
  file_url    TEXT,           -- Supabase Storage URL
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- 4. MENTOR CV / DOCUMENTS
-- ─────────────────────────────────────────────
CREATE TABLE mentor_documents (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  mentor_id   UUID REFERENCES mentor_profiles(id) ON DELETE CASCADE,
  doc_type    TEXT CHECK (doc_type IN ('cv','portfolio','transcript','other')),
  title       TEXT,
  file_url    TEXT NOT NULL,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- 5. SUBSCRIPTIONS (abituriyent tarif sotib oladi)
-- ─────────────────────────────────────────────
CREATE TABLE subscriptions (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  student_id    UUID REFERENCES users(id) ON DELETE CASCADE,
  tier          TEXT NOT NULL CHECK (tier IN ('free','group','basic','elite')),
  status        TEXT DEFAULT 'active' CHECK (status IN ('active','expired','cancelled')),
  price         INTEGER NOT NULL,        -- so'm
  started_at    TIMESTAMPTZ DEFAULT NOW(),
  expires_at    TIMESTAMPTZ,
  payment_id    UUID,                   -- payments.id ga bog'liq
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- 6. SESSIONS (mentor bilan sessiya)
-- ─────────────────────────────────────────────
CREATE TABLE sessions (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  student_id      UUID REFERENCES users(id),
  mentor_id       UUID REFERENCES mentor_profiles(id),
  subscription_id UUID REFERENCES subscriptions(id),
  session_type    TEXT CHECK (session_type IN ('group','individual','video')),
  status          TEXT DEFAULT 'pending'
                    CHECK (status IN ('pending','confirmed','completed','cancelled','no_show')),
  scheduled_at    TIMESTAMPTZ,
  duration_min    INTEGER DEFAULT 60,
  meet_link       TEXT,
  tg_group_id     BIGINT,             -- Telegram guruh chat ID
  notes           TEXT,               -- mentor izohi
  student_rating  INTEGER CHECK (student_rating BETWEEN 1 AND 5),
  student_review  TEXT,
  points_awarded  INTEGER DEFAULT 0,  -- mentorga berilgan ball
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- 7. MENTOR POINTS (bal/earning tizimi)
-- ─────────────────────────────────────────────
CREATE TABLE mentor_points (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  mentor_id   UUID REFERENCES mentor_profiles(id) ON DELETE CASCADE,
  session_id  UUID REFERENCES sessions(id),
  points      INTEGER NOT NULL,       -- musbat = qo'shildi, manfiy = yechildi
  reason      TEXT,                   -- 'session_completed', 'bonus', 'withdrawal', 'penalty'
  balance_after INTEGER NOT NULL,     -- balans shu tranzaksiyadan keyin
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Mentor joriy balansini tezda olish uchun (denormalized)
ALTER TABLE mentor_profiles ADD COLUMN balance INTEGER DEFAULT 0;

-- ─────────────────────────────────────────────
-- 8. WITHDRAWALS (pul chiqarish so'rovlari)
-- ─────────────────────────────────────────────
CREATE TABLE withdrawals (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  mentor_id     UUID REFERENCES mentor_profiles(id) ON DELETE CASCADE,
  amount        INTEGER NOT NULL,         -- so'm
  points_used   INTEGER NOT NULL,
  card_last4    TEXT,
  card_holder   TEXT,
  status        TEXT DEFAULT 'pending'
                  CHECK (status IN ('pending','approved','processing','paid','rejected')),
  admin_note    TEXT,
  processed_by  UUID REFERENCES users(id),
  processed_at  TIMESTAMPTZ,
  transaction_ref TEXT,                  -- Payme/Click tranzaksiya ID
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- 9. PAYMENTS (barcha to'lovlar)
-- ─────────────────────────────────────────────
CREATE TABLE payments (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id       UUID REFERENCES users(id),
  amount        INTEGER NOT NULL,
  method        TEXT CHECK (method IN ('payme','click','uzcard','humo','free')),
  status        TEXT DEFAULT 'pending'
                  CHECK (status IN ('pending','success','failed','refunded')),
  provider_tx   TEXT,                    -- Payme/Click tranzaksiya ID
  meta          JSONB,                   -- qo'shimcha ma'lumot
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- 10. UNIVERSITIES (admin boshqaradi)
-- ─────────────────────────────────────────────
CREATE TABLE universities (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  short_name    TEXT NOT NULL,
  full_name     TEXT NOT NULL,
  cover_url     TEXT,
  description   TEXT,
  website       TEXT,
  telegram      TEXT,
  instagram     TEXT,
  is_active     BOOLEAN DEFAULT true,
  sort_order    INTEGER DEFAULT 0,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- 11. FACULTIES
-- ─────────────────────────────────────────────
CREATE TABLE faculties (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  university_id   UUID REFERENCES universities(id) ON DELETE CASCADE,
  name            TEXT NOT NULL,
  cover_url       TEXT,
  description     TEXT,
  quota           INTEGER,
  employment_pct  INTEGER,
  avg_salary_mln  NUMERIC(4,1),
  sort_order      INTEGER DEFAULT 0,
  is_active       BOOLEAN DEFAULT true,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- 12. FACULTY STATS (yillik statistika)
-- ─────────────────────────────────────────────
CREATE TABLE faculty_stats (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  faculty_id    UUID REFERENCES faculties(id) ON DELETE CASCADE,
  year          INTEGER NOT NULL,
  min_score     INTEGER,
  max_score     INTEGER,
  applicants    INTEGER,
  quota         INTEGER,
  UNIQUE(faculty_id, year)
);

-- ─────────────────────────────────────────────
-- 13. NOTIFICATIONS
-- ─────────────────────────────────────────────
CREATE TABLE notifications (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
  title       TEXT NOT NULL,
  body        TEXT,
  type        TEXT,   -- 'session','payment','system','points'
  is_read     BOOLEAN DEFAULT false,
  meta        JSONB,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- 14. OTP CODES (Telegram OTP)
-- ─────────────────────────────────────────────
CREATE TABLE otp_codes (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  identifier  TEXT NOT NULL,   -- telefon yoki email
  code        TEXT NOT NULL,
  expires_at  TIMESTAMPTZ NOT NULL,
  is_used     BOOLEAN DEFAULT false,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- VIEWS (tez query uchun)
-- ─────────────────────────────────────────────

-- Mentor to'liq profil view
CREATE VIEW mentor_full AS
  SELECT
    u.id, u.telegram_id, u.phone, u.full_name, u.username, u.avatar_url,
    mp.university, mp.faculty, mp.year, mp.bio,
    mp.is_verified, mp.rating, mp.total_sessions, mp.total_reviews,
    mp.balance, mp.card_last4, mp.card_holder,
    mp.student_id_url, mp.gpa,
    mp.id AS mentor_profile_id
  FROM users u
  JOIN mentor_profiles mp ON mp.user_id = u.id
  WHERE u.role = 'mentor';

-- Mentor oylik daromad summary
CREATE VIEW mentor_monthly_earnings AS
  SELECT
    mp.id AS mentor_id,
    u.full_name,
    DATE_TRUNC('month', s.created_at) AS month,
    COUNT(s.id) AS sessions_count,
    SUM(s.points_awarded) AS points_earned
  FROM mentor_profiles mp
  JOIN users u ON u.id = mp.user_id
  LEFT JOIN sessions s ON s.mentor_id = mp.id AND s.status = 'completed'
  GROUP BY mp.id, u.full_name, DATE_TRUNC('month', s.created_at);

-- ─────────────────────────────────────────────
-- FUNCTIONS & TRIGGERS
-- ─────────────────────────────────────────────

-- Sessiya tugaganda mentorga avtomatik ball berish
CREATE OR REPLACE FUNCTION award_points_on_session()
RETURNS TRIGGER AS $$
DECLARE
  pts INTEGER;
  new_balance INTEGER;
  tier_val TEXT;
BEGIN
  -- Faqat 'completed' ga o'tganda ishlaydi
  IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
    -- Tarif bo'yicha ball hisoblash
    SELECT s.tier INTO tier_val
    FROM subscriptions s
    WHERE s.id = NEW.subscription_id;

    pts := CASE tier_val
      WHEN 'group'   THEN 2000   -- 2,000 so'm ekvivalent
      WHEN 'basic'   THEN 8000   -- 8,000 so'm ekvivalent
      WHEN 'elite'   THEN 18000  -- 18,000 so'm ekvivalent
      ELSE 0
    END;

    -- Mentorga ball qo'shish
    UPDATE mentor_profiles
    SET balance = balance + pts,
        total_sessions = total_sessions + 1
    WHERE id = NEW.mentor_id
    RETURNING balance INTO new_balance;

    -- Ball tarixi
    INSERT INTO mentor_points (mentor_id, session_id, points, reason, balance_after)
    VALUES (NEW.mentor_id, NEW.id, pts, 'session_completed', new_balance);

    -- Sessiya yozuvini yangilash
    NEW.points_awarded := pts;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_award_points
  BEFORE UPDATE ON sessions
  FOR EACH ROW EXECUTE FUNCTION award_points_on_session();

-- Withdraw tasdiqlanganda balansdan yechish
CREATE OR REPLACE FUNCTION process_withdrawal()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.status = 'approved' AND OLD.status = 'pending' THEN
    UPDATE mentor_profiles
    SET balance = balance - NEW.points_used
    WHERE id = NEW.mentor_id;

    INSERT INTO mentor_points (mentor_id, points, reason, balance_after)
    SELECT NEW.mentor_id, -NEW.points_used, 'withdrawal',
           balance FROM mentor_profiles WHERE id = NEW.mentor_id;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_process_withdrawal
  BEFORE UPDATE ON withdrawals
  FOR EACH ROW EXECUTE FUNCTION process_withdrawal();

-- updated_at avtomatik
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated        BEFORE UPDATE ON users         FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_mentor_updated       BEFORE UPDATE ON mentor_profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_sessions_updated     BEFORE UPDATE ON sessions       FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_unis_updated         BEFORE UPDATE ON universities   FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_faculties_updated    BEFORE UPDATE ON faculties      FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ─────────────────────────────────────────────
-- ROW LEVEL SECURITY (RLS)
-- ─────────────────────────────────────────────

ALTER TABLE users               ENABLE ROW LEVEL SECURITY;
ALTER TABLE mentor_profiles     ENABLE ROW LEVEL SECURITY;
ALTER TABLE mentor_certificates ENABLE ROW LEVEL SECURITY;
ALTER TABLE mentor_documents    ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions            ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions       ENABLE ROW LEVEL SECURITY;
ALTER TABLE mentor_points       ENABLE ROW LEVEL SECURITY;
ALTER TABLE withdrawals         ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications       ENABLE ROW LEVEL SECURITY;

-- Foydalanuvchi faqat o'z ma'lumotlarini ko'radi
CREATE POLICY "Users see own data"     ON users           FOR ALL USING (auth.uid()::text = id::text);
CREATE POLICY "Mentor sees own profile" ON mentor_profiles FOR ALL USING (auth.uid()::text = user_id::text);
CREATE POLICY "Mentor sees own certs"  ON mentor_certificates FOR ALL USING (
  mentor_id IN (SELECT id FROM mentor_profiles WHERE user_id::text = auth.uid()::text)
);
CREATE POLICY "Mentor sees own docs"   ON mentor_documents FOR ALL USING (
  mentor_id IN (SELECT id FROM mentor_profiles WHERE user_id::text = auth.uid()::text)
);
CREATE POLICY "See own sessions"       ON sessions         FOR ALL USING (
  student_id::text = auth.uid()::text OR
  mentor_id IN (SELECT id FROM mentor_profiles WHERE user_id::text = auth.uid()::text)
);
CREATE POLICY "See own subscriptions"  ON subscriptions    FOR ALL USING (student_id::text = auth.uid()::text);
CREATE POLICY "See own points"         ON mentor_points    FOR ALL USING (
  mentor_id IN (SELECT id FROM mentor_profiles WHERE user_id::text = auth.uid()::text)
);
CREATE POLICY "See own withdrawals"    ON withdrawals      FOR ALL USING (
  mentor_id IN (SELECT id FROM mentor_profiles WHERE user_id::text = auth.uid()::text)
);
CREATE POLICY "See own notifications"  ON notifications    FOR ALL USING (user_id::text = auth.uid()::text);

-- Hamma universities va faculties ni ko'ra oladi (public)
CREATE POLICY "Public read universities" ON universities   FOR SELECT USING (is_active = true);
CREATE POLICY "Public read faculties"    ON faculties      FOR SELECT USING (is_active = true);
CREATE POLICY "Public read faculty_stats" ON faculty_stats FOR SELECT USING (true);
CREATE POLICY "Public read mentor_certs" ON mentor_certificates FOR SELECT USING (true);
CREATE POLICY "Public read mentor_docs"  ON mentor_documents FOR SELECT USING (doc_type IN ('cv','portfolio'));

-- ─────────────────────────────────────────────
-- DEMO DATA
-- ─────────────────────────────────────────────

-- Universitetlar
INSERT INTO universities (short_name, full_name, cover_url, description, website, telegram, instagram, sort_order) VALUES
('TDYU',    'Toshkent Davlat Yuridik Universiteti',            'https://images.unsplash.com/photo-1562774053-701939374585?w=800&q=80', 'O''zbekistondagi yetakchi huquq universiteti.', 'https://tsul.uz',    'https://t.me/tdyu_official',  'https://instagram.com/tsul.uz',     1),
('ODI',     'O''zbekiston Diplomatiya Instituti',               'https://images.unsplash.com/photo-1568992688065-536aad8a12f6?w=800&q=80', 'Markaziy Osiyodagi yagona diplomatik OTM.',   'https://odi.uz',     'https://t.me/odi_uz',         'https://instagram.com/odi_official',2),
('TATU',    'Toshkent Axborot Texnologiyalari Universiteti',   'https://images.unsplash.com/photo-1518770660439-4636190af475?w=800&q=80', 'O''zbekistondagi IT ta''limining yetakchisi.', 'https://tuit.uz',    'https://t.me/tuit_uz',        'https://instagram.com/tuit_official',3),
('UDJTAU',  'O''zbekiston Davlat Jahon Tillari Universiteti',  'https://images.unsplash.com/photo-1523050854058-8df90110c9f1?w=800&q=80', '15+ xorijiy til yo''nalishi.',                'https://uzswlu.uz',  'https://t.me/uzswlu',         'https://instagram.com/uzswlu',      4),
('TDTU',    'Toshkent Davlat Texnika Universiteti',            'https://images.unsplash.com/photo-1496307653780-42ee777d4833?w=800&q=80', 'O''zbekistondagi eng yirik texnika universiteti.','https://tdtu.uz','https://t.me/tdtu_official',  'https://instagram.com/tdtu_uz',     5);