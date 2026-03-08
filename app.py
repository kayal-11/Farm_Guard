from flask import Flask, request, jsonify, redirect, url_for, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
#from dotenv import load_dotenv
from flask_cors import CORS
import os

#load_dotenv()
app = Flask(__name__, static_folder='.', static_url_path='')
app.config['SECRET_KEY'] = 'your-secret-key-here-change-this'
# Adjust this to your actual DB credentials if needed
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg://postgres:kayaladmin1109@localhost:5432/farmguard'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app, supports_credentials=True)
db = SQLAlchemy(app)

# ========================
# DATABASE MODELS
# ========================

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # farmer, vet, authority
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    amu_entries = db.relationship('AMUEntry', backref='farmer', lazy=True, foreign_keys='AMUEntry.farmer_id')
    audit_logs = db.relationship('AuditLog', backref='user', lazy=True)
    alerts = db.relationship('Alert', backref='user', lazy=True)


class Animal(db.Model):
    __tablename__ = 'animals'
    id = db.Column(db.Integer, primary_key=True)
    tag_number = db.Column(db.String(50), unique=True, nullable=False)
    species = db.Column(db.String(50), nullable=False)
    farmer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    amu_entries = db.relationship('AMUEntry', backref='animal', lazy=True)


class Drug(db.Model):
    __tablename__ = 'drugs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    withdrawal_period_days = db.Column(db.Integer, nullable=False)
    max_dosage = db.Column(db.Float)
    unit = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    entries = db.relationship('AMUEntry', backref='drug', lazy=True)


class AMUEntry(db.Model):
    __tablename__ = 'amu_entries'
    id = db.Column(db.Integer, primary_key=True)
    entry_id = db.Column(db.String(50), unique=True, nullable=False)
    farmer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    animal_id = db.Column(db.Integer, db.ForeignKey('animals.id'), nullable=False)
    drug_id = db.Column(db.Integer, db.ForeignKey('drugs.id'), nullable=False)
    dosage = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    treatment_date = db.Column(db.Date, nullable=False)
    withdrawal_end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    vet_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    vet_notes = db.Column(db.Text)
    reviewed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    vet = db.relationship('User', foreign_keys=[vet_id])


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    log_id = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    related_entry_id = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class Alert(db.Model):
    __tablename__ = 'alerts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    alert_type = db.Column(db.String(50), nullable=False)  # withdrawal, compliance, notification
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='normal')  # urgent, high, medium, normal
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ========================
# ROUTES (HTML PAGES)
# ========================

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        identifier = data.get('identifier')
        password = data.get('password')
        role = data.get('role')

        user = User.query.filter_by(identifier=identifier, role=role).first()

        if not user:
            return jsonify({
                'success': False,
                'message': f'User with identifier "{identifier}" and role "{role}" not found. Available test users: FARM001, VET001, AUTH001'
            }), 401

        if not check_password_hash(user.password_hash, password):
            return jsonify({'success': False, 'message': 'Invalid password. Default password is: password123'}), 401

        session['user_id'] = user.id
        session['role'] = user.role
        session['name'] = user.name

        log = AuditLog(
            log_id=f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            user_id=user.id,
            action='login',
            description=f"{user.name} logged in as {user.role}"
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({'success': True, 'role': user.role})

    return send_from_directory('.', 'login.html')


@app.route('/logout')
def logout():
    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id)

        log = AuditLog(
            log_id=f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            user_id=user_id,
            action='logout',
            description=f"{user.name} logged out"
        )
        db.session.add(log)
        db.session.commit()

    session.clear()
    return redirect(url_for('index'))


@app.route('/farmer-dashboard')
def farmer_dashboard():
    if 'user_id' not in session or session['role'] != 'farmer':
        return redirect(url_for('login'))
    return send_from_directory('.', 'farmer-dashboard.html')


@app.route('/vet-dashboard')
def vet_dashboard():
    if 'user_id' not in session or session['role'] != 'vet':
        return redirect(url_for('login'))
    return send_from_directory('.', 'vet-dashboard.html')


@app.route('/authority-dashboard')
def authority_dashboard():
    if 'user_id' not in session or session['role'] != 'authority':
        return redirect(url_for('login'))
    return send_from_directory('.', 'authority-dashboard.html')


@app.route('/analytics')
def analytics():
    return send_from_directory('.', 'analytics.html')


