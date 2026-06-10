# 🌐 RTVM-LAB

> ⚠️ **AVERTISSEMENT CONFIGURATION DNS :** Par défaut, l'infrastructure de ce laboratoire virtuel est configurée pour utiliser le serveur DNS de l'Université de Lorraine (`193.50.27.27`) comme redirecteur primaire (forwarder). Si cette machine virtuelle est déployée dans un autre environnement de test, sur un autre réseau académique ou pour d'autres besoins spécifiques, il est impératif de modifier cette adresse IP dans le script `menu.sh` (variable `DNS_UL`) afin d'éviter tout blocage de la résolution de noms ou perte de connectivité externe.

## Présentation du projet
RTVM-LAB est un environnement de test virtuel développé dans le cadre de la formation BUT Réseaux et Télécommunications en deuxième année. L'objectif de ce projet est de fournir une machine virtuelle (VM) autonome, conçue pour simuler une infrastructure réseau d'entreprise complète. Ce système est particulièrement adapté pour la mise en situation lors de travaux pratiques ou d'événements (hackathon par exemple).

### Équipe du projet
La conception et la réalisation de cet environnement ont été réparties comme suit :
* **Augustin de Vivar** : Architecture système, développement du panel d'administration web (Python/Flask), développement des scripts de déploiement (Bash) et de la page de template web (HTML/CSS).
* **Maxence Kroetz** : Conception de la maquette réseau initiale, exécution des phases de tests et validation de la stabilité globale de l'environnement.

## Topologie et Services Inclus
La solution repose sur l'utilisation de conteneurs Docker pour virtualiser les services suivants :
* 🌐 **Serveur Web** (Apache httpd)
* 🗺️ **Serveur DNS** (BIND9) avec gestion automatique des zones
* 📧 **Serveur SMTP** (Docker Mailserver)
* 📁 **Serveur FTP** (vsftpd)
* ✉️ **Interface Webmail** (Roundcube)

Un panel d'administration est inclus pour superviser l'état des conteneurs, modifier le routage IP et injecter des enregistrements DNS.

## 🚀 Démarrage Rapide (Version Plug-and-Play)
Pour les utilisateurs souhaitant tester l'environnement immédiatement sans passer par la phase d'installation complète, une image pré-configurée de la machine virtuelle est disponible au téléchargement.

1. Télécharger l'appliance virtuelle complète : **[Lien vers la Release ou le Cloud pour télécharger le fichier .ova]**
2. Ouvrir VirtualBox, aller dans **Fichier** > **Importer un appareil virtuel**.
3. Sélectionner le fichier `.ova` téléchargé.
4. Dans les paramètres de la carte réseau, s'assurer que le mode est sur **Accès par pont** et que le mode promiscuité est sur **Allow All**.
5. Démarrer la VM. Le système s'initialisera automatiquement sur l'interface de sélection réseau de RTVM-LAB.

## Fonctionnalités des Composants

