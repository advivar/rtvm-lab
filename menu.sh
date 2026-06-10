#!/bin/bash
# /opt/rtvm-lab/menu.sh

# awk / head : extraction carte reseau active
IFACE=$(ip route | awk '/default/ {print $5}' | head -n1)
# fallback defaut
[ -z "$IFACE" ] && IFACE="enp0s3"

# whiptail : menu graphique interactif terminal
# 3>&1 1>&2 2>&3 : inversion stdout/stderr pour capture variable CHOIX
CHOIX=$(whiptail --title "RTVM LAB - INFRASTRUCTURE" --menu "Choisir le réseau de l'entreprise (Interface: $IFACE) :" 23 60 15 \
"A" "192.168.1.0/24" "B" "192.168.2.0/24" "C" "192.168.3.0/24" \
"D" "192.168.4.0/24" "E" "192.168.5.0/24" "F" "192.168.6.0/24" \
"G" "192.168.7.0/24" "H" "192.168.8.0/24" "I" "192.168.9.0/24" \
"J" "192.168.10.0/24" "K" "192.168.11.0/24" "L" "192.168.12.0/24" \
"M" "192.168.13.0/24" "N" "192.168.14.0/24" "O" "192.168.15.0/24" 3>&1 1>&2 2>&3)

# $? : code retour (echap = sortie script)
if [ $? -ne 0 ]; then exit 1; fi

clear

# tr : formatage min/maj
LETTER=$(printf "%s" "$CHOIX" | tr '[:upper:]' '[:lower:]')
DOMAIN="${LETTER}.net"

# case : assignation var reseau / hex couleurs
case $CHOIX in
    A) NET=1;  COLOR="#2563eb"; HOVER="#1d4ed8" ;;
    B) NET=2;  COLOR="#10b981"; HOVER="#059669" ;;
    C) NET=3;  COLOR="#f97316"; HOVER="#ea580c" ;;
    D) NET=4;  COLOR="#14b8a6"; HOVER="#0d9488" ;;
    E) NET=5;  COLOR="#6366f1"; HOVER="#4f46e5" ;;
    F) NET=6;  COLOR="#e11d48"; HOVER="#be123c" ;;
    G) NET=7;  COLOR="#059669"; HOVER="#047857" ;;
    H) NET=8;  COLOR="#06b6d4"; HOVER="#0891b2" ;;
    I) NET=9;  COLOR="#8b5cf6"; HOVER="#7c3aed" ;;
    J) NET=10; COLOR="#f59e0b"; HOVER="#d97706" ;;
    K) NET=11; COLOR="#0ea5e9"; HOVER="#0284c7" ;;
    L) NET=12; COLOR="#84cc16"; HOVER="#65a30d" ;;
    M) NET=13; COLOR="#a855f7"; HOVER="#9333ea" ;;
    N) NET=14; COLOR="#d946ef"; HOVER="#c026d3" ;;
    O) NET=15; COLOR="#475569"; HOVER="#334155" ;;
esac

BASE_IP="192.168.$NET"
GATEWAY="${BASE_IP}.254"

DNS_UL="193.50.27.27"
DNS_SECONDARY="8.8.8.8"

printf "Action : Sauvegarde de l'état global (Web, DNS, Mails) de l'entreprise précédente...\n"

