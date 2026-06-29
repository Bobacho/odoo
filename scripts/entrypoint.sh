#!/bin/bash
set -e

echo "=========================================="
echo "  Odoo Banco de la Nación - Entrypoint"
echo "  Versión: 17.0"
echo "=========================================="

ODOO_ADMIN_PASSWORD="${ODOO_ADMIN_PASSWORD:-admin_sbs_banco_nacion_2026}"
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-odoo}"
DB_PASSWORD="${DB_PASSWORD:-banco_nacion_sbs_2026}"
DB_NAME="${DB_NAME:-odoo_banco_nacion}"
REDIS_PASSWORD="${REDIS_PASSWORD:-redis_banco_2026}"
SMTP_SERVER="${SMTP_SERVER:-smtp.banconacion.pe}"

# Configurar odoo.conf con Python (evita problemas de permisos con sed -i)
echo "[+] Configurando odoo.conf..."
python3 -c "
import os
path = '/etc/odoo/odoo.conf'
with open(path, 'r') as f:
    content = f.read()

replacements = {
    '\${DB_HOST:db}': os.environ.get('DB_HOST', 'db'),
    '\${DB_PORT:5432}': os.environ.get('DB_PORT', '5432'),
    '\${DB_USER:odoo}': os.environ.get('DB_USER', 'odoo'),
    '\${DB_PASSWORD:banco_nacion_sbs_2026}': os.environ.get('DB_PASSWORD', 'banco_nacion_sbs_2026'),
    '\${DB_NAME:odoo_banco_nacion}': os.environ.get('DB_NAME', 'odoo_banco_nacion'),
    '\${ODOO_ADMIN_PASSWORD:admin_sbs_banco_nacion_2026}': os.environ.get('ODOO_ADMIN_PASSWORD', 'admin_sbs_banco_nacion_2026'),
    '\${REDIS_PASSWORD:redis_banco_2026}': os.environ.get('REDIS_PASSWORD', 'redis_banco_2026'),
    '\${SMTP_SERVER:smtp.banconacion.pe}': os.environ.get('SMTP_SERVER', 'smtp.banconacion.pe'),
    '\${SMTP_PORT:587}': os.environ.get('SMTP_PORT', '587'),
    '\${SMTP_USER:notificaciones-sbs@banconacion.pe}': os.environ.get('SMTP_USER', 'notificaciones-sbs@banconacion.pe'),
    '\${SMTP_PASSWORD:smtp_banco_2026}': os.environ.get('SMTP_PASSWORD', 'smtp_banco_2026'),
}

for old, new in replacements.items():
    content = content.replace(old, new)

with open(path, 'w') as f:
    f.write(content)
print('    odoo.conf configurado correctamente')
"

# Esperar a PostgreSQL
echo "[+] Esperando a PostgreSQL en ${DB_HOST}:${DB_PORT}..."
for i in $(seq 1 60); do
    if python3 -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('${DB_HOST}', ${DB_PORT})); s.close()" 2>/dev/null; then
        echo "[+] PostgreSQL disponible!"
        break
    fi
    echo "[*] Esperando PostgreSQL... (intento $i/60)"
    sleep 2
done

python3 -c "
import socket
try:
    s = socket.socket()
    s.settimeout(5)
    s.connect(('${DB_HOST}', ${DB_PORT}))
    s.close()
except Exception as e:
    print(f'[!] ERROR: No se puede conectar a PostgreSQL: {e}')
    exit(1)
"

# Crear directorio de logs con permisos para odoo
mkdir -p /var/log/odoo
chown odoo:odoo /var/log/odoo
touch /var/log/odoo/odoo.log /var/log/odoo/odoo-audit.log
chown odoo:odoo /var/log/odoo/odoo.log /var/log/odoo/odoo-audit.log

# Configurar e iniciar Wazuh agent
if [ -n "${WAZUH_MANAGER_IP}" ]; then
    echo "[+] Configurando Wazuh agent..."
    python3 -c "
path = '/var/ossec/etc/ossec.conf'
with open(path, 'r') as f:
    content = f.read()
content = content.replace('WAZUH_MANAGER_IP', '${WAZUH_MANAGER_IP}')
content = content.replace('WAZUH_REGISTRATION_PASSWORD', '${WAZUH_REGISTRATION_PASSWORD:-wazuh}')
with open(path, 'w') as f:
    f.write(content)
print('    ossec.conf configurado')
"
    /var/ossec/bin/wazuh-agent -f > /dev/null 2>&1 &
    echo "[+] Wazuh agent iniciado"
else
    echo "[!] WAZUH_MANAGER_IP no configurado, Wazuh agent no iniciado"
fi

export TZ="${TZ:-America/Lima}"
ln -sf "/usr/share/zoneinfo/${TZ}" /etc/localtime
echo "[+] Zona horaria configurada: ${TZ}"

echo "[+] Iniciando Odoo 17.0..."
echo "    DB: ${DB_HOST}:${DB_PORT}/${DB_NAME}"
echo "=========================================="

exec gosu odoo "$@"
