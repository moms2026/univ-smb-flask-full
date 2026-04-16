# Démarrage

Connexion à Gitpod :

[![Open in Gitpod](https://gitpod.io/button/open-in-gitpod.svg)](https://gitpod.io/#https://github.com/CHANGE_ME/univ-smb-flask-full)

# Sites

Démarrage du Site Web API :

`cd src/flask-api/ && flask --app api run -p 5000`

Démarrage du Site Web WebSite :

`cd src/flask-website/ && flask --app website run -p 5001`

L'application WebSite appelle ensuite l'API en HTTP sur `http://localhost:5000` pour charger et modifier les données JSON.

# Fonctionnalités

## Authentification
- Page de connexion obligatoire avant d'accéder au site
- Identifiants de test : 
  - **Utilisateur** : admin / admin123
  - **Utilisateur** : user / user123
- Bouton de déconnexion dans la barre de navigation

## Validation des formulaires
- Validation obligatoire des champs requis (nom, détails spécifiques)
- Messages d'erreur détaillés en cas de saisie invalide
- Vérification du format des chemins racine (doivent commencer par `/`)
- Vérification du format IP (xxx.xxx.xxx.xxx)
- Vérification des serveurs backend pour les reverse proxy

## Téléchargement des configurations
- Bouton "Télécharger config" sur la page de détail de chaque élément
- Génère automatiquement un fichier `.conf` Nginx
- Nom du fichier incluant type, ID et timestamp
- Prêt à être utilisé directement dans Nginx

# Base de données

## Pour voir l'état du serveur de base de données

`sudo /etc/init.d/mysql status`

## Pour configurer la base de données

`cd manifest/ && chmod +x db.sh`

## Se connecter à la base de données

Le mot de passe est dans le fichier de base de données.

`sudo mysql -u root -p`