@app.route('/audit-log')
def audit_log():
    return send_from_directory('.', 'audit-log.html')


@app.route('/alerts')
def alerts():
    return send_from_directory('.', 'alerts.html')


# ========================
# API ENDPOINTS
# ========================

@app.route('/api/amu-entries', methods=['GET', 'POST'])
def amu_entries_api():
    if request.method == 'GET':
        entries = AMUEntry.query.all()
        return jsonify([{
            'id': e.id,
            'entry_id': e.entry_id,
            'animal_tag': e.animal.tag_number if e.animal else 'N/A',
            'drug_name': e.drug.name if e.drug else 'N/A',
            'dosage': e.dosage,
            'status': e.status,
            'created_at': e.created_at.isoformat() if e.created_at else None
        } for e in entries])

    # POST
    if 'user_id' not in session or session['role'] != 'farmer':
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    entry_id = f"AMU-{datetime.now().strftime('%Y-%m%d%H%M%S')}"

    drug = Drug.query.get(data['drug_id'])
    if not drug:
        return jsonify({'error': 'Drug not found'}), 404

    animal = Animal.query.get(data['animal_id'])
    if not animal:
        return jsonify({'error': 'Animal not found'}), 404
    if animal.farmer_id != session['user_id']:
        return jsonify({'error': 'Animal does not belong to you'}), 403

    treatment_date = datetime.strptime(data['treatment_date'], '%Y-%m-%d').date()
    withdrawal_end = treatment_date + timedelta(days=drug.withdrawal_period_days)

    entry = AMUEntry(
        entry_id=entry_id,
        farmer_id=session['user_id'],
        animal_id=data['animal_id'],
        drug_id=data['drug_id'],
        dosage=data['dosage'],
        unit=data['unit'],
        treatment_date=treatment_date,
        withdrawal_end_date=withdrawal_end,
        status='pending'
    )

    db.session.add(entry)

    log = AuditLog(
        log_id=f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        user_id=session['user_id'],
        action='create',
        description=f"Created AMU entry {entry_id}",
        related_entry_id=entry_id
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({'success': True, 'entry_id': entry_id})


@app.route('/api/amu-entries/<int:entry_id>/review', methods=['POST'])
def review_entry(entry_id):
    if 'user_id' not in session or session['role'] != 'vet':
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    entry = AMUEntry.query.get(entry_id)

    if not entry:
        return jsonify({'error': 'Entry not found'}), 404

    if entry.status != 'pending':
        return jsonify({'error': 'Entry has already been reviewed'}), 400

    entry.status = data['status']
    entry.vet_id = session['user_id']
    entry.vet_notes = data.get('notes', '')
    entry.reviewed_at = datetime.utcnow()

    log = AuditLog(
        log_id=f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        user_id=session['user_id'],
        action=data['status'],
        description=f"{data['status'].capitalize()} AMU entry {entry.entry_id} for farmer {entry.farmer.name}",
        related_entry_id=entry.entry_id
    )
    db.session.add(log)

    alert = Alert(
        user_id=entry.farmer_id,
        alert_type='notification',
        title=f"Entry {data['status'].capitalize()}",
        message=f"Your AMU entry {entry.entry_id} has been {data['status']} by {User.query.get(session['user_id']).name}",
        priority='high' if data['status'] == 'rejected' else 'normal'
    )
    db.session.add(alert)
    db.session.commit()

    return jsonify({'success': True, 'message': f'Entry {data["status"]} successfully'})


@app.route('/api/stats')
def get_stats():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    if session['role'] == 'farmer':
        total = AMUEntry.query.filter_by(farmer_id=session['user_id']).count()
        pending = AMUEntry.query.filter_by(farmer_id=session['user_id'], status='pending').count()
        approved = AMUEntry.query.filter_by(farmer_id=session['user_id'], status='approved').count()

        return jsonify({
            'total_entries': total,
            'pending': pending,
            'compliance_rate': (approved / total * 100) if total > 0 else 0
        })

    if session['role'] == 'authority':
        total = AMUEntry.query.count()
        approved = AMUEntry.query.filter_by(status='approved').count()
        farms = User.query.filter_by(role='farmer').count()

        return jsonify({
            'total_entries': total,
            'compliance_rate': (approved / total * 100) if total > 0 else 0,
            'total_farms': farms
        })


@app.route('/api/check-session')
def check_session():
    if 'user_id' not in session:
        return jsonify({'authenticated': False}), 401

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'authenticated': False}), 401

    return jsonify({
        'authenticated': True,
        'user': {
            'id': user.id,
            'name': user.name,
            'role': user.role
        }
    })


