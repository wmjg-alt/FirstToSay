from . import db, es
from flask_login import UserMixin
from sqlalchemy.sql import func

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), unique=True)
    username = db.Column(db.String(250), unique=True)
    password = db.Column(db.String(250))
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())
    quotes= db.relationship('Quote', backref ='user', passive_deletes=True)
    likes= db.relationship('Like', backref ='user', passive_deletes=True)

class Quote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text= db.Column(db.Text, unique=True, nullable=False)
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())
    author = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    likes= db.relationship('Like', backref ='quote', passive_deletes=True)

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    quote_id = db.Column(db.Integer, db.ForeignKey('quote.id', ondelete="CASCADE"), nullable=False)
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())
