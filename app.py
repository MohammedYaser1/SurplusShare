from flask import (
    Flask, render_template, request, redirect, url_for, flash, jsonify, session
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os
import math

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Runtime configuration comes from environment variables.
# Keep deployment credentials out of the repository.
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))

database_url = os.getenv('DATABASE_URL')
if not database_url:
    raise RuntimeError(
        'DATABASE_URL is required. Set it in the environment before starting the application.'
    )

# Some hosting providers still expose the legacy postgres:// scheme.
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # donor, recipient, charity
    organization = db.Column(db.String(100), nullable=True)
    address = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'organization': self.organization,
            'address': self.address,
            'latitude': self.latitude,
            'longitude': self.longitude,
        }

class FoodListing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    quantity = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    expiry_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='available')
    donor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    pickup_location = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    donor = db.relationship('User', backref=db.backref('listings', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'quantity': self.quantity,
            'category': self.category,
            'expiry_date': self.expiry_date.isoformat(),
            'status': self.status,
            'pickup_location': self.pickup_location,
            'latitude': self.latitude,
            'longitude': self.longitude
        }

class FoodRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    listing_id = db.Column(
        db.Integer, 
        db.ForeignKey('food_listing.id'), 
        nullable=False
    )
    
    recipient_id = db.Column(
        db.Integer, 
        db.ForeignKey('user.id'), 
        nullable=False
    )
    
    status = db.Column(
        db.String(20), 
        default='pending'
    )  # pending, accepted, rejected, completed
    
    message = db.Column(
        db.Text, 
        nullable=True
    )
    
    created_at = db.Column(
        db.DateTime, 
        default=datetime.utcnow
    )
    
    scheduled_pickup = db.Column(
        db.DateTime, 
        nullable=True
    )

    # Relationships
    listing = db.relationship(
        'FoodListing', 
        backref=db.backref('requests', lazy=True)
    )

    recipient = db.relationship(
        'User', 
        backref=db.backref('requests', lazy=True)
    )

    def to_dict(self):
        return {
            'id': self.id,
            'listing_id': self.listing_id,
            'recipient_id': self.recipient_id,
            'status': self.status,
            'message': self.message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'scheduled_pickup': self.scheduled_pickup.isoformat() if self.scheduled_pickup else None,
        }


class Message(db.Model):
    __tablename__ = 'message'

    id = db.Column(db.Integer, primary_key=True)

    sender_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )

    receiver_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )

    request_id = db.Column(
        db.Integer,
        db.ForeignKey('food_request.id'),
        nullable=True
    )

    content = db.Column(
        db.Text,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    is_read = db.Column(
        db.Boolean,
        default=False
    )

    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id])
    receiver = db.relationship('User', foreign_keys=[receiver_id])
    request = db.relationship('FoodRequest', backref=db.backref('messages', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'request_id': self.request_id,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'is_read': self.is_read
        }
# Helper Functions
def calculate_distance(lat1, lon1, lat2, lon2):
    # Haversine formula to calculate distance between two points
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2) * math.sin(dlat/2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon/2) * math.sin(dlon/2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    return distance

import requests

def get_user_coordinates(address):
    """
    Uses OpenStreetMap Nominatim to get latitude and longitude for a given address.
    Defaults to Hyderabad if no result is found.
    """
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": address,
        "format": "json",
        "limit": 1
    }

    try:
        response = requests.get(url, params=params, headers={'User-Agent': 'SurplusShare/1.0'})
        response.raise_for_status()
        data = response.json()
        if data:
            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            return lat, lon
    except Exception as e:
        print(f"Geocoding error: {e}")

    # Default to Hyderabad if not found or error
    return (17.3850, 78.4867)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        organization = request.form.get('organization', '')
        address = request.form['address']
       
        if User.query.filter_by(username=username).first():
            flash('Username already taken', 'danger')
            return redirect(url_for('register'))
       
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))
       
        lat, lon = get_user_coordinates(address)
       
        new_user = User(
            username=username,
            email=email,
            role=role,
            organization=organization,
            address=address,
            latitude=lat,
            longitude=lon
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
       
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
   
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        remember = True if request.form.get('remember') else False
       
        user = User.query.filter_by(email=email).first()
       
        if not user or not user.check_password(password):
            flash('Invalid email or password', 'danger')
            return redirect(url_for('login'))
       
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role
       
        flash('Login successful!', 'success')
        return redirect(url_for('dashboard'))
   
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login to access this page', 'warning')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if user.role == 'donor':
        # Donor: show only their own listings that are NOT completed
        listings = (
            FoodListing.query
            .filter_by(donor_id=user.id)
            .filter(FoodListing.status != 'completed')
            .all()
        )

        return render_template(
            'dashboard_donor.html',
            user=user,
            listings=listings
        )

    else:
        # Recipient or Charity: show only available listings
        available_listings = (
            FoodListing.query
            .filter_by(status='available')
            .all()
        )

        user_lat, user_lon = user.latitude, user.longitude

        # Calculate distance to user for sorting
        for listing in available_listings:
            listing.distance = round(
                calculate_distance(
                    user_lat, user_lon,
                    listing.latitude, listing.longitude
                ), 1
            )

        # Sort listings by nearest
        available_listings.sort(key=lambda x: x.distance)

        # Get user's own requests (to display below if needed)
        requests = (
            FoodRequest.query
            .filter_by(recipient_id=user.id)
            .all()
        )

        return render_template(
            'dashboard_recipient.html',
            user=user,
            listings=available_listings,
            requests=requests
        )



@app.route('/create_listing', methods=['GET', 'POST'])
def create_listing():
    if 'user_id' not in session or session['role'] != 'donor':
        flash('You must be a donor to create a listing', 'warning')
        return redirect(url_for('login'))

    # Get user object from DB
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        quantity = request.form['quantity']
        category = request.form['category']
        expiry_date = datetime.strptime(request.form['expiry_date'], '%Y-%m-%d')
        pickup_location = request.form['pickup_location']

        lat, lon = get_user_coordinates(pickup_location)

        new_listing = FoodListing(
            title=title,
            description=description,
            quantity=quantity,
            category=category,
            expiry_date=expiry_date,
            donor_id=session['user_id'],
            pickup_location=pickup_location,
            latitude=lat,
            longitude=lon
        )
        db.session.add(new_listing)
        db.session.commit()

        flash('Food listing created successfully!', 'success')
        return redirect(url_for('dashboard'))

    categories = ['Bakery', 'Dairy', 'Produce', 'Prepared Meals', 'Meat',
                  'Frozen Foods', 'Pantry Items', 'Other']

    return render_template('create_listing.html', categories=categories, user=user)

@app.route('/listing/<int:listing_id>')
def listing_detail(listing_id):
    listing = FoodListing.query.get_or_404(listing_id)
    donor = User.query.get(listing.donor_id)
   
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        user_lat, user_lon = user.latitude, user.longitude
        distance = round(calculate_distance(
            user_lat, user_lon,
            listing.latitude, listing.longitude
        ), 1)
    else:
        distance = None
   
    return render_template('listing_detail.html', listing=listing, donor=donor, distance=distance)

@app.route('/request_listing/<int:listing_id>', methods=['GET', 'POST'])
def request_listing(listing_id):
    if 'user_id' not in session or session['role'] == 'donor':
        flash('You must be a recipient or charity to request food', 'warning')
        return redirect(url_for('login'))
   
    listing = FoodListing.query.get_or_404(listing_id)
   
    if listing.status != 'available':
        flash('This listing is no longer available', 'danger')
        return redirect(url_for('dashboard'))
   
    if request.method == 'POST':
        message = request.form['message']
       
        new_request = FoodRequest(
            listing_id=listing.id,
            recipient_id=session['user_id'],
            message=message
        )
        listing.status = 'reserved'
       
        db.session.add(new_request)
        db.session.commit()
       
        flash('Request submitted successfully!', 'success')
        return redirect(url_for('dashboard'))
   
    return render_template('request_listing.html', listing=listing)

@app.route('/manage_requests')
def manage_requests():
    if 'user_id' not in session or session['role'] != 'donor':
        flash('Only donors can manage requests', 'warning')
        return redirect(url_for('login'))
   
    user = User.query.get(session['user_id'])
    listings = FoodListing.query.filter_by(donor_id=user.id).all()
    listing_ids = [listing.id for listing in listings]

    # Show only requests on these listings, and exclude rejected & completed
    requests = FoodRequest.query.filter(
        FoodRequest.listing_id.in_(listing_ids),
        FoodRequest.status.notin_(['rejected', 'completed'])
    ).all()
   
    return render_template('manage_requests.html', requests=requests)

@app.route('/update_request/<int:request_id>/<status>')
def update_request(request_id, status):
    if 'user_id' not in session or session['role'] != 'donor':
        flash('Only donors can manage requests', 'warning')
        return redirect(url_for('login'))
   
    food_request = FoodRequest.query.get_or_404(request_id)
    listing = FoodListing.query.get(food_request.listing_id)
   
    if listing.donor_id != session['user_id']:
        flash('You are not authorized to manage this request', 'danger')
        return redirect(url_for('dashboard'))
   
    if status == 'accept':
        food_request.status = 'accepted'
        listing.status = 'claimed'
        flash('Request accepted!', 'success')
    elif status == 'reject':
        food_request.status = 'rejected'
        listing.status = 'available'
        flash('Request rejected', 'info')
    else:
        flash('Invalid action', 'danger')
        return redirect(url_for('manage_requests'))
   
    db.session.commit()
    return redirect(url_for('manage_requests'))

@app.route('/complete_request/<int:request_id>', methods=['POST'])
def complete_request(request_id):
    if 'user_id' not in session or session['role'] != 'donor':
        flash('Only donors can mark requests as completed', 'warning')
        return redirect(url_for('login'))
    
    food_request = FoodRequest.query.get_or_404(request_id)
    listing = FoodListing.query.get(food_request.listing_id)

    # make sure this donor owns this listing
    if listing.donor_id != session['user_id']:
        flash('Unauthorized action', 'danger')
        return redirect(url_for('dashboard'))

    food_request.status = 'completed'
    listing.status = 'completed'  # optional — or you can keep listing separate
    db.session.commit()

    flash('Marked as picked up!', 'success')
    return redirect(url_for('manage_requests'))

@app.route('/messages')
def messages():
    if 'user_id' not in session:
        flash('Please login to access messages', 'warning')
        return redirect(url_for('login'))
   
    user_id = session['user_id']
    # Get conversations
    sent_messages = Message.query.filter_by(sender_id=user_id).all()
    received_messages = Message.query.filter_by(receiver_id=user_id).all()
   
    # Get unique conversation partners
    conversations = {}
    for msg in sent_messages + received_messages:
        partner_id = msg.receiver_id if msg.sender_id == user_id else msg.sender_id
        partner = User.query.get(partner_id)
       
        if partner_id not in conversations:
            conversations[partner_id] = {
                'partner': partner,
                'last_message': msg,
                'unread': False
            }
        else:
            if msg.created_at > conversations[partner_id]['last_message'].created_at:
                conversations[partner_id]['last_message'] = msg
       
        if msg.receiver_id == user_id and not msg.is_read:
            conversations[partner_id]['unread'] = True
   
    # Mark messages as read when viewing
    for msg in received_messages:
        if not msg.is_read:
            msg.is_read = True
    db.session.commit()
   
    return render_template('messages.html', conversations=conversations.values())

@app.route('/schedule_pickup/<int:request_id>', methods=['POST'])
def schedule_pickup(request_id):
    req = FoodRequest.query.get_or_404(request_id)  # fix model name
    if req.status != 'accepted':
        flash('Only accepted requests can be scheduled.', 'warning')
        return redirect(url_for('manage_requests'))

    req.status = 'scheduled'
    req.scheduled_pickup = datetime.now(timezone.utc)  # fix field name + timezone
    db.session.commit()

    flash('Pickup successfully scheduled!', 'success')
    return redirect(url_for('manage_requests'))

@app.route('/conversation/<int:partner_id>')
def conversation(partner_id):
    if 'user_id' not in session:
        flash('Please login to access messages', 'warning')
        return redirect(url_for('login'))
   
    user_id = session['user_id']
    partner = User.query.get_or_404(partner_id)
   
    messages = Message.query.filter(
        ((Message.sender_id == user_id) & (Message.receiver_id == partner_id)) |
        ((Message.sender_id == partner_id) & (Message.receiver_id == user_id))
    ).order_by(Message.created_at).all()
   
    # Mark messages as read
    for msg in messages:
        if msg.receiver_id == user_id and not msg.is_read:
            msg.is_read = True
    db.session.commit()
   
    return render_template('conversation.html', partner=partner, messages=messages)

@app.route('/send_message', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})
   
    data = request.get_json()
    receiver_id = data.get('receiver_id')
    content = data.get('content')
   
    if not receiver_id or not content:
        return jsonify({'success': False, 'error': 'Missing data'})
   
    new_message = Message(
        sender_id=session['user_id'],
        receiver_id=receiver_id,
        content=content
    )
    db.session.add(new_message)
    db.session.commit()
   
    return jsonify({
        'success': True,
        'message': {
            'id': new_message.id,
            'content': content,
            'created_at': new_message.created_at.strftime('%b %d, %Y %I:%M %p'),
            'sender_id': session['user_id']
        }
    })

