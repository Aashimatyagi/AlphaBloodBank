import os
import uuid
from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy import create_engine
import urllib.request
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_manager, LoginManager
from flask_login import login_required, current_user
import folium
import pandas
import json
import requests
from urllib.request import urlopen
from geopy.geocoders import ArcGIS
import smtplib


local_server = True
app = Flask(__name__)
app.secret_key = "aashimatyagi"

login_manager = LoginManager(app)
login_manager.login_view = 'donorlogin'


@login_manager.user_loader
def load_user(id):
    return Donor.query.get(int(id))


app.config['SQLALCHEMY_DATABASE_URI'] = "mysql://root:@localhost/bbms"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
db_engine = create_engine('mysql://root:@localhost/bbms')
db_engine.connect()

UPLOAD_FOLDER = 'static/images/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


class Donor(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(80), nullable=False)
    address = db.Column(db.Text, nullable=False)
    state = db.Column(db.String, nullable=False)
    phone = db.Column(db.Integer, nullable=False, default=0)
    dob = db.Column(db.String, nullable=False)
    bloodtype = db.Column(db.String(3), nullable=False)
    password = db.Column(db.String, nullable=False)
    profilepic = db.Column(db.String, nullable=False)


class Donation(UserMixin, db.Model):

    tid = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer, db.ForeignKey('donor.id'), nullable=False)
    date = db.Column(db.DateTime)
    unit = db.Column(db.Integer, nullable=False)
    vid = db.Column(db.Integer, db.ForeignKey(
        'volunteers.vid'), nullable=False)


class Volunteers(UserMixin, db.Model):
    vid = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(80), nullable=False)
    address = db.Column(db.Text, nullable=False)
    phone = db.Column(db.Integer, nullable=False, unique=True)
    dob = db.Column(db.String, nullable=False)
    gender = db.Column(db.String, nullable=False)


