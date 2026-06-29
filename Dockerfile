FROM odoo:17.0

LABEL maintainer="Banco de la Nación - TI"
LABEL description="Odoo Banco de la Nación con módulos SBS y Wazuh SIEM"
LABEL version="1.0.0"

USER root

# Install system dependencies for Wazuh agent and utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg2 \
    lsb-release \
    python3-pip \
    python3-requests \
    python3-jinja2 \
    python3-reportlab \
    python3-openpyxl \
    net-tools \
    procps \
    sudo \
    jq \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Install Wazuh repository
RUN curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH | gpg --dearmor > /usr/share/keyrings/wazuh.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main" > /etc/apt/sources.list.d/wazuh.list

# Install Wazuh agent
RUN apt-get update && apt-get install -y wazuh-agent && rm -rf /var/lib/apt/lists/*

# Copy custom addons
COPY odoo/custom_addons /mnt/extra-addons

# Copy Odoo configuration
COPY odoo/config/odoo.conf /etc/odoo/odoo.conf

# Copy Wazuh configuration files
COPY wazuh/agent/ossec.conf /var/ossec/etc/ossec.conf
COPY wazuh/decoders/odoo_decoder.xml /var/ossec/etc/decoders/odoo_decoder.xml
COPY wazuh/rules/odoo_rules.xml /var/ossec/etc/rules/odoo_rules.xml

# Copy scripts
COPY scripts/entrypoint.sh /entrypoint.sh
COPY scripts/setup_wazuh.sh /usr/local/bin/setup_wazuh.sh
COPY scripts/init_db.sh /usr/local/bin/init_db.sh

# Create necessary directories
RUN mkdir -p /var/log/odoo && \
    mkdir -p /mnt/extra-addons && \
    mkdir -p /var/odoo/sbs_reports && \
    chmod +x /entrypoint.sh && \
    chmod +x /usr/local/bin/setup_wazuh.sh && \
    chmod +x /usr/local/bin/init_db.sh

# Fix permissions
RUN chown -R odoo:odoo /var/log/odoo /mnt/extra-addons /var/odoo/sbs_reports /etc/odoo/odoo.conf

ENTRYPOINT ["/entrypoint.sh"]
CMD ["odoo"]
