FROM apache/airflow:2.9.3

USER root

# Install modern Docker CLI from Docker's official repo (not Debian's docker.io)
ARG DOCKER_CLI_VERSION=5:26.1.4-1~debian.12~bookworm
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates curl gnupg lsb-release; \
    install -m 0755 -d /etc/apt/keyrings; \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg; \
    chmod a+r /etc/apt/keyrings/docker.gpg; \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" \
      > /etc/apt/sources.list.d/docker.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends docker-ce-cli="${DOCKER_CLI_VERSION}"; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*

USER airflow
