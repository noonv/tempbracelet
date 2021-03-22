#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
server for braslet_tmp

'''

import os, time
from flask import Flask
from flask import request
from flask import render_template
from flask import jsonify
from flask import Response
from flask import redirect, url_for, flash

from flask_sqlalchemy import SQLAlchemy

from flask_login import UserMixin, LoginManager, login_user, login_required, current_user, logout_user

from datetime import datetime
from pytz import timezone

from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
SECRET_KEY = os.environ.get("SECRET_KEY")
app.config['SECRET_KEY'] = SECRET_KEY
DEBUG = os.environ.get("DEBUG")
app.config['DEBUG'] = DEBUG
TESTING = os.environ.get("TESTING")
app.config['TESTING'] = TESTING
SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI")
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI

TEMPERATURE_THRESHOLD = float(os.environ.get("TEMPERATURE_THRESHOLD"))
app.config['TEMPERATURE_THRESHOLD'] = TEMPERATURE_THRESHOLD
INIT_KEY = os.environ.get("INIT_KEY")
app.config['INIT_KEY'] = INIT_KEY

INIT_USER_NAME = os.environ.get("INIT_USER_NAME")
INIT_USER_EMAIL = os.environ.get("INIT_USER_EMAIL")
INIT_USER_PASSWORD = os.environ.get("INIT_USER_PASSWORD")
INIT_USER_CLASS = os.environ.get("INIT_USER_CLASS")
INIT_USER_BRID = int(os.environ.get("INIT_USER_BRID"))
INIT_USER_BRCODE = os.environ.get("INIT_USER_BRCODE")

TIME_ZONE = os.environ.get("TIME_ZONE", 'Europe/Kaliningrad')

os.environ['TZ'] = TIME_ZONE
time.tzset()
print(datetime.now())

#app.config.from_pyfile('settings.cfg')
db = SQLAlchemy(app)

#print(app.config)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(200), nullable=False)
    user_class = db.Column(db.String(50), default="")
    bracelet_id = db.Column(db.Integer, default=0)
    bracelet_code = db.Column(db.String(50), default="")
    temperature = db.Column(db.Float, default=0)
    time = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone('UTC')).astimezone(timezone(TIME_ZONE)))

    def __init__(self, name=None, email=None, password=None, uclass="", br_id=0, br_code="", temperature=0):
        self.name = name
        self.email = email
        self.password = password
        self.user_class = uclass
        self.bracelet_id = br_id
        self.bracelet_code = br_code
        self.temperature = temperature

    @property
    def serialize(self):
       """Return object data in easily serializable format"""
       return {
           'name' : self.name,
           'email': self.email,
           'user_class'  : self.user_class,
           'bracelet_id': self.bracelet_id,
           #'bracelet_code': self.bracelet_code,
           'temperature': self.temperature,
           'time': self.time
       }

    def __repr__(self):
        return '<User %r %d %d>' % (self.name, self.id, self.bracelet_id)

class Tempdata(db.Model):
    __tablename__ = 'tempdata'
    id = db.Column(db.Integer, primary_key=True)
    bracelet_id = db.Column(db.Integer, nullable=False)
    time = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone('UTC')).astimezone(timezone(TIME_ZONE)))
    temperature = db.Column(db.Float, nullable=False)

    def __init__(self, br_id=None, time=None, temperature=None):
        self.bracelet_id = br_id
        self.time = time
        self.temperature = temperature
    
    @property
    def serialize(self):
       """Return object data in easily serializable format"""
       return {
           'id'         : self.bracelet_id,
           'time': self.time,
           'temperature'  : self.temperature
       }

    def __repr__(self):
        return '<Tempdata %d %s %.2f>' % (self.bracelet_id, self.time, self.temperature)


login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    # since the user_id is just the primary key of our user table, use it in the query for the user
    return User.query.get(int(user_id))


@app.route('/profile')
def profile():
    if not current_user.is_active:
        return redirect(url_for('login'))

    return render_template('profile.html', name=current_user.name, email=current_user.email, user_class = current_user.user_class,
    bracelet_id = current_user.bracelet_id, bracelet_code = current_user.bracelet_code)
        

@app.route('/profile', methods=['POST'])
def profile_post():
    if not current_user.is_active:
        return redirect(url_for('login'))

    email = request.form.get('email')
    name = request.form.get('name')
    password = request.form.get('password')
    user_class = request.form.get('user_class')
    bracelet_id = request.form.get('bracelet_id')
    bracelet_code = request.form.get('bracelet_code')

    user = User.query.filter_by(email=email).first()

    # check if the user actually exists
    # take the user-supplied password, hash it, and compare it to the hashed password in the database
    if not user or current_user.email != email:
        flash('Проверьте введённые данные')
        return redirect(url_for('profile'))
    
    user.name = name
    user.password = generate_password_hash(password, method='sha256')
    user.user_class = user_class
    user.bracelet_id = bracelet_id
    user.bracelet_code = bracelet_code
    user.time = datetime.now(timezone('UTC')).astimezone(timezone(TIME_ZONE))
    db.session.commit()

    flash('Данные обновлены')
    return redirect(url_for('profile'))

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    email = request.form.get('email')
    password = request.form.get('password')
    remember = False
    if request.form.get('remember'):
        remember = True
    #print(request.form)
    #print(email, password, remember)

    user = User.query.filter_by(email=email).first()

    # check if the user actually exists
    # take the user-supplied password, hash it, and compare it to the hashed password in the database
    if not user or not check_password_hash(user.password, password):
        flash('Проверьте введённые данные')
        return redirect(url_for('login')) # if the user doesn't exist or password is wrong, reload the page

    login_user(user, remember=remember)

    # if the above check passes, then we know the user has the right credentials
    return redirect(url_for('index'))  

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/signup', methods=['POST'])
def signup_post():
    email = request.form.get('email')
    name = request.form.get('name')
    password = request.form.get('password')

    #print(email, name, password)

    user = User.query.filter_by(email=email).first() # if this returns a user, then the email already exists in database

    if user: # if a user is found, we want to redirect back to signup page so user can try again
        flash('Такой email уже есть')
        return redirect(url_for('signup'))

    # create a new user with the form data. Hash the password so the plaintext version isn't saved.
    new_user = User(email=email, name=name, password=generate_password_hash(password, method='sha256'))
    print('Add new user:', email, password)

    # add the new user to the database
    db.session.add(new_user)
    db.session.commit()

    return redirect(url_for('login'))    

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/init')
def init():
    key = request.args.get('key', '')
    print(key, 'vs', INIT_KEY)
    if key != INIT_KEY:
        return 'key error'
    db.drop_all()
    db.create_all()

    db.session.add(User(name=INIT_USER_NAME, email=INIT_USER_EMAIL, password=generate_password_hash(INIT_USER_PASSWORD, method='sha256'),  uclass=INIT_USER_CLASS, br_id=INIT_USER_BRID, br_code=INIT_USER_BRCODE))
    db.session.commit()

    return 'init done.'

@app.route('/')
def index():
    # index page
    #print(app.config['SQLALCHEMY_DATABASE_URI'])

    #users = User.query.all()
    #print(users)

    return render_template('index.html', TEMPERATURE_THRESHOLD=TEMPERATURE_THRESHOLD)

@app.route('/users')
def users():
    if not current_user.is_active:
        return redirect(url_for('login'))

    users = User.query.all()

    return render_template('users.html', TEMPERATURE_THRESHOLD=TEMPERATURE_THRESHOLD, users=users)

@app.route('/reports')
def reports():
    if not current_user.is_active:
        return redirect(url_for('login'))
    return render_template('reports.html')

@app.route('/api/update', methods=['GET', 'POST'])
def api_update():
    if request.method == 'POST':
        return 'post'
    else:
        # GET
        id = request.args.get('id', '')
        code = request.args.get('code', '')
        temperature = request.args.get('temperature', '')
        print("id=", id)
        print("code=", code)
        print("temperature=", temperature)

        if id == '':
            return 'No id!'

        user = User.query.filter(User.bracelet_id == int(id)).first()
        print(user, user.bracelet_code)

        if user.bracelet_code != code:
        #if check_code(id, code) == False:
            return 'Bad code: id='+id + ' code= '+code
        print('Code OK')

        user.temperature = temperature
        user.time = datetime.now(timezone('UTC')).astimezone(timezone(TIME_ZONE))

        db.session.add(Tempdata(br_id=int(id), time=user.time, temperature=temperature))
        db.session.commit()

        print(user.time)

        if float(temperature) > TEMPERATURE_THRESHOLD:
            print("!!! Alert Temperature !!!")
            # TBD

        #temps = Tempdata.query.all()
        #print(temps)

        return 'update ' + 'id= ' + str(id) + ' code= ' + code + ' temperature= '+temperature

@app.route('/api/data')
def api_data():
    id = request.args.get('id', '')

    if id == '':
        return 'No id!'
    
    temps = Tempdata.query.filter(Tempdata.bracelet_id == int(id)).all()
    #print(temps)

    #return 'data'
    return jsonify(data = [i.serialize for i in temps])

@app.route('/api/users')
def api_users():
    users = User.query.all()
    print(users)

    #return 'data'
    return jsonify(data = [i.serialize for i in users])

'''
@app.route('/api/userstemp')
def api_userstemp():
    users = User.query.all()
    print(users)

    res = []
    for user in users:
        id = user.bracelet_id
        print(user, id)
        temp = Tempdata.query.filter(Tempdata.bracelet_id == int(id)).order_by(Tempdata.time.desc()).first()
        if not temp:
            print("None temp found!")
        print(temp)
        ser = user.serialize
        ser['temperature'] = temp.temperature
        print(ser)
        res.append(ser)

    return jsonify(data = res)
'''        

def check_code(id, code):
    print('Check:', id, code)

    user = User.query.filter(User.bracelet_id == int(id)).first()
    print(user, user.bracelet_code)

    if user.bracelet_code == code:
        return True
    return False

if __name__ == '__main__':
    # '0.0.0.0' = 127.0.0.1 i.e. localhost
    # port = 5000 : we can modify it for localhost
    #app.run(host='0.0.0.0', port=5000, debug=True) # local webserver : app.run()
    app.run()