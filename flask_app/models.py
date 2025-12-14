from database import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    role = db.Column(db.String(20), default='normal')  # visitor, normal, uploader, admin
    email = db.Column(db.String(120), unique=True, nullable=False)

class Torrent(db.Model):
    __tablename__ = 'torrents'
    id = db.Column(db.Integer, primary_key=True)
    info_hash = db.Column(db.String(40), unique=True, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    comments = db.relationship('Comment', backref='torrent', lazy=True)

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    torrent_id = db.Column(db.Integer, db.ForeignKey('torrents.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))