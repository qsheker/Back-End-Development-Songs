"""MongoDB-backed Songs REST service for the capstone."""
import json
import os
from pathlib import Path
from urllib.parse import quote_plus

from bson import json_util
from flask import abort, jsonify, request
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError
from . import app

host = os.environ.get('MONGODB_SERVICE', '127.0.0.1')
port = os.environ.get('MONGODB_PORT', '27017')
username = os.environ.get('MONGODB_USERNAME')
password = os.environ.get('MONGODB_PASSWORD')
credentials = f'{quote_plus(username)}:{quote_plus(password)}@' if username and password else ''
uri = os.environ.get('MONGODB_URI') or f'mongodb://{credentials}{host}:{port}/?authSource=admin'
client = MongoClient(uri, serverSelectionTimeoutMS=5000)
db = client[os.environ.get('MONGODB_DATABASE', 'songs')]


def parse_json(value):
    return json.loads(json_util.dumps(value))


@app.cli.command('seed-data')
def seed_data():
    """Load missing course fixtures explicitly; never delete or replace user data."""
    db.songs.create_index('id', unique=True)
    with (Path(__file__).parent / 'data' / 'songs.json').open() as source:
        for song in json.load(source):
            db.songs.update_one({'id': song['id']}, {'$setOnInsert': song}, upsert=True)
    print(f'Songs ready: {db.songs.count_documents({})}')


def song_payload(expected_id=None):
    value = request.get_json()
    if not isinstance(value, dict):
        abort(400, description='A JSON object is required')
    song_id = value.get('id', expected_id)
    if type(song_id) is not int or song_id < 1:
        abort(400, description='id must be a positive integer')
    if expected_id is not None and song_id != expected_id:
        abort(400, description='Body id must match the URL id')
    if any(not isinstance(value.get(field), str) or not value[field].strip() for field in ('title', 'lyrics')):
        abort(400, description='title and lyrics must be nonempty strings')
    return {'id': song_id, 'title': value['title'], 'lyrics': value['lyrics']}


@app.errorhandler(PyMongoError)
def database_unavailable(error):
    app.logger.error('MongoDB operation failed: %s', type(error).__name__)
    return {'message': 'Database temporarily unavailable'}, 503


@app.get('/health')
def health():
    client.admin.command('ping')
    return jsonify(status='OK'), 200


@app.get('/count')
def count():
    return {'count': db.songs.count_documents({})}, 200


@app.get('/song')
def songs():
    return {'songs': parse_json(list(db.songs.find({}).sort('id', 1)))}, 200


@app.get('/song/<int:id>')
def get_song_by_id(id):
    song = db.songs.find_one({'id': id})
    if song is None:
        return {'message': f'song with id {id} not found'}, 404
    return parse_json(song), 200


@app.post('/song')
def create_song():
    song = song_payload()
    if db.songs.find_one({'id': song['id']}):
        return {'Message': f"song with id {song['id']} already present"}, 302
    try:
        result = db.songs.insert_one(song)
    except DuplicateKeyError:
        return {'Message': f"song with id {song['id']} already present"}, 302
    return {'inserted id': parse_json(result.inserted_id)}, 201


@app.put('/song/<int:id>')
def update_song(id):
    song = song_payload(id)
    result = db.songs.update_one({'id': id}, {'$set': song})
    if not result.matched_count:
        return {'message': 'song not found'}, 404
    if not result.modified_count:
        return {'message': 'song found, but nothing updated'}, 200
    return parse_json(db.songs.find_one({'id': id})), 201


@app.delete('/song/<int:id>')
def delete_song(id):
    if not db.songs.delete_one({'id': id}).deleted_count:
        return {'message': 'song not found'}, 404
    return '', 204
