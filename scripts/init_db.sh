#!/bin/bash
# ==========================================
# Odoo BDN - Database Initialization Script
# ==========================================

set -e

ODOO_URL="${ODOO_URL:-http://localhost:8069}"
DB_NAME="${DB_NAME:-odoo_banco_nacion}"
DB_USER="${DB_USER:-odoo}"
DB_PASSWORD="${DB_PASSWORD:-banco_nacion_sbs_2026}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin_sbs_banco_nacion_2026}"

echo "=========================================="
echo "  Inicialización de Base de Datos Odoo"
echo "  Banco de la Nación"
echo "=========================================="

echo "[+] Creando base de datos '${DB_NAME}'..."
curl -X POST "${ODOO_URL}/web/database/create" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "master_pwd=${ADMIN_PASSWORD}" \
    -d "name=${DB_NAME}" \
    -d "login=${DB_USER}" \
    -d "password=${DB_PASSWORD}" \
    -d "lang=es_PE" \
    -d "country_code=PE" \
    -d "phone="

echo "[+] Base de datos '${DB_NAME}' creada correctamente"

echo "[+] Instalando módulo banco_nacion..."
curl -X POST "${ODOO_URL}/web/database/install_module" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "master_pwd=${ADMIN_PASSWORD}" \
    -d "name=${DB_NAME}" \
    -d "module=banco_nacion"

echo "[+] Módulo banco_nacion instalado"

echo "[+] Instalando módulos base del banco..."
MODULES=("sale" "purchase" "stock" "account" "account_accountant")

for module in "${MODULES[@]}"; do
    echo "    Instalando ${module}..."
    curl -X POST "${ODOO_URL}/web/database/install_module" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "master_pwd=${ADMIN_PASSWORD}" \
        -d "name=${DB_NAME}" \
        -d "module=${module}" 2>/dev/null || echo "    [!] ${module} ya instalado o no disponible"
done

echo "=========================================="
echo "  Inicialización completada"
echo "  URL: ${ODOO_URL}"
echo "  DB: ${DB_NAME}"
echo "  Usuario admin: ${DB_USER}"
echo "=========================================="
