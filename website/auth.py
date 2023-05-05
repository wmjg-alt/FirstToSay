from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from string import ascii_letters, digits, punctuation, whitespace
from time import sleep

from . import db
from .models import User
from .helper_funcs import author_normalize

# minimize to utf8
allowed_chars = set(ascii_letters + digits + punctuation + whitespace)

auth = Blueprint('auth', __name__)


@auth.route('/login', methods=["GET", "POST"])
def login():
    ''' route handling for login, lots of user rules
        POST -> credential checking
        GET - > display login page
    '''
    if request.method == 'POST':
        emailuser = request.form.get('emailuser')
        pwd = request.form.get('password')
        if not emailuser or not pwd:
            flash('Enter an email/username and a password', category='error')
        else:
            if "@" in emailuser:
                emailuser = emailuser.lower()
                user = User.query.filter_by(email=emailuser).first()
            else:
                emailuser = emailuser.lower()
                user = User.query.filter_by(username=emailuser).first()
            print(emailuser, user)

            if user:
                if check_password_hash(user.password, pwd):
                    logged = login_user(user,
                                        remember=True,
                                        fresh=True,
                                        force=True)
                    sleep(0.25)
                    if logged:
                        flash('Successfully logged in as '+emailuser,
                              category='success')
                        return redirect(url_for('views.home'))
                    else:
                        flash('something went wrong logging you in',
                              category='error')
                else:
                    flash('Password fail, incorrect', category="error")
            else:
                flash('No registered user associated with '+emailuser,
                      category="error")

    return render_template('login.html', user=current_user)


@auth.route('/register', methods=["GET", "POST"])
def register():
    ''' route handling for registering a user
        lots of user input rules
    '''
    if request.method == 'POST':
        email = request.form.get('email').lower()
        username = request.form.get('username').upper()
        pwd1 = request.form.get('password1')
        pwd2 = request.form.get('password2')
        email_exists = User.query.filter_by(email=email).first()
        user_exists = User.query.filter_by(username=username).first()

        if email_exists:
            flash('Email already associated with an account',
                  category="error")
        elif user_exists:
            flash("That Name is already taken; add something",
                  category='error')
        elif pwd1 != pwd2:
            flash("Passwords do not match. Passwords are case sensitive.",
                  category='error')
        elif len(username) <= 2:
            flash('Thats not a name',
                  category="error")
        elif "@" in username:
            flash('No @s in usernames, thanks',
                  category="error")
        elif not not (set(username) - allowed_chars):
            flash('Symbols not allowed in username', category="error")
        elif len(pwd1) <= 7:
            flash('Password too short. Minimum length = 8 characters',
                  category="error")
        # elif  fail to reach a real email? authenticatioN?
        elif "@" not in email or len(email) <= 5:
            flash('Email '+email+" invalid",
                  category="error")
        else:
            new_user = User(email=email,
                            username=author_normalize(username),
                            password=generate_password_hash(pwd1,
                                                            method='sha256'))
            db.session.add(new_user)
            db.session.commit()

            sleep(0.25)
            logged = login_user(new_user,
                                remember=True,
                                fresh=True,
                                force=True)

            if logged:
                flash('User registered successfully', category='success')
                return redirect(url_for('views.home'))
            else:
                flash('something went wrong logging you in', category='error')

    return render_template('register.html', user=current_user)


@auth.route('/logout')
@login_required
def logout():
    ''' logout handling, returning home -> new user login'''
    print(current_user)
    flash('Successfully logged out from '+current_user.username)
    logout_user()
    return redirect(url_for("views.home"))
