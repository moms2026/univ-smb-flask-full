from flask import Flask, jsonify, request, abort
import json
import os

app = Flask(__name__)
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

TYPE_CONFIG = {
    "ws": {
        "file": "webserver.json",
        "fields": ["name", "server_name", "root_path"],
    },
    "rp": {
        "file": "reverseproxy.json",
        "fields": ["name", "upstream_name", "backend_servers"],
    },
    "lb": {
        "file": "loadbalancer.json",
        "fields": ["name", "ip_bind", "pass"],
    },
}


def get_data_path(kind):
    return os.path.join(DATA_DIR, TYPE_CONFIG[kind]["file"])


def load_items(kind):
    path = get_data_path(kind)
    if not os.path.exists(path):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_items(kind, items):
    path = get_data_path(kind)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


def normalize_payload(kind, payload):
    output = {}
    for key in TYPE_CONFIG[kind]["fields"]:
        if key not in payload:
            abort(400, description=f"Champ manquant : {key}")
        value = payload[key]
        if key == "backend_servers":
            if isinstance(value, str):
                value = [server.strip() for server in value.split(",") if server.strip()]
            elif not isinstance(value, list):
                abort(400, description="backend_servers doit être une liste ou une chaîne séparée par des virgules")
        output[key] = value
    return output


@app.route("/config/<kind>", methods=["GET", "POST"])
def config_collection(kind):
    if kind not in TYPE_CONFIG:
        abort(404)

    if request.method == "GET":
        return jsonify(load_items(kind))

    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Requête JSON attendue"}), 400

    items = load_items(kind)
    next_id = max((item.get("id", 0) for item in items), default=0) + 1
    item = normalize_payload(kind, payload)
    item["id"] = next_id
    items.append(item)
    save_items(kind, items)
    return jsonify(item), 201


@app.route("/config/<kind>/<int:item_id>", methods=["GET", "DELETE"])
def config_item(kind, item_id):
    if kind not in TYPE_CONFIG:
        abort(404)

    items = load_items(kind)
    item = next((entry for entry in items if entry.get("id") == item_id), None)
    if item is None:
        abort(404)

    if request.method == "GET":
        return jsonify(item)

    items = [entry for entry in items if entry.get("id") != item_id]
    save_items(kind, items)
    return jsonify({"deleted": item_id})


@app.route("/")
def root():
    return jsonify({"message": "API de configuration disponible", "endpoints": ["/config/ws", "/config/rp", "/config/lb"]})
