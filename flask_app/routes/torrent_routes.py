from flask import Blueprint, request, jsonify, send_file
from models import User, Torrent, Comment, db
from services.auth_service import require_roles, get_keycloak_user_id, get_role_representation
from services.redis_service import rate_limit
from services.elastic_service import index_torrent, search_torrents_elasticsearch, delete_torrent_index, update_torrent_swarm_info
from config import Config
import bencodepy
import hashlib
from datetime import datetime, timedelta
import struct
import random
import io

torrent_bp = Blueprint("torrents", __name__)

@torrent_bp.route("/torrents", methods=["POST"])
@rate_limit()
@require_roles("admin", "uploader")
def upload_torrent():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No torrent file provided"}), 400

        torrent_file = request.files['file']
        description = request.form.get('description', '')

        if torrent_file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        if not torrent_file.filename.endswith('.torrent'):
            return jsonify({"error": "File must be a .torrent file"}), 400

        # Parse torrent file
        torrent_data = bencodepy.decode(torrent_file.read())

        # Extract info_hash
        info_bytes = bencodepy.encode(torrent_data[b'info'])
        info_hash = hashlib.sha1(info_bytes).hexdigest()

        # Check if torrent already exists
        if Torrent.query.filter_by(info_hash=info_hash).first():
            return jsonify({"error": "Torrent already exists"}), 409

        # Extract torrent information
        info = torrent_data[b'info']
        filename = info[b'name'].decode('utf-8')
        piece_length = info[b'piece length']
        pieces = info[b'pieces']  # Raw bytes of concatenated SHA-1 hashes

        # Convert pieces to list of hex strings
        pieces_list = [pieces[i:i+20].hex() for i in range(0, len(pieces), 20)]

        # Calculate total file size
        file_size = 0
        files_list = []

        if b'files' in info:
            # Multi-file torrent
            for file_info in info[b'files']:
                file_path = '/'.join([p.decode('utf-8') for p in file_info[b'path']])
                file_length = file_info[b'length']
                file_size += file_length
                files_list.append({
                    "path": file_path,
                    "length": file_length
                })
        else:
            # Single-file torrent
            file_size = info[b'length']
            files_list = None

        # Get current user (implement based on your auth setup)
        user_id = 1
        if not user_id:
            return jsonify({"error": "Authentication failed"}), 401

        # Create torrent record
        new_torrent = Torrent(
            info_hash=info_hash,
            filename=filename,
            description=description,
            file_size=file_size,
            piece_length=piece_length,
            pieces=pieces_list,
            files=files_list if files_list else None,
            uploader_id=user_id,
            seeders=0,
            leechers=0,
            completed=0
        )

        db.session.add(new_torrent)
        db.session.commit()

        # Index in Elasticsearch
        index_torrent(new_torrent)

        return jsonify({
            "message": "Torrent uploaded successfully",
            "torrent_id": new_torrent.id,
            "info_hash": info_hash,
            "filename": filename,
            "file_size": file_size,
            "pieces_count": len(pieces_list)
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to upload torrent", "details": str(e)}), 500

@torrent_bp.route("/search", methods=["GET"])
@rate_limit()
@require_roles("admin", "uploader", "normal")
def search():
    query = request.args.get("q", "").strip()
    limit = request.args.get("limit", 50, type=int)

    if not query or len(query) < 2:
        return jsonify({"error": "Search query must be at least 2 characters"}), 400

    if limit > 200:
        limit = 200  # Cap the limit

    try:
        # Try Elasticsearch first
        es_results = search_torrents_elasticsearch(query, limit)

        if es_results:
            return jsonify({
                "query": query,
                "count": len(es_results),
                "results": es_results,
                "source": "elasticsearch"
            }), 200

        # Fallback to PostgreSQL
        torrents = Torrent.query.filter(
            (Torrent.filename.ilike(f"%{query}%")) |
            (Torrent.description.ilike(f"%{query}%")) |
            (Torrent.info_hash.ilike(f"%{query}%"))
        ).limit(limit).all()

        results = [{
            "id": t.id,
            "filename": t.filename,
            "description": t.description,
            "info_hash": t.info_hash,
            "file_size": t.file_size,
            "seeders": t.seeders,
            "leechers": t.leechers,
            "completed": t.completed,
            "created_at": t.created_at.isoformat()
        } for t in torrents]

        return jsonify({
            "query": query,
            "count": len(results),
            "results": results,
            "source": "postgresql"
        }), 200

    except Exception as e:
        return jsonify({"error": "Search failed", "details": str(e)}), 500

@torrent_bp.route("/torrents/<int:torrent_id>", methods=["GET"])
@rate_limit()
@require_roles("admin", "uploader", "normal")
def get_torrent_details(torrent_id):
    try:
        torrent = Torrent.query.get(torrent_id)

        if not torrent:
            return jsonify({"error": "Torrent not found"}), 404

        # comments = [{
        #     "id": c.id,
        #     "content": c.content,
        #     "author": c.author.username,
        #     "created_at": c.created_at.isoformat()
        # } for c in torrent.comments]

        return jsonify({
            "id": torrent.id,
            "filename": torrent.filename,
            "description": torrent.description,
            "info_hash": torrent.info_hash,
            "file_size": torrent.file_size,
            "piece_length": torrent.piece_length,
            "pieces_count": len(torrent.pieces),
            "files": torrent.files,
            "seeders": torrent.seeders,
            "leechers": torrent.leechers,
            "completed": torrent.completed,
            "uploader": torrent.uploader.username,
            "created_at": torrent.created_at.isoformat(),
            # "comments": comments
        }), 200

    except Exception as e:
        return jsonify({"error": "Failed to fetch torrent", "details": str(e)}), 500

@torrent_bp.route("/torrents/<int:torrent_id>", methods=["DELETE"])
@rate_limit()
@require_roles("admin")
def delete_torrent(torrent_id):
    try:
        torrent = Torrent.query.get(torrent_id)

        if not torrent:
            return jsonify({"error": "Torrent not found"}), 404

        delete_torrent_index(torrent.id)

        # Comment.query.filter_by(torrent_id=torrent_id).delete()

        db.session.delete(torrent)
        db.session.commit()

        return jsonify({
            "message": "Torrent deleted successfully",
            "torrent_id": torrent_id,
            "filename": torrent.filename
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to delete torrent", "details": str(e)}), 500

@torrent_bp.route("/torrents/<int:torrent_id>/download", methods=["GET"])
@rate_limit()
@require_roles("admin", "uploader", "normal")
def download_torrent(torrent_id):
    try:
        torrent = Torrent.query.get(torrent_id)

        if not torrent:
            return jsonify({"error": "Torrent not found"}), 404

        info = {
            b'name': torrent.filename.encode('utf-8'),
            b'piece length': torrent.piece_length,
            b'pieces': b''.join(bytes.fromhex(piece) for piece in torrent.pieces)
        }

        if torrent.files:
            # Multi-file torrent
            files = []
            for file_info in torrent.files:
                file_path = file_info.get('path', '').split('/')
                files.append({
                    b'path': [p.encode('utf-8') for p in file_path],
                    b'length': file_info.get('length', 0)
                })
            info[b'files'] = files
        else:
            # Single-file torrent
            info[b'length'] = torrent.file_size

        torrent_dict = {
            b'announce': b'http://localhost/announce',
            b'info': info,
            b'creation date': int(torrent.created_at.timestamp()),
            b'created by': b'torrent-tracker'
        }

        torrent_data = bencodepy.encode(torrent_dict)

        buffer = io.BytesIO(torrent_data)
        buffer.seek(0)

        return send_file(
            buffer,
            mimetype='application/x-bencoded',
            as_attachment=True,
            download_name=f"{torrent.filename}.torrent"
        )

    except Exception as e:
        return jsonify({"error": "Failed to download torrent", "details": str(e)}), 500

@torrent_bp.route("/announce", methods=["GET"])
def announce():
    return jsonify({"error": "Not relevant to the project. (damblaua mea pt cand am timp liber)"}), 418