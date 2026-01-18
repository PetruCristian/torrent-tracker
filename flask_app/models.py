from database import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    role = db.Column(db.String(20), default='normal')  # visitor, normal, uploader, admin
    email = db.Column(db.String(120), unique=True, nullable=False)

    # torrents = db.relationship('Torrent', backref='uploader', lazy=True)
    # comments = db.relationship('Comment', backref='author', lazy=True)

class Torrent(db.Model):
    __tablename__ = 'torrents'
    id = db.Column(db.Integer, primary_key=True)
    info_hash = db.Column(db.String(40), unique=True, nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)

    # File and piece information
    file_size = db.Column(db.BigInteger, nullable=False)  # Total size in bytes
    piece_length = db.Column(db.Integer, nullable=False)  # Length of each piece
    pieces = db.Column(db.JSON, nullable=False)  # Array of piece hashes (SHA-1)

    # Files within torrent (for multi-file torrents)
    files = db.Column(db.JSON, nullable=True)  # Array of {path, length, hash}

    # Swarm information
    seeders = db.Column(db.Integer, default=0)
    leechers = db.Column(db.Integer, default=0)
    completed = db.Column(db.Integer, default=0)

    # Metadata
    # uploader_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    uploader_id = db.Column(db.Integer, default=1, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # comments = db.relationship('Comment', backref='torrent', lazy=True, cascade='all, delete-orphan')

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    # torrent_id = db.Column(db.Integer, db.ForeignKey('torrents.id'), nullable=False)
    torrent_id = db.Column(db.Integer, default=1, nullable=False)
    # user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user_id = db.Column(db.Integer, default=1, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)