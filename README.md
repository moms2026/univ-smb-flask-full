# Démarrage

Connexion à Gitpod :

[![Open in Gitpod](https://gitpod.io/button/open-in-gitpod.svg)](https://gitpod.io/#https://github.com/CHANGE_ME/univ-smb-flask-full)

# Sites

Démarrage du Site Web API :

`cd src/flask-api/ && flask --app api run -p 5000`

Démarrage du Site Web WebSite :

`cd src/flask-website/ && flask --app website run -p 5001`

L'application WebWebsite appelle ensuite l'API en HTTP sur `http://localhost:5000` pour charger et modifier les données JSON.

# Base de données

## Pour voir l'état du serveur de base de données

`sudo /etc/init.d/mysql status`

## Pour configurer la base de données

`cd manifest/ && chmod +x db.sh`

## Se connecter à la base de données

Le mot de passe est dans le fichier de base de données.

`sudo mysql -u root -p`