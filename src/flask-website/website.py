from flask import Flask, render_template, request, redirect, url_for, flash, abort, send_file, session
import json
import urllib.request
import urllib.error
import io
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = "dev-secret-change-in-production"
API_BASE_URL = "http://localhost:5000"

# Utilisateurs autorisés (à remplacer par une vraie DB en production)
USERS = {
    "admin": "admin123",
    "user": "user123",
}

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


# ========== AUTHENTIFICATION ==========

def login_required(f):
    """Décorateur pour vérifier l'authentification"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("Vous devez vous connecter.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ========== VALIDATION DES FORMULAIRES ==========

def validate_form_data(kind, data):
    """Valide les données avant création/modification"""
    errors = []
    
    if not data.get("name", "").strip():
        errors.append("Le nom est obligatoire.")
    
    if kind == "ws":
        if not data.get("server_name", "").strip():
            errors.append("Le nom de serveur est obligatoire.")
        if not data.get("root_path", "").strip():
            errors.append("Le chemin racine est obligatoire.")
        if not data.get("root_path", "").startswith("/"):
            errors.append("Le chemin racine doit commencer par /")
    
    if kind == "rp":
        if not data.get("upstream_name", "").strip():
            errors.append("Le nom de l'upstream est obligatoire.")
        backends = data.get("backend_servers", "").strip()
        if not backends:
            errors.append("Au moins un serveur backend est requis.")
    
    if kind == "lb":
        if not data.get("ip_bind", "").strip():
            errors.append("L'IP de liaison est obligatoire.")
        if not data.get("pass", "").strip():
            errors.append("L'URL de destination est obligatoire.")
        # Valider le format IP
        try:
            ip = data.get("ip_bind", "").strip()
            if ip:
                parts = ip.split(".")
                if len(parts) != 4 or not all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
                    errors.append("L'IP est invalide (format: xxx.xxx.xxx.xxx)")
        except:
            errors.append("L'IP est invalide.")
    
    return errors


# ========== API REQUESTS ==========

def api_request(path, method="GET", payload=None):
    """Effectue une requête HTTP vers l'API"""
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
    """Récupère la liste des items d'un type"""
    if kind not in TYPE_INFO:
        abort(404)
    items = api_request(f"/config/{kind}")
    if items is None:
        return []
    return items


def get_item(kind, item_id):
    """Récupère un item spécifique"""
    if kind not in TYPE_INFO:
        abort(404)
    item = api_request(f"/config/{kind}/{item_id}")
    if item is None:
        abort(404)
    return item


def render_nginx_config(kind, item):
    """Génère la configuration Nginx pour un item"""
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


# ========== ROUTES ==========

@app.route("/login", methods=["GET", "POST"])
def login():
    """Page de connexion"""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        
        if not username:
            flash("Le nom d'utilisateur est requis.", "danger")
        elif not password:
            flash("Le mot de passe est requis.", "danger")
        elif username in USERS and USERS[username] == password:
            session["user"] = username
            flash(f"Bienvenue {username}!", "success")
            return redirect(url_for("start"))
        else:
            flash("Nom d'utilisateur ou mot de passe incorrect.", "danger")
    
    return render_template("login.html")


@app.route("/logout")
def logout():
    """Déconnexion"""
    session.pop("user", None)
    flash("Vous avez été déconnecté.", "info")
    return redirect(url_for("login"))


@app.route("/")
def start():
    """Page d'accueil"""
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("start.html", user=session.get("user"))


@app.route("/<kind>")
@login_required
def list_items(kind):
    """Liste les items d'un type"""
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
@login_required
def create_item(kind):
    """Crée un nouvel item"""
    if kind not in TYPE_INFO:
        abort(404)
    info = TYPE_INFO[kind]
    
    if request.method == "POST":
        payload = {"name": request.form.get("name", "").strip()}
        for field, _label in info["fields"]:
            value = request.form.get(field, "").strip()
            if field == "backend_servers":
                value = [server.strip() for server in value.split(",") if server.strip()]
            payload[field] = value
        
        # Validation
        errors = validate_form_data(kind, payload)
        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template(
                "form.html",
                title=f"Ajouter {info['title']}",
                description=info["description"],
                fields=info["fields"],
                kind=kind,
            )
        
        # Envoi à l'API
        try:
            api_request(f"/config/{kind}", method="POST", payload=payload)
            flash(f"{info['title'].rstrip('s')} créé(e) avec succès!", "success")
            return redirect(url_for("list_items", kind=kind))
        except RuntimeError as e:
            flash(f"Erreur API : {str(e)}", "danger")

    return render_template(
        "form.html",
        title=f"Ajouter {info['title']}",
        description=info["description"],
        fields=info["fields"],
        kind=kind,
    )


@app.route("/<kind>/<int:item_id>")
@login_required
def show_item(kind, item_id):
    """Affiche les détails d'un item"""
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
@login_required
def delete_item(kind, item_id):
    """Supprime un item"""
    if kind not in TYPE_INFO:
        abort(404)
    info = TYPE_INFO[kind]
    try:
        api_request(f"/config/{kind}/{item_id}", method="DELETE")
        flash(f"{info['title'].rstrip('s')} supprimé(e) avec succès!", "success")
    except RuntimeError as e:
        flash(f"Erreur lors de la suppression : {str(e)}", "danger")
    return redirect(url_for("list_items", kind=kind))


@app.route("/<kind>/<int:item_id>/download")
@login_required
def download_config(kind, item_id):
    """Télécharge la configuration Nginx d'un item"""
    if kind not in TYPE_INFO:
        abort(404)
    
    item = get_item(kind, item_id)
    nginx_config = render_nginx_config(kind, item)
    
    # Créer un fichier en mémoire
    file_content = nginx_config.encode("utf-8")
    file_obj = io.BytesIO(file_content)
    
    # Générer un nom de fichier
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"nginx-{kind}-{item['id']}-{timestamp}.conf"
    
    return send_file(
        file_obj,
        mimetype="text/plain",
        as_attachment=True,
        download_name=filename
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001)
