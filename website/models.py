from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func


# similarities table, but using follower many-to-many structure
follows = db.Table(
    "follows",
    db.Column("follower_id", db.Integer, db.ForeignKey("user.id")),
    db.Column("followed_id", db.Integer, db.ForeignKey("user.id"))
)


class User(db.Model, UserMixin):
    # Users sql_alchemy table
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), unique=True)
    username = db.Column(db.String(250), unique=True)
    password = db.Column(db.String(250))
    # strikes  = db.Column(db.Integer) # 3 matches in a row, display FAIL
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())
    quotes = db.relationship('Quote',
                             backref='user',
                             passive_deletes=True)
    likes = db.relationship('Like',
                            backref='user',
                            passive_deletes=True)
    followers = db.relationship("User",
                                secondary=follows,
                                primaryjoin=(follows.c.follower_id == id),
                                secondaryjoin=(follows.c.followed_id == id),
                                backref=db.backref("follows", lazy="dynamic"),
                                lazy="dynamic"
                                )


class Quote(db.Model):
    # Quotes Sql_alchemy table
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, unique=True, nullable=False)
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())
    author = db.Column(db.Integer,
                       db.ForeignKey('user.id', ondelete="CASCADE"),
                       nullable=False)
    likes = db.relationship('Like', backref='quote', passive_deletes=True)


class Like(db.Model):
    # Likes SQL_Alchemy Table
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.Integer,
                       db.ForeignKey('user.id', ondelete="CASCADE"),
                       nullable=False)
    quote_id = db.Column(db.Integer,
                         db.ForeignKey('quote.id', ondelete="CASCADE"),
                         nullable=False)
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())


class Streak(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.Integer,
                       db.ForeignKey('user.id', ondelete="CASCADE"),
                       nullable=False)
    strikes = db.Column(db.Integer)
    streak = db.Column(db.Integer)