### 1. Script d'initialisation et d'orchestration (`menu.sh`)
Le script Bash centralise la gestion de l'infrastructure avant le démarrage de la session utilisateur :
* **Interface graphique TUI (Terminal User Interface)** : Intégration d'un menu interactif via `whiptail` permettant de sélectionner instantanément un réseau parmi 15 profils d'entreprises prédéfinis (Réseaux de `192.168.1.0/24` à `192.168.15.0/24` et domaines associés de `a.net` à `o.net`).
* **Système de sauvegarde et restauration** : Archivage automatique et transparent de l'état de l'entreprise précédente (fichiers du site web, enregistrements DNS personnalisés et volumes de messagerie) vers le répertoire `/opt/rtvm-lab/archives/`. Lors du basculement, un prompt interactif doté d'un compte à rebours de 10 secondes permet à l'étudiant de réinitialiser sélectivement ou de restaurer ses configurations antérieures.
* **Configuration dynamique de la couche réseau** : Nettoyage automatisé des anciennes configurations d'interfaces et instanciation de 6 alias IP consécutifs sur la carte réseau physique pour isoler les services de la topologie.
* **Moteur de routage et DNS amont** : Configuration à chaud de la passerelle par défaut et liaison dynamique des mécanismes de résolution vers les serveurs DNS de l'Université de Lorraine et les redirecteurs secondaires.
* **Moteur de templating d'infrastructure** : Injection dynamique des variables d'environnement dans le fichier de configuration `.env` et modification automatique en arrière-plan du code source HTML de la page d'accueil (`index.html`) pour adapter la charte graphique et les hyperliens à l'entreprise choisie.
* **Génération de la matrice DNS de laboratoire** : Écriture automatisée du fichier de zone locale et provisionnement automatique de 14 fichiers de zones maîtres externes pour simuler la communication et la résolution mutuelle entre toutes les entreprises du réseau.
* **Gestionnaire de résilience Docker (Algorithme de récupération à 3 niveaux)** : En cas d'anomalie ou de blocage du moteur Docker, le script déploie une logique de tolérance aux pannes :
  * *Niveau 1* : Élagage (Prune) des conteneurs et réseaux orphelins.
  * *Niveau 2* : Redémarrage à chaud du démon et des sockets du moteur Docker.
  * *Niveau 3* : Hard Reset (réinitialisation d'usine complète des répertoires `/var/lib/docker`) suivi d'un rapatriement propre des images.

### 2. Console d'administration web (`admin-panel.py`)
Développée en Python avec le micro-framework Flask, cette interface offre un contrôle granulaire de l'environnement depuis un navigateur web (port `5000`) :
* **Tableau de bord réseau temps réel** : Extraction et affichage dynamique des informations de l'hôte (interface active, adresse IPv4 courante, passerelle active et serveurs DNS configurés).
* **Supervision et contrôle des services** : Monitoring de l'état opérationnel des conteneurs Docker avec possibilité d'initier des actions d'arrêt (`stop`) ou de démarrage (`start`) à la volée.
* **Gestion dynamique des adresses IP** : Interface de modification de l'adressage des services entraînant la mise à jour du fichier d'environnement `.env`, le flush et la réattribution des alias réseaux système à chaud (`ip addr`), suivie de la re-création transparente des conteneurs cibles.
* **Contrôleur de zone BIND9 programmable** :
  * *Périmètre local* : Formulaire d'injection d'enregistrements DNS (`A`, `AAAA`, `CNAME`, `MX`, `TXT`) dans le fichier `db.zone` with recalcul et incrémentation automatique du numéro de série (Serial) de la zone.
  * *Périmètre externe* : Création dynamique à la volée de fichiers de zones maîtres dédiés pour les requêtes hors du domaine par défaut et mise à jour des inclusions de fichiers dans `named.conf.local`.
* **Sécurité des entrées** : Filtrage systématique par expressions régulières (Regex) des données soumises par les formulaires pour interdire l'injection de caractères spéciaux et protéger l'intégrité du système de fichiers de la VM.

---

## Prérequis de la Machine Virtuelle
* Système d'exploitation : Ubuntu Server 26.04
* Processeur : 2 cœurs
* Mémoire : 2048 Mo
* Stockage : Minimum 20 Go
* Paramètre de la carte réseau : Accès par pont (Promiscuous mode : Allow All)

*Important : Lors de l'installation de l'OS, le compte administrateur créé doit impérativement se nommer `master`.*

## Procédure d'installation détaillée

### Étape 0 : Configuration de la VM et installation de l'OS
Cette étape décrit la création initiale de la machine virtuelle sur l'hyperviseur (ex: VirtualBox) ainsi que le provisionnement du système d'exploitation de base.

1. **Création de la machine virtuelle :**
   * Initier la création d'une nouvelle VM avec le système Linux de votre choix (Ubuntu Server 26.04 requis).
2. **Allocation des prérequis matériels minimaux :**
   * **Processeur** : 2 cœurs
   * **Mémoire** : 2048 Mo
   * **Stockage** : Minimum 20 Go
3. **Configuration rigoureuse des paramètres de la carte réseau :**
   * **Mode d'accès (Attached to)** : Accès par pont (Bridged Adapter)
   * **Nom (Name)** : Sélectionner explicitement le nom de la carte réseau physique active de l'ordinateur hôte.
   * **Type d'interface (Adapter type)** : Laisser la valeur par défaut proposée par l'hyperviseur (ne pas modifier).
   * **Mode promiscuité (Promiscuous mode)** : Sélectionner obligatoirement **Allow All** (Autoriser tout). *Cette option est indispensable pour permettre le routage et le trafic réseau vers les adresses IP virtuelles de nos conteneurs.*
   * **Adresse MAC (MAC Address)** : Conserver la valeur par défaut (ne pas modifier).
   * **Câble connecté (Virtual Cable Connected)** : Laisser la case cochée.
4. **Déroulement de l'installation d'Ubuntu Server :**
   * Charger l'image ISO d'Ubuntu Server 26.04 et démarrer la VM.
   * Lors du démarrage, il est recommandé de décocher l'option **Proceed with Unattended Installation** afin de pouvoir configurer manuellement l'utilisateur.
   * Lors de l'assistant d'installation, sélectionner l'option **Ubuntu Server Minimized** afin d'optimiser l'empreinte mémoire et d'éviter l'installation de paquets superflus.
   * Créer le compte utilisateur initial avec les identifiants stricts suivants :
     * **Nom d'utilisateur** : `master`
     * **Mot de passe** : `cisco`
5. **Configuration SSH d'accès distant :**
   * Cocher l'installation d'**OpenSSH Server** au cours de l'assistant afin de garantir un accès distant et une administration simplifiée de la plateforme.

### Étape 1 : Préparation du système et installation des prérequis
Se connecter sur la console de la VM ou via SSH en utilisant le compte administrateur `master` créé précédemment. 

1. **Mise à jour complète du système d'exploitation :**
   ```bash
   sudo apt update && sudo apt upgrade
   ```
2. **Installation des dépendances logicielles et des moteurs d'exécution :**
   * *Outils réseau, composants du moteur Docker, et environnement d'exécution pour le panel Flask.*
   ```bash
   sudo apt install nano whiptail iputils-ping dnsutils curl wget net-tools docker.io docker-compose-v2 python3 python3-flask man-db
   ```
3. **Persistance et activation du démon Docker :**
   * Configurer le service système pour s'exécuter de façon automatique à chaque initialisation de la machine.
   ```bash
   sudo systemctl enable docker
   ```

### Étape 2 : Création du compte de service étudiant sans mot de passe
L'étudiant utilisateur final de la machine doit pouvoir ouvrir sa session locale à chaud sur la console physique sans saisir de mot de passe.

1. **Création du compte système `etudiant` :**
   * Désactiver la saisie initiale du mot de passe et ignorer les informations GECOS d'identification de l'utilisateur.
   ```bash
   sudo adduser etudiant --disabled-password --gecos ""
   ```
2. **Purge explicite du mot de passe dans les tables d'authentification de l'OS :**
   ```bash
   sudo passwd -d etudiant
   ```
3. **Modification de la politique de sécurité PAM (Pluggable Authentication Modules) :**
   * Selon l'OS, Linux refuse par sécurité les connexions sur des comptes vides. Il est nécessaire d'autoriser explicitement l'argument `nullok`.
   * Ouvrir le fichier de configuration d'authentification commune :
     ```bash
     sudo nano /etc/pam.d/common-auth
     ```
   * Localiser précisément la ligne commençant par :
     `auth [success=1 default=ignore] pam_unix.so...`
   * Ajouter le mot-clé `nullok` à la toute fin de cette ligne (si elle n'y figure pas déjà). Enregistrer (Ctrl+O, Entrée) et quitter (Ctrl+X).

### Étape 3 : Configuration de l'arborescence et téléchargement de l'environnement
Cette étape structure l'arborescence système et rapatrie automatiquement l'ensemble des scripts applicatifs depuis le dépôt distant.

1. **Création du répertoire de travail principal et des templates :**
   ```bash
   sudo mkdir -p /opt/rtvm-lab/templates
   ```
2. **Télécharger les scripts applicatifs via  `curl` :**
   ```bash
   sudo curl -o /opt/rtvm-lab/docker-compose.yml https://raw.githubusercontent.com/advivar/rtvm-lab/main/docker-compose.yml
   sudo curl -o /opt/rtvm-lab/menu.sh https://raw.githubusercontent.com/advivar/rtvm-lab/main/menu.sh
   sudo curl -o /opt/rtvm-lab/admin-panel.py https://raw.githubusercontent.com/advivar/rtvm-lab/main/admin-panel.py
   sudo curl -o /opt/rtvm-lab/templates/index.html https://raw.githubusercontent.com/advivar/rtvm-lab/main/index.html
   ```
3. **Application des permissions de sécurité strictes :**
   * Attribuer la propriété exclusive de l'infrastructure à l'administrateur (`master`) :
   ```bash
   sudo chown -R master:master /opt/rtvm-lab
   ```
4. **Verrouillage des privilèges d'accès sur le système de fichiers :**
   * Appliquer un cloisonnement strict et sécuriser les fichiers sensibles :
   ```bash
   sudo chmod 700 /opt/rtvm-lab
   sudo touch /opt/rtvm-lab/.env
   sudo chmod 600 /opt/rtvm-lab/.env
   sudo chmod 600 /opt/rtvm-lab/docker-compose.yml
   sudo chmod 600 /opt/rtvm-lab/admin-panel.py
   sudo chmod 700 /opt/rtvm-lab/menu.sh
   ```

### Étape 4 : Élévation contrôlée des privilèges (Sudoers)
L'étudiant doit pouvoir lancer le script d'orchestration réseau avec les droits `root` sans qu'aucun mot de passe ne lui soit demandé. L'utilisation du bit SETUID étant inopérante sur les fichiers d'extensions de scripts `.sh`, la sécurité repose sur les directives sudoers.d.

1. **Création du fichier de règle de sécurité dédié :**
   ```bash
   sudo nano /etc/sudoers.d/rtvm-lab
   ```
2. **Déclaration de l'exception de privilèges :**
   * Copier et coller l'unique ligne d'instruction suivante au sein du fichier :
     ```text
     etudiant ALL=(ALL) NOPASSWD: /opt/rtvm-lab/menu.sh
     ```
3. **Verrouillage restrictif des droits d'accès du fichier sudoers :**
   * Par mesure de sécurité, Linux ignore et rejette les configurations sudoers si elles sont modifiables ou lisibles par un tiers. L'application des droits stricts en lecture seule est obligatoire.
   ```bash
   sudo chmod 0440 /etc/sudoers.d/rtvm-lab
   ```
4. **Validation de l'intégrité de la syntaxe système :**
   * Lancer la commande de vérification pour s'assurer de l'absence d'erreurs de configuration :
   ```bash
   sudo visudo -c
   ```
   * Si la console renvoie la mention `/etc/sudoers.d/rtvm-lab: parsed OK`, la configuration est valide.

### Étape 5 : Configuration du mécanisme d'Auto-login ( getty )
Pour simplifier l'exploitation lors du démarrage de la VM, le terminal console numéro 1 (`tty1`) doit outrepasser l'écran classique d'invite de login pour ouvrir directement la session de travail.

1. **Création du répertoire d'écrasement du service d'affichage Getty :**
   ```bash
   sudo mkdir -p /etc/systemd/system/getty@tty1.service.d
   ```
2. **Création et édition du fichier de surcharge de configuration :**
   ```bash
   sudo nano /etc/systemd/system/getty@tty1.service.d/override.conf
   ```
3. **Spécification des paramètres d'initialisation systemd :**
   * Insérer scrupuleusement les 3 lignes de configuration suivantes :
     ```ini
     [Service]
     ExecStart=
     ExecStart=-/sbin/agetty --autologin etudiant --noclear %I $TERM
     ```
4. **Prise en compte des modifications et rechargement des démons systemd :**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable getty@tty1.service
   ```

### Étape 6 : Automatisation du lancement du script applicatif au Login
Cette étape assure l'appel asynchrone du menu d'infrastructure dès que la session utilisateur s'initialise sur la console, sans altérer le chargement des profils.

1. **Création du profil utilisateur prioritaire de l'étudiant :**
   ```bash
   sudo nano /home/etudiant/.bash_profile
   ```
2. **Implémentation de la logique de routage du terminal :**
   * Ce bloc de script charge l'environnement utilisateur standard (couleurs, alias) puis vérifie via la commande `tty` si l'étudiant se situe sur l'affichage principal (`tty1`). Si la condition est vraie, le menu d'orchestration est appelé après une temporisation de sécurité d'une seconde.
   * Insérer le bloc d'instructions suivant :
     ```bash
     if [ -f ~/.bashrc ]; then
          . ~/.bashrc
     fi

     if [ "$(tty)" = "/dev/tty1" ]; then
          sleep 1
          sudo /opt/rtvm-lab/menu.sh
          if [ $? -ne 0 ]; then
              exit
          fi
     fi
     ```
3. **Restituer la propriété exclusive du profil à son utilisateur cible :**
   ```bash
   sudo chown etudiant:etudiant /home/etudiant/.bash_profile
   ```

### Étape ÉTAPES FINALE : Désactivation du client d'adressage dynamique (Netplan)
Pour éviter qu'Ubuntu Server ne tente de négocier ou de renouveler une adresse IP de façon autonome au démarrage (ce qui ralentit l'initialisation et entre en conflit direct avec l'instanciation des alias IP par le script), le protocole DHCP doit être coupé sur la carte maîtresse.

1. **Identification du nom du fichier de configuration réseau Netplan :**
   * Lister le répertoire pour identifier le nom exact du fichier YAML généré par l'OS :
   ```bash
   ls /etc/netplan/
   ```
2. **Édition de la configuration réseau système :**
   * Ouvrir le fichier trouvé à la sous-étape précédente (généralement `00-installer-config.yaml` sous Ubuntu Server) :
   ```bash
   sudo nano /etc/netplan/00-installer-config.yaml
   ```
3. **Configuration de l'interface en mode statique isolé :**
   * Modifier la structure pour qu'elle corresponde exactement au schéma ci-dessous. L'indentation par espaces est stricte et obligatoire en YAML. On suppose ici que la carte réseau physique s'intitule `enp0s3`.
     ```yaml
     network:
       ethernets:
         enp0s3:
           dhcp4: false
           dhcp6: false
           optional: true
       version: 2
     ```
4. **Application immédiate de la politique réseau :**
   * Enregistrer les modifications du fichier, puis forcer la prise en compte des paramètres par le noyau Linux :
   ```bash
   sudo netplan apply
   ```

---

## Manuel d'exploitation
Au redémarrage de la machine virtuelle, le processus s'initie de la façon suivante :
1. **Sélection réseau :** Choix du profil réseau cible (entreprises A à O) via l'interface du terminal.
2. **Nettoyage et assignation :** Purge des alias IP existants et implémentation des nouvelles directives de routage.
3. **Déploiement Docker :** Re-création forcée des conteneurs pour intégrer les nouvelles variables d'environnement.
4. **Administration :** Accès aux flux DNS et supervision des démons via le panel web (port 5000).