@app.route('/api/user')
def get_user():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'id': user.id,
        'name': user.name,
        'role': user.role,
        'identifier': user.identifier,
        'email': user.email,
        'phone': user.phone
    })


@app.route('/api/farmer/dashboard')
def farmer_dashboard_api():
    if 'user_id' not in session or session['role'] != 'farmer':
        return jsonify({'error': 'Unauthorized'}), 401

    user = User.query.get(session['user_id'])
    entries = AMUEntry.query.filter_by(farmer_id=user.id).order_by(AMUEntry.created_at.desc()).limit(10).all()

    total_entries = AMUEntry.query.filter_by(farmer_id=user.id).count()
    pending_entries = AMUEntry.query.filter_by(farmer_id=user.id, status='pending').count()
    active_withdrawals = AMUEntry.query.filter(
        AMUEntry.farmer_id == user.id,
        AMUEntry.withdrawal_end_date >= datetime.now().date(),
        AMUEntry.status == 'approved'
    ).count()

    approved = AMUEntry.query.filter_by(farmer_id=user.id, status='approved').count()
    compliance_rate = (approved / total_entries * 100) if total_entries > 0 else 0

    return jsonify({
        'user': {
            'name': user.name,
            'role': user.role
        },
        'stats': {
            'total_entries': total_entries,
            'pending': pending_entries,
            'active_withdrawals': active_withdrawals,
            'compliance_rate': round(compliance_rate, 1)
        },
        'entries': [{
            'id': e.id,
            'entry_id': e.entry_id,
            'animal_tag': e.animal.tag_number if e.animal else 'N/A',
            'drug_name': e.drug.name if e.drug else 'N/A',
            'dosage': e.dosage,
            'unit': e.unit,
            'status': e.status,
            'treatment_date': e.treatment_date.isoformat() if e.treatment_date else None,
            'withdrawal_end_date': e.withdrawal_end_date.isoformat() if e.withdrawal_end_date else None,
            'created_at': e.created_at.isoformat() if e.created_at else None
        } for e in entries]
    })


@app.route('/api/vet/dashboard')
def vet_dashboard_api():
    if 'user_id' not in session or session['role'] != 'vet':
        return jsonify({'error': 'Unauthorized'}), 401

    user = User.query.get(session['user_id'])
    pending_entries = AMUEntry.query.filter_by(status='pending').order_by(AMUEntry.created_at.desc()).all()

    pending_count = len(pending_entries)
    approved_today = AMUEntry.query.filter_by(
        vet_id=user.id,
        status='approved'
    ).filter(
        db.func.date(AMUEntry.reviewed_at) == datetime.now().date()
    ).count()

    new_entries_this_week = AMUEntry.query.filter(
        AMUEntry.created_at >= datetime.now() - timedelta(days=7)
    ).count()

    return jsonify({
        'user': {
            'name': user.name,
            'role': user.role
        },
        'stats': {
            'pending': pending_count,
            'approved_today': approved_today,
            'new_entries_week': new_entries_this_week
        },
        'pending_entries': [{
            'id': e.id,
            'entry_id': e.entry_id,
            'farmer_name': e.farmer.name if e.farmer else 'Unknown',
            'animal_tag': e.animal.tag_number if e.animal else 'N/A',
            'drug_name': e.drug.name if e.drug else 'N/A',
            'dosage': e.dosage,
            'unit': e.unit,
            'treatment_date': e.treatment_date.isoformat() if e.treatment_date else None,
            'animal_species': e.animal.species if e.animal else 'N/A',
            'drug_max_dosage': e.drug.max_dosage if e.drug else None,
            'withdrawal_end_date': e.withdrawal_end_date.isoformat() if e.withdrawal_end_date else None,
            'created_at': e.created_at.isoformat() if e.created_at else None,
            'created_ago': format_time_ago(e.created_at) if e.created_at else None
        } for e in pending_entries]
    })


