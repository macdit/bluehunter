from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
from data import Pharmacies
from flask_mysqldb import MySQL
from wtforms import Form, StringField, IntegerField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps


#Create new Flask application
app = Flask(__name__)

#Config flask_mysql
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Mm8026477'
app.config['MYSQL_DB'] = 'bluehunterapp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'


#init MySQL
mysql = MySQL(app)

# Create an instance of Pharmacies
Pharmacies = Pharmacies()

# Index OR Home page
@app.route('/')
def index():
    return render_template('home.html')

#About
@app.route('/about')
def about():
    return render_template('about.html')

#sorted pharmacies
@app.route('/sorted_pharmacies')
def sorted_pharmacies():
    return render_template('sorted_pharmacies.html')

#Pharmacies List
@app.route('/pharmacies')
def pharmacies():
    return render_template('pharmacies.html', pharmacies = Pharmacies)

# Individual pharmacy
@app.route('/pharmacie/<string:id>/')
def pharmacie(id):
    return render_template('pharmacie.html', id=id)

# Register Form Class
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')

# User Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        # Create cursor
        cur = mysql.connection.cursor()

        # Execute query
        cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash('You are now registered and can log in', 'success')

        return redirect(url_for('login'))
    return render_template('register.html', form=form)


# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get Form Fields
        username = request.form['username']
        password_candidate = request.form['password']

        # Create cursor
        cur = mysql.connection.cursor()

        # Get user by username
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            # Get stored hash
            data = cur.fetchone()
            password = data['password']

            # Compare Passwords
            if sha256_crypt.verify(password_candidate, password):
                # Passed
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
            # Close connection
            cur.close()
        else:
            #error = 'Username not found'
            error = 'The username OR passsword is Invalid'
            return render_template('login.html', error=error)

    return render_template('login.html')

# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

# Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

# Dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
    # Create cursor
    cur = mysql.connection.cursor()

    # Retrive all pharmacies
    result = cur.execute("SELECT * FROM pharmacies")

    pharmacies = cur.fetchall()

    if result > 0:
        return render_template('dashboard.html', pharmacies=pharmacies)
    else:
        msg = 'No pharmacy Found'
        return render_template('dashboard.html', msg=msg)
    # Close connection
    cur.close()

# Pharmacy Form Class
class PharmacyForm(Form):
    name = StringField('name', [validators.Length(min=1, max=300)])
    address = StringField('address', [validators.Length(min=1, max=300)])
    rate = IntegerField('rate', [validators.NumberRange(min=0, max=5)])
    drug = StringField('drug', [validators.Length(min=5, max=300)])


# Add Pharmacy route
@app.route('/add_pharmacy', methods=['GET', 'POST'])
@is_logged_in
def add_pharmacy():
    form = PharmacyForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        address = form.address.data
        rate = form.rate.data
        drug = form.drug.data

        # Create Cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute("INSERT INTO pharmacies(name, address,rate, drug) VALUES(%s, %s, %s, %s)",(name, address,rate, drug))

        # Commit to DB
        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('Pharmacy Created', 'success')

        return redirect(url_for('dashboard'))

    return render_template('add_pharmacy.html', form=form)


# Edit Pharmacy
@app.route('/edit_pharmacy/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_pharmacy(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get pharmacy by its id
    result = cur.execute("SELECT * FROM pharmacies WHERE id = %s", [id])

    pharmacy = cur.fetchone()  # can be change to pharmacy
    cur.close()
    # Get form
    form = PharmacyForm(request.form)

    # Populate pharmacy form fields
    form.name.data = pharmacy['name']
    form.address.data = pharmacy['address']
    form.rate.data = pharmacy['rate']
    form.drug.data = pharmacy['drug']

    if request.method == 'POST' and form.validate():
        name = request.form['name']
        address = request.form['address']
        rate = request.form['rate']
        drug = request.form['drug']

        # Create Cursor
        cur = mysql.connection.cursor()
        app.logger.info()
        # Execute
        cur.execute ("UPDATE pharmacies SET name=%s, address=%s, rate=%s, drug=%s WHERE id=%s",(name, address, rate, drug, id))
        # Commit to DB
        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('Pharmacy Updated', 'success')

        return redirect(url_for('dashboard'))

    return render_template('edit_pharmacy.html', form=form)

# Delete Pharmacy
@app.route('/delete_pharmacy/<string:id>', methods=['POST'])
@is_logged_in
def delete_pharmacy(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Execute
    cur.execute("DELETE FROM pharmacies WHERE id = %s", [id])

    # Commit to DB
    mysql.connection.commit()

    #Close connection
    cur.close()

    flash('Pharmacy Deleted', 'success')

    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.secret_key='secret360'
    app.run(debug=True)
