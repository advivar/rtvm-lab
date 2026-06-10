from flask import Flask, request, redirect, url_for, render_template_string
import subprocess
import os
import re
from datetime import datetime

app = Flask(__name__)
LAB_DIR = '/opt/rtvm-lab'

# config / env
def get_env_config():
    """lecture .env / extraction IP"""
    config = {}
    env_path = os.path.join(LAB_DIR, '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line:
                    k, v = line.strip().split('=', 1)
                    config[k] = v
    return config

# reseau hote
def get_vm_info():
    """infos reseau VM temps reel"""
    info = {'iface': 'N/A', 'ip': 'N/A', 'gateway': 'N/A', 'dns': 'N/A'}
    try:
        # awk : filtre chaine / head : 1ere ligne
        iface = subprocess.check_output("ip route | awk '/default/ {print $5}' | head -n1", shell=True).decode().strip()
        if not iface: iface = "enp0s3"
        info['iface'] = iface

        # grep -oP : regex perl extraction IP
        ip_cmd = f"ip -4 addr show {iface} | grep -oP '(?<=inet\\s)\\d+(\\.\\d+){{3}}' | head -n1"
        info['ip'] = subprocess.check_output(ip_cmd, shell=True).decode().strip()

        info['gateway'] = subprocess.check_output("ip route | awk '/default/ {print $3}' | head -n1", shell=True).decode().strip()

        # sed : substitution regex / nettoyage string
        dns_cmd = f"resolvectl status {iface} | grep 'DNS Servers' | sed 's/.*DNS Servers:\\s*//'"
        try:
            info['dns'] = subprocess.check_output(dns_cmd, shell=True).decode().strip().replace('\n', ' ')
        except:
            info['dns'] = "ERR_FETCH"
    except Exception:
        pass
    return info

# status docker
def get_services_info():
    """etat conteneurs / mapping ports"""
    config = get_env_config()
    try:
        output = subprocess.check_output(['docker', 'ps', '-a', '--format', '{{.Names}}|{{.State}}']).decode('utf-8')
    except:
        output = ""

    states = {}
    for line in output.strip().split('\n'):
        if line and line.startswith('rtvm-'):
            name, state = line.split('|')
            states[name] = state

    services = [
        {'id': 'WEB', 'name': 'rtvm-web', 'port': '80', 'ip': config.get('IP_WEB', 'N/A')},
        {'id': 'DNS', 'name': 'rtvm-dns', 'port': '53', 'ip': config.get('IP_DNS', 'N/A')},
        {'id': 'SMTP', 'name': 'rtvm-smtp', 'port': '25', 'ip': config.get('IP_SMTP', 'N/A')},
        {'id': 'FTP', 'name': 'rtvm-ftp', 'port': '21', 'ip': config.get('IP_FTP', 'N/A')},
        {'id': 'WEBMAIL', 'name': 'rtvm-webmail', 'port': '80', 'ip': config.get('IP_WEBMAIL', 'N/A')}
    ]

    for s in services:
        s['state'] = states.get(s['name'], 'unknown')

    return services

# modification ip
def update_env_ip(service, new_ip):
    """maj fichier .env / reset alias ip systeme"""
    env_path = os.path.join(LAB_DIR, '.env')
    if not os.path.exists(env_path): return False

    config = get_env_config()
    old_ip = config.get(f"IP_{service.upper()}")

    try:
        iface = subprocess.check_output("ip route | awk '/default/ {print $5}' | head -n1", shell=True).decode().strip()
    except:
        iface = "enp0s3"
    if not iface: iface = "enp0s3"

    # ip addr del/add : flush ancien alias, set nouveau
    if old_ip and old_ip != new_ip:
        subprocess.run(['sudo', 'ip', 'addr', 'del', f"{old_ip}/24", 'dev', iface], stderr=subprocess.DEVNULL)
        subprocess.run(['sudo', 'ip', 'addr', 'add', f"{new_ip}/24", 'dev', iface], stderr=subprocess.DEVNULL)

    with open(env_path, 'r') as file: lines = file.readlines()
    with open(env_path, 'w') as file:
        for line in lines:
            if line.startswith(f"IP_{service.upper()}="):
                file.write(f"IP_{service.upper()}={new_ip}\n")
            else:
                file.write(line)

    subprocess.run(['docker', 'compose', '-p', 'rtvm_core', 'up', '-d'], cwd=LAB_DIR)
    return True

# injection dns
def add_dns_record(name, rtype, value):
    """ajout record zone locale / creation zone externe master"""
    # Sécurité : suppression des espaces, sauts de ligne et caractères interdits
    name = re.sub(r'[^a-zA-Z0-9.-]', '', name)
    value = re.sub(r'[^a-zA-Z0-9.-]', '', value)
    config = get_env_config()
    domain = config.get('DOMAIN', 'local.net')

    # pas de '.' = sous-domaine local
    if '.' not in name:
        zone_path = os.path.join(LAB_DIR, 'dns', 'db.zone')
        with open(zone_path, 'r') as file: content = file.read()
        
        new_serial = datetime.now().strftime('%Y%m%d%H')
        # re.sub : update serial bind9
        content = re.sub(r'\(\d+', f'({new_serial}', content)
        content += f"{name.ljust(15)} IN  {rtype.ljust(5)} {value}\n"
        
        with open(zone_path, 'w') as file: file.write(content)
    # avec '.' = domaine externe cible
    else:
        zones_dir = os.path.join(LAB_DIR, 'dns', 'zones')
        os.makedirs(zones_dir, exist_ok=True)
        custom_zone_file = f"db.{name}"
        custom_zone_path = os.path.join(zones_dir, custom_zone_file)

        with open(custom_zone_path, 'w') as file:
            file.write(f"$TTL 86400\n")
            file.write(f"@   IN  SOA  dns.{domain}. root.{domain}. (1 3600 900 604800 86400)\n")
            file.write(f"@   IN  NS   dns.{domain}.\n")
            file.write(f"@   IN  {rtype.ljust(5)} {value}\n")

        named_local_path = os.path.join(LAB_DIR, 'dns', 'named.conf.local')
        with open(named_local_path, 'r') as file: named_content = file.read()
        if f'zone "{name}"' not in named_content:
            with open(named_local_path, 'a') as file:
                file.write(f'\nzone "{name}" {{ type master; file "/etc/bind/zones/{custom_zone_file}"; }};\n')

    subprocess.run(['docker', 'restart', 'rtvm-dns'])
    return True

# lecture dns
def get_dns_records():
    """parsing regex db.zone / db.* -> structure dict"""
    config = get_env_config()
    domain = config.get('DOMAIN', 'local.net')
    records = []

    zone_path = os.path.join(LAB_DIR, 'dns', 'db.zone')
    if os.path.exists(zone_path):
        with open(zone_path, 'r') as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith(';') or 'SOA' in line or 'NS' in line: continue
                parts = line.split()
                if len(parts) >= 4 and parts[1] == 'IN':
                    name = parts[0]
                    name_full = domain if name == '@' else f"{name}.{domain}"
                    records.append({'name': name_full, 'type': parts[2], 'value': " ".join(parts[3:]), 'zone': 'LOCALE'})

    zones_dir = os.path.join(LAB_DIR, 'dns', 'zones')
    if os.path.exists(zones_dir):
        for filename in os.listdir(zones_dir):
            if filename.startswith('db.'):
                zone_domain = filename[3:]
                filepath = os.path.join(zones_dir, filename)
                with open(filepath, 'r') as file:
                    for line in file:
                        line = line.strip()
                        if not line or line.startswith(';') or 'SOA' in line or 'NS' in line: continue
                        parts = line.split()
                        if len(parts) >= 4 and parts[1] == 'IN':
                            name = parts[0]
                            name_full = zone_domain if name == '@' else f"{name}.{zone_domain}"
                            records.append({'name': name_full, 'type': parts[2], 'value': " ".join(parts[3:]), 'zone': 'EXTERNE', 'file': zone_domain})

    return records

# purge dns
def delete_dns_record(record_name, record_type, record_value, zone_type, file_domain=None):
    """suppression regex ligne ciblée / rm fichier zone externe"""
    config = get_env_config()
    domain = config.get('DOMAIN', 'local.net')

    if zone_type == 'LOCALE':
        zone_path = os.path.join(LAB_DIR, 'dns', 'db.zone')
        if not os.path.exists(zone_path): return False

        if record_name == domain: short_name = "@"
        elif record_name.endswith(f".{domain}"): short_name = record_name[:-len(f".{domain}")]
        else: short_name = record_name

        with open(zone_path, 'r') as file: lines = file.readlines()
        new_lines = []
        for line in lines:
            parts = line.split()
            if len(parts) >= 4 and parts[0] == short_name and parts[1] == 'IN' and parts[2] == record_type and " ".join(parts[3:]) == record_value:
                continue
            new_lines.append(line)

        content = "".join(new_lines)
        new_serial = datetime.now().strftime('%Y%m%d%H')
        content = re.sub(r'\(\d+', f'({new_serial}', content)
        with open(zone_path, 'w') as file: file.write(content)

    elif zone_type == 'EXTERNE' and file_domain:
        zone_file = os.path.join(LAB_DIR, 'dns', 'zones', f"db.{file_domain}")
        if os.path.exists(zone_file): os.remove(zone_file)

        named_local = os.path.join(LAB_DIR, 'dns', 'named.conf.local')
        if os.path.exists(named_local):
            with open(named_local, 'r') as file: lines = file.readlines()
            with open(named_local, 'w') as file:
                for line in lines:
                    if f'zone "{file_domain}"' not in line:
                        file.write(line)

    subprocess.run(['docker', 'restart', 'rtvm-dns'])
    return True

# interface raw HTML
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>RTVM-LAB - Entreprise {{ letter }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { font-family: 'Courier New', Courier, monospace; background-color: #1e1e1e; color: #d4d4d4; }
        .card { background-color: #252526; border: 1px solid #3e3e42; border-radius: 0; }
        .card-header { background-color: #333337 !important; color: #fff !important; border-bottom: 1px solid #3e3e42; border-radius: 0; font-weight: bold; font-size: 0.9rem; letter-spacing: 1px; }
        .table { color: #d4d4d4; font-size: 0.9rem; }
        .table-dark { background-color: #252526; }
        .table-dark th { border-color: #3e3e42; background-color: #333337; color: #9cdcfe; font-weight: normal; }
        .table-dark td { border-color: #3e3e42; vertical-align: middle; }
        .btn { border-radius: 0; font-weight: bold; font-size: 0.8rem; letter-spacing: 0.5px; }
        .form-control, .form-select { background-color: #3c3c3c; color: #d4d4d4; border: 1px solid #555; border-radius: 0; font-family: inherit; font-size: 0.9rem; }
        .form-control:focus, .form-select:focus { background-color: #3c3c3c; color: #fff; border-color: #007acc; box-shadow: none; }
        .badge { border-radius: 0; font-weight: normal; padding: 0.4em 0.6em; }
        .text-muted { color: #858585 !important; }
        .text-primary { color: #569cd6 !important; }
        .text-success { color: #b5cea8 !important; }
        .text-warning { color: #ce9178 !important; }
        .text-info { color: #4fc1ff !important; }
        .bg-success { background-color: #4CAF50 !important; }
        .bg-danger { background-color: #f14c4c !important; }
        .bg-secondary { background-color: #4d4d4d !important; }
        .bg-warning { background-color: #d7ba7d !important; color: #1e1e1e !important; }
        .btn-primary { background-color: #007acc; border-color: #007acc; }
        .btn-success { background-color: #4CAF50; border-color: #4CAF50; }
        .btn-outline-danger { color: #f14c4c; border-color: #f14c4c; }
        .btn-outline-danger:hover { background-color: #f14c4c; color: #fff; }
        .btn-outline-success { color: #4CAF50; border-color: #4CAF50; }
        .btn-outline-success:hover { background-color: #4CAF50; color: #fff; }
        .delete-btn { background-color: transparent; border: 1px solid #f14c4c; color: #f14c4c; font-size: 0.7rem; padding: 2px 6px; cursor: pointer; }
        .delete-btn:hover { background-color: #f14c4c; color: #fff; }
        .header-title { border-bottom: 2px solid #007acc; padding-bottom: 10px; margin-bottom: 20px; font-weight: bold; color: #fff; }
        .sys-info-label { font-size: 0.75rem; color: #858585; text-transform: uppercase; }
        .sys-info-value { font-size: 1.1rem; color: #9cdcfe; }
        .credit-banner { text-align: center; font-size: 0.8rem; color: #6e6e6e; margin-top: 30px; border-top: 1px dashed #3e3e42; padding-top: 15px; }
        ::-webkit-scrollbar { width: 10px; }
        ::-webkit-scrollbar-track { background: #1e1e1e; }
        ::-webkit-scrollbar-thumb { background: #424242; }

        /* OVERLAY DE CHARGEMENT */
        #loading-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(30, 30, 30, 0.85); z-index: 9999; justify-content: center; align-items: center; flex-direction: column; backdrop-filter: blur(2px); }
        .loader-box { background-color: #252526; border: 1px solid #3e3e42; padding: 30px; min-width: 380px; text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.5); }
        .loader-text { color: #569cd6; font-weight: bold; font-size: 1.1rem; margin-bottom: 15px; letter-spacing: 1px; }
        .blinker { animation: blinker 1s linear infinite; color: #d4d4d4; }
        @keyframes blinker { 50% { opacity: 0; } }
        .progress-bar-container { width: 100%; background-color: #1e1e1e; border: 1px solid #3e3e42; height: 15px; position: relative; overflow: hidden; }
        .progress-bar-fill { height: 100%; background-color: #4CAF50; width: 30%; position: absolute; animation: loadBar 1.5s infinite linear; }
        @keyframes loadBar { 0% { left: -30%; } 100% { left: 100%; } }
    </style>
</head>
<body class="pb-5">

<div id="loading-overlay">
    <div class="loader-box">
        <div class="loader-text">TRAITEMENT EN COURS<span class="blinker">_</span></div>
        <div class="progress-bar-container">
            <div class="progress-bar-fill"></div>
        </div>
        <div style="font-size: 0.75rem; color: #858585; margin-top: 15px;">Veuillez patienter pendant l'exécution système...</div>
    </div>
</div>

<div class="container mt-4">
    <h3 class="header-title">RTVM-LAB - Console d'administration (Company : {{ letter }})</h3>

    <div class="card mb-4">
        <div class="card-header">Configuration réseau de la machine virtuelle</div>
        <div class="card-body py-2">
            <div class="row text-center">
                <div class="col-md-3 border-end border-secondary">
                    <span class="sys-info-label d-block">Interface</span>
                    <span class="sys-info-value">{{ vm.iface }}</span>
                </div>
                <div class="col-md-3 border-end border-secondary">
                    <span class="sys-info-label d-block">Adresse IP</span>
                    <span class="sys-info-value text-primary">{{ vm.ip }}</span>
                </div>
                <div class="col-md-3 border-end border-secondary">
                    <span class="sys-info-label d-block">Passerelle</span>
                    <span class="sys-info-value">{{ vm.gateway }}</span>
                </div>
                <div class="col-md-3">
                    <span class="sys-info-label d-block">Serveurs DNS actifs</span>
                    <span class="sys-info-value" style="color:#b5cea8;">{{ vm.dns }}</span>
                </div>
            </div>
        </div>
    </div>

    <div class="row">
        <div class="col-md-6">
            <div class="card mb-3">
                <div class="card-header">État des services (Conteneurs Docker)</div>
                <ul class="list-group list-group-flush bg-transparent">
                    {% for s in services %}
                    <li class="list-group-item bg-transparent border-secondary d-flex justify-content-between align-items-center py-2">
                        <div>
                            <span style="color:#ce9178; font-weight:bold;">{{ s.name }}</span><br>
                            <span class="text-muted" style="font-size:0.8rem;">Liaison : {{ s.ip }}:{{ s.port }}</span>
                        </div>
                        <span>
                            <span class="badge {% if s.state == 'running' %}bg-success{% else %}bg-danger{% endif %} me-2">
                                {{ s.state | upper }}
                            </span>
                            <a href="/toggle/{{ s.name }}/{{ 'stop' if s.state == 'running' else 'start' }}" onclick="showLoader()"
                               class="btn btn-sm {% if s.state == 'running' %}btn-outline-danger{% else %}btn-outline-success{% endif %}">
                                {{ 'STOP' if s.state == 'running' else 'START' }}
                            </a>
                        </span>
                    </li>
                    {% endfor %}
                </ul>
            </div>

            <div class="card mb-3">
                <div class="card-header">Changement rapide d'adresse IP</div>
                <div class="card-body">
                    <form action="/change_ip" method="POST" onsubmit="showLoader()">
                        <select name="service" class="form-select mb-2" required>
                            <option value="" disabled selected>Choisir un service cible...</option>
                            {% for s in services %}
                            <option value="{{ s.id }}">{{ s.name }} [Actuel : {{ s.ip }}]</option>
                            {% endfor %}
                        </select>
                        <input type="text" name="new_ip" class="form-control mb-3" placeholder="Nouvelle adresse IPv4 (ex : 192.168.1.50)" required>
                        <button type="submit" class="btn btn-primary w-100">Modifier l'IP</button>
                    </form>
                </div>
            </div>
        </div>

        <div class="col-md-6">
            <div class="card mb-3">
                <div class="card-header">Ajout d'un enregistrement DNS</div>
                <div class="card-body">
                    <form action="/add_dns" method="POST" onsubmit="showLoader()">
                        <label class="sys-info-label">Nom d'hôte ou FQDN complet</label>
                        <input type="text" name="name" class="form-control mb-2" placeholder="Ex : intranet ou www.b.net" required>

                        <div class="row">
                            <div class="col-md-4">
                                <label class="sys-info-label">Type</label>
                                <select name="rtype" class="form-select mb-2">
                                    <option value="A">A</option>
                                    <option value="AAAA">AAAA</option>
                                    <option value="CNAME">CNAME</option>
                                    <option value="MX">MX</option>
                                    <option value="TXT">TXT</option>
                                </select>
                            </div>
                            <div class="col-md-8">
                                <label class="sys-info-label">Valeur ou Cible</label>
                                <input type="text" name="value" class="form-control mb-3" placeholder="Ex : IP ou cible DNS" required>
                            </div>
                        </div>
                        <button type="submit" class="btn btn-success w-100">Ajouter au DNS</button>
                    </form>
                </div>
                <div class="card-footer border-secondary text-muted" style="font-size: 0.75rem; background-color: #2d2d30;">
                    // Redirection externe : Université de Lorraine (Primaire) et Google (Secondaire)
                </div>
            </div>
        </div>
    </div>

    <div class="row">
        <div class="col-12">
            <div class="card">
                <div class="card-header">Table des enregistrements DNS actifs (BIND9)</div>
                <div class="card-body p-0">
                    <table class="table table-dark table-striped mb-0">
                        <thead>
                            <tr>
                                <th>Nom FQDN</th>
                                <th>Type</th>
                                <th>Donnée / Cible</th>
                                <th>Périmètre de zone</th>
                                <th class="text-center">Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for r in dns_records %}
                            <tr>
                                <td style="color:#dcdcaa;">{{ r.name }}</td>
                                <td><span style="color:#569cd6;">{{ r.type }}</span></td>
                                <td>{{ r.value }}</td>
                                <td>
                                    <span class="badge {% if r.zone == 'LOCALE' %}bg-secondary{% else %}bg-warning{% endif %}">
                                        {{ r.zone }}
                                    </span>
                                </td>
                                <td class="text-center">
                                    <form action="/delete_dns" method="POST" class="d-inline" onsubmit="if(confirm('Confirmer la suppression de cet enregistrement ?')){showLoader(); return true;} else {return false;}">
                                        <input type="hidden" name="name" value="{{ r.name }}">
                                        <input type="hidden" name="type" value="{{ r.type }}">
                                        <input type="hidden" name="value" value="{{ r.value }}">
                                        <input type="hidden" name="zone" value="{{ r.zone }}">
                                        <input type="hidden" name="file_domain" value="{{ r.file|default('') }}">
                                        <button type="submit" class="delete-btn">Supprimer</button>
                                    </form>
                                </td>
                            </tr>
                            {% else %}
                            <tr>
                                <td colspan="5" class="text-center text-muted py-3">Aucun enregistrement DNS trouvé</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    
    <div class="credit-banner">
        RTVM-Lab &mdash; Plateforme d'apprentissage conçue et réalisée par Augustin de Vivar et Maxence Kroetz
    </div>
</div>

<script>
    function showLoader() {
        document.getElementById('loading-overlay').style.display = 'flex';
    }
</script>

</body>
</html>
"""

# routes flask
@app.route('/')
def index():
    config = get_env_config()
    domain = config.get('DOMAIN', 'a.net')
    # isolement de la lettre d'entreprise
    letter = domain.split('.')[0].upper()
    vm_info = get_vm_info()
    services = get_services_info()
    dns_records = get_dns_records()
    return render_template_string(HTML_TEMPLATE, vm=vm_info, services=services, dns_records=dns_records, letter=letter)

@app.route('/toggle/<container>/<action>')
def toggle_container(container, action):
    if action in ['start', 'stop']: subprocess.run(['docker', action, container])
    return redirect(url_for('index'))

@app.route('/change_ip', methods=['POST'])
def change_ip():
    if request.form.get('service') and request.form.get('new_ip'):
        update_env_ip(request.form.get('service'), request.form.get('new_ip'))
    return redirect(url_for('index'))

@app.route('/add_dns', methods=['POST'])
def add_dns():
    name = request.form.get('name')
    rtype = request.form.get('rtype')
    value = request.form.get('value')
    if name and rtype and value:
        add_dns_record(name, rtype, value)
    return redirect(url_for('index'))

@app.route('/delete_dns', methods=['POST'])
def delete_dns():
    name = request.form.get('name')
    rtype = request.form.get('type')
    value = request.form.get('value')
    zone = request.form.get('zone')
    file_domain = request.form.get('file_domain')

    if name and rtype and value and zone:
        delete_dns_record(name, rtype, value, zone, file_domain)

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)