@app.route('/map')
def map_view():
    if 'user_id' not in session:
        flash('Please login to view the map', 'warning')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if user.role == 'donor':
        recipients = User.query.filter(User.role.in_(['recipient', 'charity'])).all()
        listings = []
    else:
        recipients = []
        listings = FoodListing.query.filter_by(status='available').all()

    # Convert to dicts for JSON serialization in template
    user_dict = user.to_dict()
    recipient_dicts = [r.to_dict() for r in recipients]
    listing_dicts = [l.to_dict() for l in listings]

    return render_template(
        'map.html',
        user=user_dict,
        recipients=recipient_dicts,
        listings=listing_dicts
    )


@app.route('/get_locations')
def get_locations():
    if 'user_id' not in session:
        return jsonify([])

    user = User.query.get(session['user_id'])
    locations = []

    if user.role == 'donor':
        # Donor sees recipients & charities on the map
        entities = User.query.filter(User.role.in_(['recipient', 'charity'])).all()
        for entity in entities:
            locations.append({
                'id': entity.id,
                'name': entity.username,
                'role': entity.role,
                'organization': entity.organization,
                'address': entity.address,
                'lat': entity.latitude,
                'lon': entity.longitude
            })
    else:
        # Recipient sees all listings that are NOT completed
        listings = (
            FoodListing.query
            .filter(FoodListing.status != 'completed')
            .all()
        )

        for listing in listings:
            donor = User.query.get(listing.donor_id)
            locations.append({
                'id': listing.id,
                'name': listing.title,
                'role': 'listing',
                'category': listing.category,
                'quantity': listing.quantity,
                'expiry': listing.expiry_date.strftime('%b %d'),
                'donor': donor.username,
                'address': listing.pickup_location,
                'lat': listing.latitude,
                'lon': listing.longitude
            })

    return jsonify(locations)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)