class Location(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uid = db.Column(db.Integer, db.ForeignKey('donor.id'), nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    state = db.Column(db.String, nullable=False)


@app.route("/")
@app.route("/about")
def about():
    return render_template('index.html', title='About Us!!!')


@app.route("/donate")
def donate():
    return render_template('donor.html', title='Donate!')


@app.route("/donornew",  methods=['GET', 'POST'])
def donarnew():
    if request.method == 'POST':
        name = request.form['name']
        add = request.form['address']
        ph = int(request.form['phone'])
        em = request.form['email']
        birth = request.form['birth']
        state = request.form['state']
        bloodgroup = request.form['bloodgroup']
        encpass = generate_password_hash(str(birth))

        global nom
        nom = ArcGIS()
        coordinates = nom.geocode(add)
        lat = [coordinates.latitude]
        lon = [coordinates.longitude]

        profilepic = request.files['file']
        picfilename = secure_filename(profilepic.filename)
        pic = str(uuid.uuid1()) + "_" + picfilename
        profilepic.save(os.path.join(app.config['UPLOAD_FOLDER'], pic))

        donor = Donor.query.filter_by(phone=ph).first()
        if donor:
            return render_template('donor_new.html', title='Donate!')
        blood = Donor(name=name, address=add, phone=ph,
                      email=em, dob=birth, bloodtype=bloodgroup, state=state, password=encpass, profilepic=pic)

        db.session.add(blood)
        db.session.commit()
        query = db.engine.execute(
            f"SELECT id FROM `donor` WHERE phone='{int(ph)}'")
        print()
        address = Location(
            uid=list(query)[0][0], lat=lat, lon=lon, state=state)
        db.session.add(address)
        db.session.commit()
        return render_template('donor_login.html', title='Donate!')

    return render_template('donor_new.html', title='Donate!')


@app.route("/donorlogin", methods=['GET', 'POST'])
def donorlogin():
    if current_user.is_authenticated:
        return redirect(url_for('donorprofile'))
    elif request.method == 'POST':
        userid = request.form['userid']
        pasw = request.form['passw']
        print(type(userid), type(pasw))
        donor = Donor.query.filter_by(phone=int(userid)).first()
        if donor and check_password_hash(donor.password, pasw):
            login_user(donor)
            return redirect(url_for('donorprofile'))
        else:
            print("not hello")
        return render_template('donor_login.html', title='Donate!')

    return render_template('donor_login.html', title='Donate!')


@app.route("/donorprofile", methods=['GET', 'POST'])
@login_required 
def donorprofile():
    id = current_user.id
    query = db.engine.execute(f"SELECT * FROM `donation` WHERE uid='{id}'")
    query2 = db.engine.execute(f"SELECT * FROM `volunteers`")
    if request.method == 'POST':
        unit = request.form['unit']
        incharge = request.form['incharge']
        date = request.form['date']
        vid = db.engine.execute(
            f"SELECT vid FROM `volunteers` where name='{incharge}'")
        transaction = Donation(uid=id, unit=unit, vid=vid, date=date)
        db.session.add(transaction)
        db.session.commit()
        return render_template('donorprofile.html', title='Donate!', query=query, query2=query2)

    return render_template('donorprofile.html', title='Donate!', query=query, query2=query2)


@app.route("/find")
def find():
    return render_template('find.html', title='Find!')


@app.route("/find_bylocation", methods=['GET', 'POST'])
def find_bylocation():
    send_url = "http://api.ipstack.com/check?access_key=738814229bd6e52de0636c37e7e178e4"
    geo_req = requests.get(send_url)
    geo_json = json.loads(geo_req.text)
    latitude_own = geo_json['latitude']
    longitude_own = geo_json['longitude']
    state = geo_json['region_name']
    data = pandas.read_sql(
        "SELECT * FROM `location` WHERE state=%s", db_engine, params=[state])
    print(data)

    uid = list(data["uid"])
    latitude = list(data["lat"])
    longitude = list(data["lon"])
    start_coords = (latitude_own, longitude_own)

    donor1 = folium.FeatureGroup(name='donors')
    donor1.add_child(folium.Marker(location=[
                     latitude_own, longitude_own], popup="YOU", icon=folium.Icon(color="blue")))
    for lat, lon, user in zip(latitude, longitude, uid):
        datas = pandas.read_sql(
            "SELECT * FROM `donor` where id=%s", db_engine, params=(user,))
        html = "<h5>"+str(datas['name'][0])+"</h5>"+"<img src="+str(url_for('static', filename='images/'+datas['profilepic'][0]))+"><br><br><button style='background-color:#38a9dc;text-align:center;color:white;border:0px;'>Blood Group  "+str(datas['bloodtype'][0])+"</button><form action='/find_bylocation/"+str(datas['id'][0])+"'> <button type='submit' style='background-color:red;display:block;text-align:center;text-align:center;color:white;border:0px;'>Request Blood</button>"
        donor1.add_child(folium.Marker(
            location=[lat, lon], popup=html, icon=folium.Icon(color="red")))

    map = folium.Map(location=start_coords, zoom_start=7)
    map.add_child(donor1)
    map.save("templates\map.html")    
    return render_template('find_bylocation.html', title='Find!')


@app.route("/find_bygroup")
def find_bygroup():
    return render_template('find_bygroup.html', title='Find!')


@app.route("/volunteers")
def volunteers():
    query = db.engine.execute(f"SELECT * FROM `volunteers`")
    print("hi")
    return render_template('volunteers.html', title='Volunteers', query=query)


@app.route("/blood")
def blood():
    return render_template('blood.html', title='Blood')

@app.route("/find_bylocation/<string:id>",methods=['POST','GET'])
def findbylocation(id):
    datas = pandas.read_sql(
            "SELECT * FROM `donor` where id=%s", db_engine, params=(id,))
    if request.method == 'POST':
        name = request.form['name']
        unit = request.form['unit']
        mobile= request.form['phone']
        subject="Request for Blood Donation:"
        body=f"{name} has requested {unit} of blood. Kindly help them.\nContact Number:{mobile}\n\n\n\nRegards\nALPHA BLOOD BANK"
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        # mail.send_message(subject, sender=params['gmail-user'], recipients=[data['email']],


    return render_template('email.html', title='Contact!')

@app.route("/edit/<string:id>",methods=['POST','GET'])
@login_required
def edit(id):
    datas = pandas.read_sql(
            "SELECT * FROM `donor` where id=%s", db_engine, params=(id,))
    if request.method == 'POST': 
        name = request.form['name']
        add = request.form['address']
        ph = int(request.form['phone'])
        em = request.form['email']
        birth = request.form['birth']
        state = request.form['state']
        bloodgroup = request.form['bloodgroup']
        profilepic = request.files['file']
        picfilename = secure_filename(profilepic.filename)
        pic = str(uuid.uuid1()) + "_" + picfilename
        profilepic.save(os.path.join(app.config['UPLOAD_FOLDER'], pic))
        db.engine.execute(f"UPDATE donor SET email = '{em}', name = '{name}', address = '{add}', state = '{state}', phone = {ph}, `dob` = '{birth}', bloodtype = '{bloodgroup}', profilepic = '{pic}' WHERE id = {id}")
        return redirect('/donorprofile')

    
    return render_template('edit.html', title='Edit')

@app.route("/delete/<string:id>",methods=['POST','GET'])
@login_required
def delete(id):
    db.engine.execute(f"DELETE FROM donor WHERE id={id}")
    db.engine.execute(f"DELETE FROM location WHERE id={id}")
    db.engine.execute(f"DELETE FROM donation WHERE id={id}")
    return render_template('index.html', title='Edit')


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return render_template('index.html', title='About Us!!!')


if __name__ == "__main__":
    app.run(debug=True)
