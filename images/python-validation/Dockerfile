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
RUN chmod +x /tmp/install_base.sh /usr/local/bin/read_config.py /usr/local/bin/az_agent.sh \
    && AZP_AGENT_VERSION="$AZP_AGENT_VERSION" INSTALL_AZP_AGENT="$INSTALL_AZP_AGENT" /tmp/install_base.sh \
    && rm /tmp/install_base.sh

COPY images/python-validation/requirements.txt /etc/python-validation/requirements.txt
COPY images/python-validation/noxfile.py /etc/python-validation/noxfile.py
COPY images/python-validation/flake8.ini /etc/python-validation/flake8.ini
COPY images/python-validation/pylint.rc /etc/python-validation/pylint.rc
COPY images/python-validation/pyproject.toml /etc/python-validation/pyproject.toml
COPY images/python-validation/pytest-coverage.rc /etc/python-validation/pytest-coverage.rc
COPY images/python-validation/docker_entrypoint.sh /usr/local/bin/docker_entrypoint.sh

RUN python3 -m pip install --no-cache-dir -r /etc/python-validation/requirements.txt \
    && chmod +x /usr/local/bin/docker_entrypoint.sh

WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/docker_entrypoint.sh"]
