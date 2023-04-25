from flask import Blueprint, render_template, redirect, url_for, request, flash
from . import db
from .models import User
from .helper_funcs import author_normalize
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

auth = Blueprint('auth', __name__)


@auth.route('/login',methods=["GET","POST"])
def login():
    if request.method == 'POST':
        emailuser = request.form.get('emailuser')
        pwd = request.form.get('password')
        if not emailuser or not pwd:
            flash('Enter an email and a password', category='error')

        if "@" in emailuser:
            emailuser = emailuser.lower()
            user = User.query.filter_by(email=emailuser).first()
        else:
            emailuser = emailuser.upper()
            user = User.query.filter_by(username=emailuser).first()

        if user:
            if check_password_hash(user.password, pwd):
                flash('Successfully logged in as '+emailuser)
                login_user(user,remember=True)
                return redirect(url_for('views.home'))
            else:
                flash('Password fail, incorrect', category="error")
        else:
            flash('No registered user associated with '+emailuser, category="error")

    return render_template('login.html', user=current_user)


@auth.route('/register',methods=["GET","POST"])
def register():
    if request.method == 'POST':
        email = request.form.get('email').lower()
        username = request.form.get('username').upper()
        pwd1 = request.form.get('password1')
        pwd2 = request.form.get('password2')
        email_exists = User.query.filter_by(email=email).first()
        user_exists = User.query.filter_by(username=username).first()

        if email_exists:
            flash('Email already associated with an account', category="error")
        elif user_exists:
            flash("That Username is already take", category='error')
        elif pwd1 != pwd2:
            flash("Passwords do not match. Passwords are case sensitive.", category='error')
        elif len(username) <=2:
            flash('Username too short',category="error")
        elif "@" in username:
            flash('Symbol @ not allowed in username', category="error")
        elif " " not in username:
            flash("Full name please, with spaces", category='error')
        elif len(pwd1) <= 7:
            flash('Password too short. Minimum length = 8 characters',category="error")
        #elif  fail to reach a real email? authenticatioN?
        elif "@" not in email or len(email) <= 3:
            flash('Email '+email+" invalid", category="error")
        else:
            new_user = User(email=email, 
                            username=author_normalize(username), 
                            password=generate_password_hash(pwd1, method='sha256'))
            db.session.add(new_user)
            db.session.commit()

            login_user(new_user,remember=True)
            flash('User registered successfully')
            return redirect(url_for('views.home'))

    return render_template('register.html', user=current_user)


@auth.route('/logout')
@login_required
def logout():
    print(current_user)
    flash('Successfully logged out from '+current_user.username)
    logout_user()
    return redirect(url_for("views.home"))

