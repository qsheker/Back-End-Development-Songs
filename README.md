# Back-End-Development-Songs

Flask and MongoDB REST API built from the official IBM capstone template.

## Environment setup

Python 3.10+ and MongoDB are required. Run `bash bin/setup.sh`, then `source .venv/bin/activate`.

Configure `MONGODB_SERVICE` (default 127.0.0.1), `MONGODB_PORT` (default 27017), and optional `MONGODB_USERNAME` / `MONGODB_PASSWORD`. Alternatively set `MONGODB_URI`. Credentials are never printed or committed.

Run `flask --app app seed-data` once to create the unique ID index and load the 20 course fixtures. This is explicit and idempotent: restarting the app never drops the collection or replaces edited songs.

Run `flask --app app run --port 5002`. For containers use the supplied Dockerfile; OpenShift source-to-image can also detect `app.py` and `requirements.txt`.

## API

- `GET /health`: MongoDB connection health, `{"status":"OK"}`.
- `GET /count`: document count.
- `GET /song`: `{"songs":[...]}` including BSON converted to extended JSON.
- `GET /song/<id>`: one song or 404.
- `POST /song`: JSON with integer `id`, `title`, `lyrics`; 201 on creation, 302 for duplicates as required by the exercise.
- `PUT /song/<id>`: 201 when changed (course convention), 200 when unchanged, 404 when missing. IDs cannot change.
- `DELETE /song/<id>`: 204, or 404 when missing.

Invalid requests return 400/415; database failures return 503 without exposing credentials. This public educational API contains synthetic course data only and has no production authentication layer.
