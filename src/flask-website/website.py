from flask import Flask, render_template, request, redirect, url_for, flash, abort
import json
import urllib.request
import urllib.error

app = Flask(__name__)
app.secret_key = "dev-secret"
API_BASE_URL = "http://localhost:5000"

TYPE_INFO = {
    "ws": {
        "title": "Serveurs Web",
        "description": "Liste et gestion de la configuration des serveurs Web.",
        "fields": [
            ("server_name", "Nom de serveur"),
            ("root_path", "Chemin racine"),
        ],
    },
    "rp": {
        "title": "Reverse Proxies",
        "description": "Liste et gestion de la configuration des reverse proxy.",
        "fields": [
            ("upstream_name", "Nom de l'upstream"),
            ("backend_servers", "Serveurs backend (séparés par des virgules)"),
        ],
    },
    "lb": {
        "title": "Load Balancers",
        "description": "Liste et gestion de la configuration des load balancers.",
        "fields": [
            ("ip_bind", "IP de liaison"),
            ("pass", "URL de destination"),
        ],
    },
}


def api_request(path, method="GET", payload=None):
    url = f"{API_BASE_URL}{path}"
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request_obj = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request_obj) as response:
            body = response.read().decode("utf-8")
            if body:
                return json.loads(body)
            return None
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        message = error.read().decode("utf-8")
        raise RuntimeError(f"API error {error.code}: {message}")
    except urllib.error.URLError as error:
        raise RuntimeError(f"Impossible de joindre l'API : {error}")


def get_item_list(kind):
    if kind not in TYPE_INFO:
        abort(404)
    items = api_request(f"/config/{kind}")
    if items is None:
        return []
    return items


def get_item(kind, item_id):
    if kind not in TYPE_INFO:
        abort(404)
    item = api_request(f"/config/{kind}/{item_id}")
    if item is None:
        abort(404)
    return item


def render_nginx_config(kind, item):
    if kind == "ws":
        return (
            "http {\n"
            "    server {\n"
            f"        server_name {item['server_name']};\n"
            f"        root {item['root_path']};\n\n"
            "        location / {\n"
            "            index index.html index.htm;\n"
            "        }\n\n"
            "        error_page 404 403 500 503 /error-page.html;\n"
            "        location = /error-page.html {\n"
            "            root /var/www/error;\n"
            "            internal;\n"
            "        }\n"
            "    }\n"
            "}"
        )
    if kind == "rp":
        backends = "\n            ".join(f"server {host};" for host in item["backend_servers"])
        return (
            "http {\n"
            "    upstream backend {\n"
            f"        {backends}\n"
            "    }\n\n"
            "    server {\n"
            "        location / {\n"
            "            proxy_pass http://backend;\n"
            "        }\n"
            "    }\n"
            "}"
        )
    if kind == "lb":
        return (
            "http {\n"
            "    server {\n"
            f"        location / {{\n"
            f"            proxy_bind {item['ip_bind']};\n"
            f"            proxy_pass {item['pass']};\n"
            "        }\n"
            "    }\n"
            "}"
        )
    return ""


@app.route("/")
def start():
    return render_template("start.html")


@app.route("/<kind>")
def list_items(kind):
    if kind not in TYPE_INFO:
        abort(404)
    info = TYPE_INFO[kind]
    items = get_item_list(kind)
    return render_template(
        "list.html",
        title=info["title"],
        description=info["description"],
        items=items,
        columns=info["fields"],
        kind=kind,
    )


@app.route("/<kind>/create", methods=["GET", "POST"])
def create_item(kind):
    if kind not in TYPE_INFO:
        abort(404)
    info = TYPE_INFO[kind]
    if request.method == "POST":
        payload = {"name": request.form["name"]}
        for field, _label in info["fields"]:
            value = request.form.get(field, "").strip()
            if not value:
                flash(f"Le champ {field} est requis.", "danger")
                return render_template("form.html", title=f"Ajouter {info['title']}", description=info["description"], fields=info["fields"], kind=kind)
            if field == "backend_servers":
                value = [server.strip() for server in value.split(",") if server.strip()]
            payload[field] = value
        api_request(f"/config/{kind}", method="POST", payload=payload)
        return redirect(url_for("list_items", kind=kind))

    return render_template(
        "form.html",
        title=f"Ajouter {info['title']}",
        description=info["description"],
        fields=info["fields"],
        kind=kind,
    )


@app.route("/<kind>/<int:item_id>")
def show_item(kind, item_id):
    if kind not in TYPE_INFO:
        abort(404)
    info = TYPE_INFO[kind]
    item = get_item(kind, item_id)
    nginx_config = render_nginx_config(kind, item)
    return render_template(
        "detail.html",
        title=f"{info['title']} / {item['name']}",
        description=info["description"],
        item=item,
        columns=info["fields"],
        kind=kind,
        nginx_config=nginx_config,
    )


@app.route("/<kind>/<int:item_id>/delete", methods=["POST"])
def delete_item(kind, item_id):
    if kind not in TYPE_INFO:
        abort(404)
    api_request(f"/config/{kind}/{item_id}", method="DELETE")
    return redirect(url_for("list_items", kind=kind))
    