# backup data
# -f : test existence fichier
if [ -f /opt/rtvm-lab/.env ]; then
    # grep / cut : parse config precedente
    PREV_DOMAIN=$(grep 'DOMAIN=' /opt/rtvm-lab/.env | cut -d= -f2)
    PREV_LETTER=$(echo "${PREV_DOMAIN}" | cut -d. -f1 | tr '[:lower:]' '[:upper:]')

    # -z : test chaine vide
    if [ ! -z "$PREV_LETTER" ]; then
        mkdir -p /opt/rtvm-lab/archives/${PREV_LETTER}/www
        mkdir -p /opt/rtvm-lab/archives/${PREV_LETTER}/dns
        mkdir -p /opt/rtvm-lab/archives/${PREV_LETTER}/mail-data

        # 2>/dev/null : silence erreurs stderr
        [ -d /home/etudiant/www ] && cp -r /home/etudiant/www/* /opt/rtvm-lab/archives/${PREV_LETTER}/www/ 2>/dev/null || true
        [ -d /opt/rtvm-lab/dns ] && cp -r /opt/rtvm-lab/dns/* /opt/rtvm-lab/archives/${PREV_LETTER}/dns/ 2>/dev/null || true
        [ -d /opt/rtvm-lab/mail-data ] && cp -r /opt/rtvm-lab/mail-data/* /opt/rtvm-lab/archives/${PREV_LETTER}/mail-data/ 2>/dev/null || true
    fi
fi

# flags restauration
RESTORE_WWW=1
RESTORE_DNS=1
RESTORE_MAIL=1

# prompt reinit
# -d : test existence dossier
if [ -d "/opt/rtvm-lab/archives/${CHOIX}" ]; then
    printf "\n\e[1;33m[?]\e[0m Une sauvegarde existe pour l'entreprise %s.\n" "${CHOIX}"

    # read -t 10 : prompt avec timeout 10s
    read -t 10 -p "Voulez-vous RÉINITIALISER le site WEB ? [y/N] (Défaut N, conserve TOUT dans 10s) : " reset_web

    # $? -gt 128 : check si expiration timeout (read)
    if [ $? -gt 128 ]; then
        printf "\n-> \e[1;30mTemps imparti écoulé (10s). Conservation globale de toutes vos configurations antérieures.\e[0m\n\n"
        RESTORE_WWW=1
        RESTORE_DNS=1
        RESTORE_MAIL=1
    else
        # regex : match oui/y
        if [[ "$reset_web" =~ ^[Yy](es)?$ ]]; then
            printf "   -> \e[1;31mSite WEB marqué pour réinitialisation.\e[0m\n"
            RESTORE_WWW=0
        else
            printf "   -> Site WEB conservé.\n"
            RESTORE_WWW=1
        fi

        read -p "Voulez-vous RÉINITIALISER la configuration DNS ? [y/N] (Défaut N) : " reset_dns
        if [[ "$reset_dns" =~ ^[Yy](es)?$ ]]; then
            printf "   -> \e[1;31mConfiguration DNS marquée pour réinitialisation.\e[0m\n"
            RESTORE_DNS=0
        else
            printf "   -> Configuration DNS conservée.\n"
            RESTORE_DNS=1
        fi

        read -p "Voulez-vous RÉINITIALISER la MESSAGERIE (Mails) ? [y/N] (Défaut N) : " reset_mail
        if [[ "$reset_mail" =~ ^[Yy](es)?$ ]]; then
            printf "   -> \e[1;31mMessagerie marquée pour réinitialisation.\e[0m\n"
            RESTORE_MAIL=0
        else
            printf "   -> Messagerie conservée.\n"
            RESTORE_MAIL=1
        fi
        printf "\n"
    fi
fi

printf "Action : Nettoyage des anciennes configurations réseau...\n"
# loop / ip del : suppr alias IP systeme
for n in {1..15}; do
    for i in {10..15}; do
        sudo ip addr del 192.168.${n}.${i}/24 dev $IFACE 2>/dev/null || true
    done
done

printf "Action : Configuration Réseau (IP, Gateway, DNS)...\n"
# ip add : ajout nv alias IP
for i in {10..15}; do
    sudo ip addr add ${BASE_IP}.${i}/24 dev $IFACE 2>/dev/null || true
done
sudo ip link set $IFACE up

# route / resolvectl : set passerelle / cache DNS systeme
sudo ip route add default via $GATEWAY 2>/dev/null || true
sudo resolvectl dns $IFACE $DNS_UL $DNS_SECONDARY
sudo resolvectl flush-caches

printf "Action : Préparation de l'environnement RTVM...\n"

# EOF : here-document, redirection bloc multilignes vers fichier
cat <<EOF > /opt/rtvm-lab/.env
DOMAIN=${DOMAIN}
IP_WEB=${BASE_IP}.11
IP_DNS=${BASE_IP}.12
IP_SMTP=${BASE_IP}.13
IP_FTP=${BASE_IP}.14
IP_WEBMAIL=${BASE_IP}.15
EOF

# flush / struct dossiers temp
rm -rf /home/etudiant/www/* 2>/dev/null || true
rm -rf /opt/rtvm-lab/dns/* 2>/dev/null || true
rm -rf /opt/rtvm-lab/mail-data/* 2>/dev/null || true
mkdir -p /opt/rtvm-lab/dns/zones
mkdir -p /opt/rtvm-lab/mail-data

# logique web
if [ -d "/opt/rtvm-lab/archives/${CHOIX}/www" ] && [ $RESTORE_WWW -eq 1 ]; then
    cp -r /opt/rtvm-lab/archives/${CHOIX}/www/* /home/etudiant/www/ 2>/dev/null || true
else
    if [ -f /opt/rtvm-lab/templates/index.html ]; then
        cp /opt/rtvm-lab/templates/index.html /home/etudiant/www/index.html
        # sed -i : substitution inline fichier texte
        sed -i "s/_COMPANY_LETTER_/${CHOIX}/g" /home/etudiant/www/index.html
        sed -i "s/_DOMAIN_/${DOMAIN}/g" /home/etudiant/www/index.html
        sed -i "s/_PRIMARY_COLOR_/${COLOR}/g" /home/etudiant/www/index.html
        sed -i "s/_PRIMARY_HOVER_/${HOVER}/g" /home/etudiant/www/index.html
    else
        echo "<h1>⚡ Entreprise ${CHOIX} Energy (${DOMAIN})</h1>" > /home/etudiant/www/index.html
    fi
fi
chown -R etudiant:etudiant /home/etudiant/www
chmod -R 777 /home/etudiant/www

# logique dns
if [ -d "/opt/rtvm-lab/archives/${CHOIX}/dns" ] && [ $RESTORE_DNS -eq 1 ]; then
    cp -r /opt/rtvm-lab/archives/${CHOIX}/dns/* /opt/rtvm-lab/dns/ 2>/dev/null || true
else
    SERIAL=$(date +%Y%m%d%H)
    cat <<EOF > /opt/rtvm-lab/dns/db.zone
\$TTL 86400
@   IN  SOA  dns.${DOMAIN}. root.${DOMAIN}. (${SERIAL} 3600 900 604800 86400)
@   IN  NS   dns.${DOMAIN}.
@   IN  MX   10 smtp.${DOMAIN}.
www      IN  A  ${BASE_IP}.11
webmail  IN  A  ${BASE_IP}.15
dns      IN  A  ${BASE_IP}.12
smtp     IN  A  ${BASE_IP}.13
ftp      IN  A  ${BASE_IP}.14
EOF

    > /opt/rtvm-lab/dns/named.conf.local
    LETTERS=(a b c d e f g h i j k l m n o)
    for idx in {1..15}; do
        l_idx=$((idx-1))
        current_letter=${LETTERS[$l_idx]}
        current_domain="${current_letter}.net"
        ip_prefix="192.168.${idx}"

        if [ "$current_domain" = "$DOMAIN" ]; then
            printf 'zone "%s" { type master; file "/etc/bind/db.zone"; };\n' "$current_domain" >> /opt/rtvm-lab/dns/named.conf.local
        else
            cat <<EOF > /opt/rtvm-lab/dns/zones/db.${current_domain}
\$TTL 86400
@   IN  SOA  dns.${current_domain}. root.${current_domain}. (${SERIAL} 3600 900 604800 86400)
@   IN  NS   dns.${current_domain}.
@   IN  MX   10 smtp.${current_domain}.
www      IN  A  ${ip_prefix}.11
webmail  IN  A  ${ip_prefix}.15
dns      IN  A  ${ip_prefix}.12
smtp     IN  A  ${ip_prefix}.13
ftp      IN  A  ${ip_prefix}.14
EOF
            printf 'zone "%s" { type master; file "/etc/bind/zones/db.%s"; };\n' "$current_domain" "$current_domain" >> /opt/rtvm-lab/dns/named.conf.local
        fi
    done

    cat <<EOF > /opt/rtvm-lab/dns/named.conf.options
options {
    directory "/var/cache/bind";
    recursion yes;
    allow-query { any; };
    allow-recursion { any; };
    forwarders { ${DNS_UL}; ${DNS_SECONDARY}; };
    forward first;
    dnssec-validation no;
    listen-on { any; };
    listen-on-v6 { none; };
};
EOF
fi

# logique mail
NEED_MAIL_SETUP=1
if [ -d "/opt/rtvm-lab/archives/${CHOIX}/mail-data" ] && [ $RESTORE_MAIL -eq 1 ]; then
    cp -r /opt/rtvm-lab/archives/${CHOIX}/mail-data/* /opt/rtvm-lab/mail-data/ 2>/dev/null || true
    NEED_MAIL_SETUP=0
fi

printf "Action : Demarrage des services Docker...\n"
cd /opt/rtvm-lab

# tentative standard
docker compose -p rtvm_core down -v --remove-orphans > /dev/null 2>&1
docker compose -p rtvm_core up -d --force-recreate > /dev/null 2>&1

if [ $? -ne 0 ]; then
    printf "Avertissement : Anomalie detectee. Purge Niveau 1 (Nettoyage logiciel)...\n"
    # suppression cibles virtuelles
    docker compose -p rtvm_core rm -fsv > /dev/null 2>&1
    docker container prune -f > /dev/null 2>&1
    docker network prune -f > /dev/null 2>&1
    
    docker compose -p rtvm_core up -d --force-recreate > /dev/null 2>&1

    if [ $? -ne 0 ]; then
        printf "Avertissement : Echec Niveau 1. Purge Niveau 2 (Redemarrage demon)...\n"
        # vidage ram containerd
        systemctl restart docker
        docker compose -p rtvm_core down -v --remove-orphans > /dev/null 2>&1
        
        docker compose -p rtvm_core up -d --force-recreate > /dev/null 2>&1

        if [ $? -ne 0 ]; then
            printf "\n[!] Echec Niveau 2 : Corruption profonde de l'index Docker.\n"
            printf "Une reinitialisation complete du moteur (Factory Reset) est requise.\n"
            printf "[ATTENTION] Cette action supprime le cache local. Le telechargement des images via Internet est necessaire.\n"

            read -p "Autoriser la reparation de Niveau 3 ? [y/N] : " confirm_reset

            if [[ "$confirm_reset" =~ ^[Yy](es)?$ ]]; then
                printf "Action : Hard Reset (Arret, Suppression, Redemarrage)...\n"
                # destruction totale BDD docker
                systemctl stop docker docker.socket containerd
                rm -rf /var/lib/docker
                rm -rf /var/lib/containerd
                systemctl start containerd
                systemctl start docker

                printf "Action : Deploiement et pull des images...\n"
                # affichage standard pour suivi telechargement
                docker compose -p rtvm_core up -d --force-recreate
                
                if [ $? -ne 0 ]; then
                    FAIL_CRITICAL=1
                fi
            else
                printf "Action : Reparation Niveau 3 annulee.\n"
                FAIL_CRITICAL=1
            fi

            if [ "$FAIL_CRITICAL" = "1" ]; then
                printf "\n[ERREUR FATALE] Infrastructure Docker indisponible.\n"
                printf "La reparation automatique a echoue ou a ete annulee.\n\n"
                printf "Interface active : %s\n" "$IFACE"
                printf "Adresse IP       : %s.10\n" "$BASE_IP"
                printf "Passerelle (GW)  : %s\n" "$GATEWAY"
                printf "Serveurs DNS     : %s / %s\n" "$DNS_UL" "$DNS_SECONDARY"
                printf "Connexion distante requise via SSH (port 22) avec les privileges master.\n"
                printf "Maintien de la session locale restreinte (etudiant).\n\n"
                
                # Code retour 0 pour laisser l'acces au terminal etudiant standard
                exit 0
            fi
        fi
    fi
fi

if [ $NEED_MAIL_SETUP -eq 1 ]; then
    printf "Action : Création des boîtes mails de base (Veuillez patienter 10s)...\n"
    sleep 10
    sudo docker exec rtvm-smtp setup email add user@${DOMAIN} rtvm-lab > /dev/null 2>&1 || true
else
    sleep 5
fi

printf "Action : Lancement du panel d'administration Python...\n"
# pkill : tuer processus precedent via nom (-f)
sudo pkill -f admin-panel.py 2>/dev/null
# & : process en arriere plan
sudo python3 /opt/rtvm-lab/admin-panel.py > /dev/null 2>&1 &

printf "Action : Vérification de l'état des services...\n"
sleep 5

VERT='\e[1;32m'
ROUGE='\e[1;31m'
RESET='\e[0m'

# helper validation dockers
check_docker() {
    local srv=$1
    if sudo docker compose -p rtvm_core ps --services --filter "status=running" 2>/dev/null | grep -qw "$srv"; then
        printf "[${VERT}*${RESET}]"
    else
        printf "[${ROUGE}X${RESET}]"
    fi
}

# helper validation sysadmin panel
check_panel() {
    if pgrep -f "admin-panel.py" > /dev/null; then
        printf "[${VERT}*${RESET}]"
    else
        printf "[${ROUGE}X${RESET}]"
    fi
}

printf "\nRÉCAPITULATIF RTVM-LAB : %s\n" "$DOMAIN"
printf "\t[${VERT}*${RESET}] Machine Virtuelle : %s.10 (GW: .254 / DNS: %s puis %s)\n" "$BASE_IP" "${DNS_UL}" "${DNS_SECONDARY}"
printf "\t%s Serveur Web : %s.11\n" "$(check_docker "web")" "$BASE_IP"
printf "\t%s Serveur DNS : %s.12\n" "$(check_docker "dns")" "$BASE_IP"
printf "\t%s SMTP (Mail) : %s.13\n" "$(check_docker "smtp")" "$BASE_IP"
printf "\t%s FTP         : %s.14\n" "$(check_docker "ftp")" "$BASE_IP"
printf "\t%s Webmail     : %s.15\n" "$(check_docker "webmail")" "$BASE_IP"

printf "\nINFORMATIONS DE CONNEXION ET ACCÈS :\n"
printf "\t- Site Web : http://www.%s (ou http://%s.11)\n" "$DOMAIN" "$BASE_IP"
printf "\t- Espace FTP      : /home/etudiant/www/ (Identifiants: etudiant / rtvm-lab)\n"
printf "\t- Webmail         : http://webmail.%s (ou http://%s.15)\n" "$DOMAIN" "$BASE_IP"
printf "\t                    Identifiants : user@%s | Mot de passe : rtvm-lab\n" "$DOMAIN"
printf "\n\t%s Panel Admin     : http://%s.10:5000\n" "$(check_panel)" "$BASE_IP"

# credits
printf "\n\e[1;30mRTVM-Lab - Plateforme d'apprentissage conçue et réalisée par Augustin de Vivar et Maxence Kroetz\e[0m\n"
printf "\n\e[1;30mhttps://github.com/advivar/rtvm-lab\e[0m\n"

printf "\nAppuyez sur entrée...\n"
read