@app.route('/api/authority/dashboard')
def authority_dashboard_api():
    if 'user_id' not in session or session['role'] != 'authority':
        return jsonify({'error': 'Unauthorized'}), 401

    user = User.query.get(session['user_id'])

    total_entries = AMUEntry.query.count()
    total_approved = AMUEntry.query.filter_by(status='approved').count()
    total_violations = AMUEntry.query.filter_by(status='rejected').count()
    total_farms = User.query.filter_by(role='farmer').count()

    today = datetime.now().date()
    entries_today = AMUEntry.query.filter(
        db.func.date(AMUEntry.created_at) == today
    ).count()

    week_ago = datetime.now() - timedelta(days=7)
    entries_this_week = AMUEntry.query.filter(
        AMUEntry.created_at >= week_ago
    ).count()

    compliance_rate = (total_approved / total_entries * 100) if total_entries > 0 else 0

    recent_entries = AMUEntry.query.order_by(AMUEntry.created_at.desc()).limit(20).all()

    drug_usage = db.session.query(
        Drug.name,
        db.func.count(AMUEntry.id).label('usage_count'),
        (db.func.count(AMUEntry.id) * 100.0 / total_entries).label('percentage')
    ).join(AMUEntry).group_by(Drug.name).order_by(db.func.count(AMUEntry.id).desc()).limit(10).all()

    # Compliance trend (last 6 months)
    compliance_trend = []
    for i in range(5, -1, -1):
        month_start = datetime.now().replace(day=1) - timedelta(days=30 * i)
        if i == 0:
            month_end = datetime.now()
        else:
            next_month = month_start + timedelta(days=32)
            month_end = next_month.replace(day=1) - timedelta(days=1)

        month_entries = AMUEntry.query.filter(
            AMUEntry.created_at >= month_start,
            AMUEntry.created_at <= month_end
        ).all()

        month_total = len(month_entries)
        month_approved = len([e for e in month_entries if e.status == 'approved'])
        month_compliance = (month_approved / month_total * 100) if month_total > 0 else 0

        compliance_trend.append({
            'month': month_start.strftime('%b %Y'),
            'compliance_rate': round(month_compliance, 1),
            'total_entries': month_total,
            'approved': month_approved
        })

    # Regional distribution (simulated by farmer_id % 4)
    regions = {
        'North Zone': 0,
        'South Zone': 0,
        'East Zone': 0,
        'West Zone': 0
    }

    for entry in AMUEntry.query.all():
        farmer_mod = entry.farmer_id % 4
        if farmer_mod == 0:
            regions['North Zone'] += 1
        elif farmer_mod == 1:
            regions['South Zone'] += 1
        elif farmer_mod == 2:
            regions['East Zone'] += 1
        else:
            regions['West Zone'] += 1

    regional_distribution = []
    for region, count in regions.items():
        percentage = (count / total_entries * 100) if total_entries > 0 else 0
        regional_distribution.append({
            'region': region,
            'count': count,
            'percentage': round(percentage, 1)
        })

    return jsonify({
        'user': {
            'name': user.name,
            'role': user.role
        },
        'stats': {
            'total_entries': total_entries,
            'compliance_rate': round(compliance_rate, 1),
            'violations': total_violations,
            'farms': total_farms,
            'entries_today': entries_today,
            'entries_this_week': entries_this_week
        },
        'recent_entries': [{
            'id': e.id,
            'entry_id': e.entry_id,
            'farmer_name': e.farmer.name if e.farmer else 'Unknown',
            'animal_tag': e.animal.tag_number if e.animal else 'N/A',
            'drug_name': e.drug.name if e.drug else 'N/A',
            'dosage': e.dosage,
            'unit': e.unit,
            'status': e.status,
            'vet_name': e.vet.name if e.vet else 'Pending',
            'treatment_date': e.treatment_date.isoformat() if e.treatment_date else None,
            'reviewed_at': e.reviewed_at.isoformat() if e.reviewed_at else None,
            'created_at': e.created_at.isoformat() if e.created_at else None
        } for e in recent_entries],
        'drug_analytics': [{
            'drug_name': d.name,
            'usage_count': int(d.usage_count),
            'percentage': float(d.percentage)
        } for d in drug_usage],
        'compliance_trend': compliance_trend,
        'regional_distribution': regional_distribution
    })


