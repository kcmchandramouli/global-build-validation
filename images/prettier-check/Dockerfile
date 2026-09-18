FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    DOCKER_WORKDIR=/workspace \
    AZP_AGENT_DIR=/opt/az_agent

ARG AZP_AGENT_VERSION=3.248.0
ARG INSTALL_AZP_AGENT=true

COPY images/common/ci_report.sh /usr/local/lib/gbv/ci_report.sh
COPY images/common/read_config.py /usr/local/bin/read_config.py
COPY images/common/az_agent.sh /usr/local/bin/az_agent.sh
COPY images/common/install_base.sh /tmp/install_base.sh
COPY images/common/install_node.sh /tmp/install_node.sh
RUN chmod +x /tmp/install_base.sh /tmp/install_node.sh /usr/local/bin/read_config.py /usr/local/bin/az_agent.sh \
    && AZP_AGENT_VERSION="$AZP_AGENT_VERSION" INSTALL_AZP_AGENT="$INSTALL_AZP_AGENT" /tmp/install_base.sh \
    && /tmp/install_node.sh \
    && npm install --global prettier@3 \
    && rm /tmp/install_base.sh /tmp/install_node.sh

COPY images/prettier-check/.prettierrc /etc/prettier-check/.prettierrc
COPY images/prettier-check/docker_entrypoint.sh /usr/local/bin/docker_entrypoint.sh
RUN chmod +x /usr/local/bin/docker_entrypoint.sh

WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/docker_entrypoint.sh"]
