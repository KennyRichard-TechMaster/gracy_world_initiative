import os
import sqlite3
from datetime import datetime
from functools import wraps
from uuid import uuid4

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    abort,
)
from werkzeug.utils import secure_filename

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, 'database.db')
UPLOAD_ROOT = os.path.join(BASE_DIR, 'static', 'uploads')
EVENT_UPLOAD_DIR = os.path.join(UPLOAD_ROOT, 'events')
PROGRAM_UPLOAD_DIR = os.path.join(UPLOAD_ROOT, 'programs')

os.makedirs(EVENT_UPLOAD_DIR, exist_ok=True)
os.makedirs(PROGRAM_UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = 'replace-this-with-a-strong-secret-key'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

ADMIN_USERNAME = 'Kenny'
ADMIN_PASSWORD = '1234Richard'
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'mov', 'm4v'}


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS inquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            organization TEXT,
            inquiry_type TEXT,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        '''
    )

    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            summary TEXT,
            description TEXT,
            event_date TEXT,
            event_time TEXT,
            location TEXT,
            status TEXT DEFAULT 'Upcoming',
            category TEXT,
            featured INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        '''
    )

    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS event_media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            media_type TEXT NOT NULL,
            alt_text TEXT,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
        )
        '''
    )

    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS programs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            summary TEXT,
            description TEXT,
            icon_label TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        '''
    )

    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS site_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            site_name TEXT,
            tagline TEXT,
            whatsapp_url TEXT,
            instagram_url TEXT,
            contact_email TEXT,
            contact_phone TEXT,
            founder_name TEXT,
            founder_role TEXT,
            founder_bio TEXT,
            founder_quote TEXT
        )
        '''
    )

    cur.execute('SELECT id FROM site_settings WHERE id = 1')
    if cur.fetchone() is None:
        cur.execute(
            '''
            INSERT INTO site_settings (
                id, site_name, tagline, whatsapp_url, instagram_url, contact_email,
                contact_phone, founder_name, founder_role, founder_bio, founder_quote
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                1,
                'Kenny Education Initiative',
                'Advancing education, impact, and partnerships for children in Nigeria.',
                'https://wa.me/2340000000000',
                'https://instagram.com/',
                'hello@example.com',
                '+234 000 000 0000',
                'Kenny',
                'Founder & Vision Lead',
                'Kenny leads an education-focused initiative committed to helping children access books, support, and meaningful learning opportunities.',
                'Education is not a luxury. It is the doorway to possibility.',
            ),
        )

    cur.execute('SELECT COUNT(*) AS count FROM programs')
    if cur.fetchone()['count'] == 0:
        now = now_str()
        starter_programs = [
            (
                'Book Distribution',
                slugify('Book Distribution'),
                'Providing books and learning materials to children and schools that need them most.',
                'This program focuses on sourcing, packaging, and distributing high-value educational resources to underserved learners and school communities.',
                'Books',
                now,
                now,
            ),
            (
                'Learning Outreach',
                slugify('Learning Outreach'),
                'Community-led education visits, mentoring moments, and child-centered activation days.',
                'Learning Outreach is designed to bring education alive through school visits, engagement days, reading sessions, and encouragement-driven outreach.',
                'Outreach',
                now,
                now,
            ),
            (
                'Partnership Projects',
                slugify('Partnership Projects'),
                'Collaborating with brands, schools, and institutions in line with SDG 17.',
                'Partnership Projects make it possible to scale impact through sponsorships, collaborations, and strategic support from organizations.',
                'Partners',
                now,
                now,
            ),
        ]
        cur.executemany(
            '''
            INSERT INTO programs (title, slug, summary, description, icon_label, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            starter_programs,
        )

    conn.commit()
    conn.close()


@app.before_request
def ensure_db():
    init_db()


def now_str():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def allowed_file(filename, media_kind='image'):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    if media_kind == 'image':
        return ext in ALLOWED_IMAGE_EXTENSIONS
    if media_kind == 'video':
        return ext in ALLOWED_VIDEO_EXTENSIONS
    return False


def detect_media_type(filename):
    ext = filename.rsplit('.', 1)[1].lower()
    if ext in ALLOWED_IMAGE_EXTENSIONS:
        return 'image'
    if ext in ALLOWED_VIDEO_EXTENSIONS:
        return 'video'
    return None


def slugify(text):
    slug = ''.join(ch.lower() if ch.isalnum() else '-' for ch in text).strip('-')
    while '--' in slug:
        slug = slug.replace('--', '-')
    return slug or f'item-{uuid4().hex[:8]}'


def unique_slug(conn, base_slug, table, current_id=None):
    slug = base_slug
    counter = 2
    while True:
        if current_id is None:
            row = conn.execute(f'SELECT id FROM {table} WHERE slug = ?', (slug,)).fetchone()
        else:
            row = conn.execute(f'SELECT id FROM {table} WHERE slug = ? AND id != ?', (slug, current_id)).fetchone()
        if row is None:
            return slug
        slug = f'{base_slug}-{counter}'
        counter += 1


def fetch_settings():
    conn = get_db_connection()
    settings = conn.execute('SELECT * FROM site_settings WHERE id = 1').fetchone()
    conn.close()
    return settings


@app.context_processor
def inject_globals():
    return {'site_settings': fetch_settings(), 'current_year': datetime.now().year}


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Please log in first.', 'error')
            return redirect(url_for('admin_login'))
        return view_func(*args, **kwargs)

    return wrapper


@app.route('/')
def home():
    conn = get_db_connection()
    featured_events = conn.execute(
        '''
        SELECT e.*, (
            SELECT filename FROM event_media m WHERE m.event_id = e.id ORDER BY sort_order ASC, id ASC LIMIT 1
        ) AS cover_media,
        (
            SELECT media_type FROM event_media m WHERE m.event_id = e.id ORDER BY sort_order ASC, id ASC LIMIT 1
        ) AS cover_media_type
        FROM events e
        ORDER BY featured DESC, id DESC
        LIMIT 6
        '''
    ).fetchall()
    programs = conn.execute('SELECT * FROM programs ORDER BY id ASC').fetchall()
    recent_gallery = conn.execute(
        '''
        SELECT m.*, e.title AS event_title, e.slug AS event_slug
        FROM event_media m
        JOIN events e ON e.id = m.event_id
        ORDER BY m.created_at DESC, m.id DESC
        LIMIT 8
        '''
    ).fetchall()
    conn.close()
    return render_template('index.html', events=featured_events, programs=programs, recent_gallery=recent_gallery)


@app.route('/founder')
def founder_page():
    return render_template('founder.html')


@app.route('/programs')
def programs_page():
    conn = get_db_connection()
    programs = conn.execute('SELECT * FROM programs ORDER BY id ASC').fetchall()
    conn.close()
    return render_template('programs.html', programs=programs)


@app.route('/programs/<slug>')
def program_detail_page(slug):
    conn = get_db_connection()
    program = conn.execute('SELECT * FROM programs WHERE slug = ?', (slug,)).fetchone()
    if program is None:
        conn.close()
        abort(404)
    related_events = conn.execute(
        '''
        SELECT e.*, (
            SELECT filename FROM event_media m WHERE m.event_id = e.id ORDER BY sort_order ASC, id ASC LIMIT 1
        ) AS cover_media,
        (
            SELECT media_type FROM event_media m WHERE m.event_id = e.id ORDER BY sort_order ASC, id ASC LIMIT 1
        ) AS cover_media_type
        FROM events e
        WHERE category = ?
        ORDER BY id DESC
        LIMIT 6
        ''',
        (program['title'],),
    ).fetchall()
    conn.close()
    return render_template('program_detail.html', program=program, related_events=related_events)


@app.route('/events')
def events_page():
    conn = get_db_connection()
    events = conn.execute(
        '''
        SELECT e.*, (
            SELECT filename FROM event_media m WHERE m.event_id = e.id ORDER BY sort_order ASC, id ASC LIMIT 1
        ) AS cover_media,
        (
            SELECT media_type FROM event_media m WHERE m.event_id = e.id ORDER BY sort_order ASC, id ASC LIMIT 1
        ) AS cover_media_type
        FROM events e
        ORDER BY id DESC
        '''
    ).fetchall()
    conn.close()
    return render_template('events.html', events=events)


@app.route('/events/<slug>')
def event_detail_page(slug):
    conn = get_db_connection()
    event = conn.execute('SELECT * FROM events WHERE slug = ?', (slug,)).fetchone()
    if event is None:
        conn.close()
        abort(404)
    media = conn.execute(
        'SELECT * FROM event_media WHERE event_id = ? ORDER BY sort_order ASC, id ASC',
        (event['id'],),
    ).fetchall()
    related_events = conn.execute(
        '''
        SELECT e.*, (
            SELECT filename FROM event_media m WHERE m.event_id = e.id ORDER BY sort_order ASC, id ASC LIMIT 1
        ) AS cover_media,
        (
            SELECT media_type FROM event_media m WHERE m.event_id = e.id ORDER BY sort_order ASC, id ASC LIMIT 1
        ) AS cover_media_type
        FROM events e
        WHERE e.id != ?
        ORDER BY id DESC
        LIMIT 3
        ''',
        (event['id'],),
    ).fetchall()
    conn.close()
    return render_template('event_detail.html', event=event, media=media, related_events=related_events)


@app.route('/gallery')
def gallery_page():
    conn = get_db_connection()
    media = conn.execute(
        '''
        SELECT m.*, e.title AS event_title, e.slug AS event_slug
        FROM event_media m
        JOIN events e ON e.id = m.event_id
        ORDER BY m.created_at DESC, m.id DESC
        '''
    ).fetchall()
    conn.close()
    return render_template('gallery.html', media=media)


@app.route('/faq')
def faq_page():
    return render_template('faq.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact_page():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        organization = request.form.get('organization', '').strip()
        inquiry_type = request.form.get('inquiry_type', '').strip()
        message = request.form.get('message', '').strip()

        if not full_name or not email or not phone or not message:
            flash('Please complete the required fields.', 'error')
            return redirect(url_for('contact_page'))

        conn = get_db_connection()
        conn.execute(
            '''
            INSERT INTO inquiries (full_name, email, phone, organization, inquiry_type, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (full_name, email, phone, organization, inquiry_type, message, now_str()),
        )
        conn.commit()
        conn.close()
        flash('Your message has been received successfully.', 'success')
        return redirect(url_for('contact_page'))

    return render_template('contact.html')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session['admin_username'] = username
            flash('Welcome back, Kenny.', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Invalid admin login details.', 'error')
        return redirect(url_for('admin_login'))

    return render_template('admin/login.html')


@app.route('/admin/logout')
@login_required
def admin_logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('admin_login'))


@app.route('/admin')
@login_required
def admin_dashboard():
    conn = get_db_connection()
    total_events = conn.execute('SELECT COUNT(*) AS count FROM events').fetchone()['count']
    total_media = conn.execute('SELECT COUNT(*) AS count FROM event_media').fetchone()['count']
    total_inquiries = conn.execute('SELECT COUNT(*) AS count FROM inquiries').fetchone()['count']
    events = conn.execute(
        '''
        SELECT e.*, COUNT(m.id) AS media_count
        FROM events e
        LEFT JOIN event_media m ON m.event_id = e.id
        GROUP BY e.id
        ORDER BY e.id DESC
        LIMIT 8
        '''
    ).fetchall()
    inquiries = conn.execute('SELECT * FROM inquiries ORDER BY id DESC LIMIT 8').fetchall()
    conn.close()
    return render_template(
        'admin/dashboard.html',
        total_events=total_events,
        total_media=total_media,
        total_inquiries=total_inquiries,
        events=events,
        inquiries=inquiries,
    )


@app.route('/admin/events')
@login_required
def admin_events_page():
    conn = get_db_connection()
    events = conn.execute(
        '''
        SELECT e.*, COUNT(m.id) AS media_count
        FROM events e
        LEFT JOIN event_media m ON m.event_id = e.id
        GROUP BY e.id
        ORDER BY e.id DESC
        '''
    ).fetchall()
    conn.close()
    return render_template('admin/events.html', events=events)


@app.route('/admin/events/new', methods=['GET', 'POST'])
@login_required
def admin_create_event():
    conn = get_db_connection()
    programs = conn.execute('SELECT * FROM programs ORDER BY title ASC').fetchall()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        summary = request.form.get('summary', '').strip()
        description = request.form.get('description', '').strip()
        event_date = request.form.get('event_date', '').strip()
        event_time = request.form.get('event_time', '').strip()
        location = request.form.get('location', '').strip()
        status = request.form.get('status', 'Upcoming').strip()
        category = request.form.get('category', '').strip()
        featured = 1 if request.form.get('featured') == 'on' else 0

        if not title:
            conn.close()
            flash('Event title is required.', 'error')
            return redirect(url_for('admin_create_event'))

        slug = unique_slug(conn, slugify(title), 'events')
        now = now_str()
        cur = conn.cursor()
        cur.execute(
            '''
            INSERT INTO events (title, slug, summary, description, event_date, event_time, location, status, category, featured, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (title, slug, summary, description, event_date, event_time, location, status, category, featured, now, now),
        )
        event_id = cur.lastrowid

        uploaded_files = request.files.getlist('media_files')
        for index, media_file in enumerate(uploaded_files):
            if media_file and media_file.filename:
                original_name = secure_filename(media_file.filename)
                media_type = detect_media_type(original_name)
                if media_type is None:
                    continue
                unique_name = f'{uuid4().hex}_{original_name}'
                media_file.save(os.path.join(EVENT_UPLOAD_DIR, unique_name))
                conn.execute(
                    '''
                    INSERT INTO event_media (event_id, filename, media_type, alt_text, sort_order, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''',
                    (event_id, unique_name, media_type, title, index, now),
                )

        conn.commit()
        conn.close()
        flash('Event created successfully.', 'success')
        return redirect(url_for('admin_events_page'))

    conn.close()
    return render_template('admin/event_form.html', event=None, programs=programs, form_action=url_for('admin_create_event'))


@app.route('/admin/events/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_event(event_id):
    conn = get_db_connection()
    event = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    if event is None:
        conn.close()
        abort(404)
    programs = conn.execute('SELECT * FROM programs ORDER BY title ASC').fetchall()
    existing_media = conn.execute('SELECT * FROM event_media WHERE event_id = ? ORDER BY sort_order ASC, id ASC', (event_id,)).fetchall()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        summary = request.form.get('summary', '').strip()
        description = request.form.get('description', '').strip()
        event_date = request.form.get('event_date', '').strip()
        event_time = request.form.get('event_time', '').strip()
        location = request.form.get('location', '').strip()
        status = request.form.get('status', 'Upcoming').strip()
        category = request.form.get('category', '').strip()
        featured = 1 if request.form.get('featured') == 'on' else 0

        if not title:
            conn.close()
            flash('Event title is required.', 'error')
            return redirect(url_for('admin_edit_event', event_id=event_id))

        slug = unique_slug(conn, slugify(title), 'events', current_id=event_id)
        now = now_str()
        conn.execute(
            '''
            UPDATE events
            SET title = ?, slug = ?, summary = ?, description = ?, event_date = ?, event_time = ?,
                location = ?, status = ?, category = ?, featured = ?, updated_at = ?
            WHERE id = ?
            ''',
            (title, slug, summary, description, event_date, event_time, location, status, category, featured, now, event_id),
        )

        uploaded_files = request.files.getlist('media_files')
        current_media_count = len(existing_media)
        for offset, media_file in enumerate(uploaded_files):
            if media_file and media_file.filename:
                original_name = secure_filename(media_file.filename)
                media_type = detect_media_type(original_name)
                if media_type is None:
                    continue
                unique_name = f'{uuid4().hex}_{original_name}'
                media_file.save(os.path.join(EVENT_UPLOAD_DIR, unique_name))
                conn.execute(
                    '''
                    INSERT INTO event_media (event_id, filename, media_type, alt_text, sort_order, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''',
                    (event_id, unique_name, media_type, title, current_media_count + offset, now),
                )

        conn.commit()
        conn.close()
        flash('Event updated successfully.', 'success')
        return redirect(url_for('admin_events_page'))

    conn.close()
    return render_template(
        'admin/event_form.html',
        event=event,
        programs=programs,
        existing_media=existing_media,
        form_action=url_for('admin_edit_event', event_id=event_id),
    )


@app.route('/admin/events/<int:event_id>/delete', methods=['POST'])
@login_required
def admin_delete_event(event_id):
    conn = get_db_connection()
    media_rows = conn.execute('SELECT * FROM event_media WHERE event_id = ?', (event_id,)).fetchall()
    for media in media_rows:
        file_path = os.path.join(EVENT_UPLOAD_DIR, media['filename'])
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
    conn.execute('DELETE FROM event_media WHERE event_id = ?', (event_id,))
    conn.execute('DELETE FROM events WHERE id = ?', (event_id,))
    conn.commit()
    conn.close()
    flash('Event deleted successfully.', 'success')
    return redirect(url_for('admin_events_page'))


@app.route('/admin/media/<int:media_id>/delete', methods=['POST'])
@login_required
def admin_delete_media(media_id):
    conn = get_db_connection()
    media = conn.execute('SELECT * FROM event_media WHERE id = ?', (media_id,)).fetchone()
    if media:
        file_path = os.path.join(EVENT_UPLOAD_DIR, media['filename'])
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        conn.execute('DELETE FROM event_media WHERE id = ?', (media_id,))
        conn.commit()
        flash('Media deleted successfully.', 'success')
    conn.close()
    return redirect(request.referrer or url_for('admin_events_page'))


@app.route('/admin/messages')
@login_required
def admin_messages_page():
    conn = get_db_connection()
    inquiries = conn.execute('SELECT * FROM inquiries ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('admin/messages.html', inquiries=inquiries)


@app.route('/admin/messages/<int:message_id>/delete', methods=['POST'])
@login_required
def admin_delete_message(message_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM inquiries WHERE id = ?', (message_id,))
    conn.commit()
    conn.close()
    flash('Inquiry deleted successfully.', 'success')
    return redirect(url_for('admin_messages_page'))


@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings_page():
    conn = get_db_connection()
    settings = conn.execute('SELECT * FROM site_settings WHERE id = 1').fetchone()

    if request.method == 'POST':
        payload = (
            request.form.get('site_name', '').strip(),
            request.form.get('tagline', '').strip(),
            request.form.get('whatsapp_url', '').strip(),
            request.form.get('instagram_url', '').strip(),
            request.form.get('contact_email', '').strip(),
            request.form.get('contact_phone', '').strip(),
            request.form.get('founder_name', '').strip(),
            request.form.get('founder_role', '').strip(),
            request.form.get('founder_bio', '').strip(),
            request.form.get('founder_quote', '').strip(),
        )
        conn.execute(
            '''
            UPDATE site_settings
            SET site_name = ?, tagline = ?, whatsapp_url = ?, instagram_url = ?, contact_email = ?,
                contact_phone = ?, founder_name = ?, founder_role = ?, founder_bio = ?, founder_quote = ?
            WHERE id = 1
            ''',
            payload,
        )
        conn.commit()
        conn.close()
        flash('Site settings updated successfully.', 'success')
        return redirect(url_for('admin_settings_page'))

    conn.close()
    return render_template('admin/settings.html', settings=settings)


@app.errorhandler(404)
def not_found(_error):
    return render_template('404.html'), 404


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