# Analytics data for charts
@app.route('/api/analytics')
def get_analytics():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    # Monthly entries (last 12 months)
    monthly_entries = []
    for i in range(11, -1, -1):
        month_start = datetime.now().replace(day=1) - timedelta(days=30 * i)
        if i == 0:
            month_end = datetime.now()
        else:
            next_month = month_start + timedelta(days=32)
            month_end = next_month.replace(day=1) - timedelta(days=1)

        count = AMUEntry.query.filter(
            AMUEntry.created_at >= month_start,
            AMUEntry.created_at <= month_end
        ).count()
        monthly_entries.append({
            'month': month_start.strftime('%b %Y'),
            'count': count
        })

    # Regional compliance (reuse simulated regions)
    regional_compliance = []
    regions = ['North Zone', 'South Zone', 'East Zone', 'West Zone']

    for idx, region in enumerate(regions):
        region_entries = []
        all_entries = AMUEntry.query.all()
        for e in all_entries:
            if e.farmer_id % 4 == idx:
                region_entries.append(e)

        total = len(region_entries)
        approved = len([e for e in region_entries if e.status == 'approved'])
        compliance = (approved / total * 100) if total > 0 else 0

        regional_compliance.append({
            'region': region,
            'compliance_rate': round(compliance, 1),
            'total_entries': total,
            'approved': approved
        })

    # Species distribution
    species_counts = {}
    for e in AMUEntry.query.all():
        if e.animal and e.animal.species:
            key = e.animal.species.capitalize()
            species_counts[key] = species_counts.get(key, 0) + 1

    total_species = sum(species_counts.values())
    species_distribution = [{
        'species': name,
        'count': count,
        'percentage': round((count / total_species * 100) if total_species > 0 else 0, 1)
    } for name, count in species_counts.items()]

    # Monthly violation trends (rejected entries)
    monthly_violations = []
    for i in range(11, -1, -1):
        month_start = datetime.now().replace(day=1) - timedelta(days=30 * i)
        if i == 0:
            month_end = datetime.now()
        else:
            next_month = month_start + timedelta(days=32)
            month_end = next_month.replace(day=1) - timedelta(days=1)

        violations = AMUEntry.query.filter(
            AMUEntry.created_at >= month_start,
            AMUEntry.created_at <= month_end,
            AMUEntry.status == 'rejected'
        ).count()

        monthly_violations.append({
            'month': month_start.strftime('%b %Y'),
            'violations': violations
        })

    return jsonify({
        'monthly_entries': monthly_entries,
        'regional_compliance': regional_compliance,
        'species_distribution': species_distribution,
        'monthly_violations': monthly_violations
    })


