#!/bin/bash
# ==========================================
# Setup Wazuh Agent for Odoo BDN
# ==========================================

set -e

WAZUH_MANAGER="${1:-wazuh.manager.local}"
WAZUH_REG_PASSWORD="${2:-wazuh_reg_banco_2026}"
WAZUH_AGENT_NAME="${3:-odoo-banco-nacion}"

echo "=========================================="
echo "  Wazuh Agent Setup - Banco de la Nación"
echo "=========================================="

# Verify Wazuh agent is installed
if ! command -v /var/ossec/bin/wazuh-agent &> /dev/null; then
    echo "[!] Wazuh agent no está instalado. Instalando..."
    curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH | gpg --dearmor > /usr/share/keyrings/wazuh.gpg
    echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main" > /etc/apt/sources.list.d/wazuh.list
    apt-get update && apt-get install -y wazuh-agent
fi

# Configure agent
echo "[+] Configurando agente Wazuh..."
sed -i "s/WAZUH_MANAGER_IP/${WAZUH_MANAGER}/g" /var/ossec/etc/ossec.conf
sed -i "s/WAZUH_REGISTRATION_PASSWORD/${WAZUH_REG_PASSWORD}/g" /var/ossec/etc/ossec.conf

# Register agent
echo "[+] Registrando agente con manager ${WAZUH_MANAGER}..."
/var/ossec/bin/wazuh-agent -m ${WAZUH_MANAGER} -A ${WAZUH_AGENT_NAME} -P ${WAZUH_REG_PASSWORD}

# Start agent
echo "[+] Iniciando agente Wazuh..."
/var/ossec/bin/wazuh-agent -f > /dev/null 2>&1 &

echo "[+] Wazuh agent configurado correctamente"
echo "    Manager: ${WAZUH_MANAGER}"
echo "    Agent Name: ${WAZUH_AGENT_NAME}"
echo "=========================================="