@app.route('/api/animals', methods=['GET', 'POST'])
def get_animals():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    if request.method == 'POST':
        if session['role'] != 'farmer':
            return jsonify({'error': 'Only farmers can add animals'}), 403

        data = request.get_json()
        animal = Animal(
            tag_number=data['tag_number'],
            species=data['species'],
            farmer_id=session['user_id']
        )

        try:
            db.session.add(animal)
            db.session.commit()
            return jsonify({
                'success': True,
                'animal': {
                    'id': animal.id,
                    'tag_number': animal.tag_number,
                    'species': animal.species
                }
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400

    if session['role'] == 'farmer':
        animals = Animal.query.filter_by(farmer_id=session['user_id']).all()
    else:
        animals = Animal.query.all()

    return jsonify([{
        'id': a.id,
        'tag_number': a.tag_number,
        'species': a.species
    } for a in animals])


@app.route('/api/drugs')
def get_drugs():
    drugs = Drug.query.all()
    return jsonify([{
        'id': d.id,
        'name': d.name,
        'withdrawal_period_days': d.withdrawal_period_days,
        'max_dosage': d.max_dosage,
        'unit': d.unit
    } for d in drugs])


@app.route('/api/alerts')
def get_alerts():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    role = session['role']

    base_alerts = Alert.query.filter_by(user_id=user_id).order_by(Alert.created_at.desc()).all()

    alerts_list = [{
        'id': a.id,
        'alert_type': a.alert_type,
        'title': a.title,
        'message': a.message,
        'priority': a.priority,
        'is_read': a.is_read,
        'created_at': a.created_at.isoformat() if a.created_at else None
    } for a in base_alerts]

    # Augment for farmers: withdrawal & compliance alerts from AMU entries
    if role == 'farmer':
        farmer_entries = AMUEntry.query.filter_by(farmer_id=user_id).all()

        # Withdrawal alerts
        for e in farmer_entries:
            if e.status == 'approved' and e.withdrawal_end_date:
                end_date = e.withdrawal_end_date
                days_remaining = (end_date - datetime.now().date()).days
                if days_remaining <= 14:
                    priority = 'urgent' if days_remaining <= 2 else 'high' if days_remaining <= 5 else 'medium'
                    alerts_list.append({
                        'id': f'withdrawal-{e.id}',
                        'alert_type': 'withdrawal',
                        'title': f'{e.animal.tag_number if e.animal else "Animal"} - Withdrawal '
                                 f'{"Ending Soon" if days_remaining <= 2 else "Active"}',
                        'message': f'{e.drug.name if e.drug else "Drug"} treatment withdrawal period '
                                   f'ends {end_date.strftime("%B %d, %Y")}',
                        'priority': priority,
                        'is_read': False,
                        'created_at': e.created_at.isoformat() if e.created_at else None,
                        'entry_id': e.entry_id,
                        'withdrawal_end_date': end_date.isoformat()
                    })

        # Compliance alerts (rejected entries)
        for e in farmer_entries:
            if e.status == 'rejected':
                alerts_list.append({
                    'id': f'compliance-{e.id}',
                    'alert_type': 'compliance',
                    'title': f'Entry Rejected: {e.entry_id}',
                    'message': f'Your AMU entry was rejected. {e.vet_notes if e.vet_notes else "Please review and resubmit."}',
                    'priority': 'high',
                    'is_read': False,
                    'created_at': e.reviewed_at.isoformat() if e.reviewed_at else e.created_at.isoformat() if e.created_at else None,
                    'entry_id': e.entry_id
                })

    return jsonify(alerts_list)


@app.route('/api/audit-logs')
def get_audit_logs():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(50).all()

    return jsonify([{
        'id': l.id,
        'log_id': l.log_id,
        'user_name': l.user.name if l.user else 'Unknown',
        'user_role': l.user.role if l.user else 'Unknown',
        'action': l.action,
        'description': l.description,
        'related_entry_id': l.related_entry_id,
        'timestamp': l.timestamp.isoformat() if l.timestamp else None
    } for l in logs])


@app.route('/api/amu-entries/<int:entry_id>')
def get_entry(entry_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    entry = AMUEntry.query.get(entry_id)
    if not entry:
        return jsonify({'error': 'Entry not found'}), 404

    return jsonify({
        'id': entry.id,
        'entry_id': entry.entry_id,
        'farmer_name': entry.farmer.name if entry.farmer else 'Unknown',
        'animal_tag': entry.animal.tag_number if entry.animal else 'N/A',
        'animal_species': entry.animal.species if entry.animal else 'N/A',
        'drug_name': entry.drug.name if entry.drug else 'N/A',
        'drug_max_dosage': entry.drug.max_dosage if entry.drug else None,
        'dosage': entry.dosage,
        'unit': entry.unit,
        'treatment_date': entry.treatment_date.isoformat() if entry.treatment_date else None,
        'withdrawal_end_date': entry.withdrawal_end_date.isoformat() if entry.withdrawal_end_date else None,
        'status': entry.status,
        'created_at': entry.created_at.isoformat() if entry.created_at else None,
        'created_ago': format_time_ago(entry.created_at) if entry.created_at else None
    })


def format_time_ago(dt):
    if not dt:
        return 'Recently'
    delta = datetime.utcnow() - dt
    if delta.days > 0:
        return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
    hours = delta.seconds // 3600
    if hours > 0:
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    minutes = delta.seconds // 60
    return f"{minutes} minute{'s' if minutes > 1 else ''} ago"


@app.route('/api/test-db')
def test_database():
    try:
        db.session.execute(db.text('SELECT 1'))

        db_info = {
            'connected': True,
            'database_uri': app.config['SQLALCHEMY_DATABASE_URI'].split('@')[-1]
            if '@' in app.config['SQLALCHEMY_DATABASE_URI'] else 'hidden',
            'tables': []
        }

        try:
            user_count = User.query.count()
            animal_count = Animal.query.count()
            drug_count = Drug.query.count()
            entry_count = AMUEntry.query.count()
            log_count = AuditLog.query.count()
            alert_count = Alert.query.count()

            db_info['tables'] = {
                'users': user_count,
                'animals': animal_count,
                'drugs': drug_count,
                'amu_entries': entry_count,
                'audit_logs': log_count,
                'alerts': alert_count
            }
        except Exception as e:
            db_info['tables'] = {'error': str(e)}

        return jsonify({
            'status': 'success',
            'message': 'Database connection successful!',
            'database': db_info
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Database connection failed!',
            'error': str(e),
            'database_uri': app.config['SQLALCHEMY_DATABASE_URI'].split('@')[-1]
            if '@' in app.config['SQLALCHEMY_DATABASE_URI'] else 'hidden',
            'help': 'Please check: 1) PostgreSQL is running, 2) Database "farmguard" exists, 3) Username/password are correct'
        }), 500


def init_db():
    with app.app_context():
        try:
            print("Connecting to database...")
            print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI'].split('@')[-1] if '@' in app.config['SQLALCHEMY_DATABASE_URI'] else 'hidden'}")

            db.session.execute(db.text('SELECT 1'))
            print("✓ Database connection successful!")

            print("Creating database tables...")
            db.create_all()
            print("✓ Tables created successfully!")

            if User.query.count() == 0:
                print("Adding sample data...")
                farmer = User(
                    identifier='FARM001',
                    password_hash=generate_password_hash('password123'),
                    name='Rajesh Kumar',
                    role='farmer',
                    phone='9876543210'
                )

                custom_farmer = User(
                    identifier='kayalvizhi110906',
                    password_hash=generate_password_hash('password123'),
                    name='Kayalvizhi',
                    role='farmer',
                    phone=''
                )

                vet = User(
                    identifier='VET001',
                    password_hash=generate_password_hash('password123'),
                    name='Dr. Priya Sharma',
                    role='vet',
                    email='priya.sharma@vet.com'
                )

                authority = User(
                    identifier='AUTH001',
                    password_hash=generate_password_hash('password123'),
                    name='Admin User',
                    role='authority',
                    email='admin@authority.gov.in'
                )

                db.session.add_all([farmer, vet, authority, custom_farmer])

                drugs = [
                    Drug(name='Oxytetracycline', withdrawal_period_days=7, max_dosage=10, unit='mg/kg'),
                    Drug(name='Amoxicillin', withdrawal_period_days=5, max_dosage=15, unit='mg/kg'),
                    Drug(name='Enrofloxacin', withdrawal_period_days=10, max_dosage=5, unit='mg/kg'),
                    Drug(name='Penicillin G', withdrawal_period_days=14, max_dosage=20000, unit='IU/kg')
                ]
                db.session.add_all(drugs)
                db.session.commit()

                animals = [
                    Animal(tag_number='CATTLE-001', species='cattle', farmer_id=farmer.id),
                    Animal(tag_number='CATTLE-002', species='cattle', farmer_id=farmer.id),
                    Animal(tag_number='BUFFALO-001', species='buffalo', farmer_id=farmer.id),
                    Animal(tag_number='GOAT-001', species='goat', farmer_id=farmer.id),
                    Animal(tag_number='CATTLE-003', species='cattle', farmer_id=custom_farmer.id),
                    Animal(tag_number='BUFFALO-002', species='buffalo', farmer_id=custom_farmer.id),
                    Animal(tag_number='GOAT-002', species='goat', farmer_id=custom_farmer.id),
                ]
                db.session.add_all(animals)
                db.session.commit()
                print("✓ Sample data added successfully!")
            else:
                print("✓ Database already has data, skipping sample data insertion.")

            custom_user = User.query.filter_by(identifier='kayalvizhi110906', role='farmer').first()
            if not custom_user:
                print("Adding custom user kayalvizhi110906...")
                custom_user = User(
                    identifier='kayalvizhi110906',
                    password_hash=generate_password_hash('password123'),
                    name='Kayalvizhi',
                    role='farmer',
                    phone=''
                )
                db.session.add(custom_user)
                db.session.commit()
                print("✓ Custom user added successfully!")
            else:
                print("✓ Custom user already exists.")

        except Exception as e:
            print(f"✗ Database initialization failed: {str(e)}")
            print("\nTroubleshooting steps:")
            print("1. Make sure PostgreSQL is running")
            print("2. Verify database 'farmguard' exists: CREATE DATABASE farmguard;")
            print("3. Check username/password in SQLALCHEMY_DATABASE_URI")
            print("4. Verify PostgreSQL port (default: 5432)")
            raise


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)