FROM mcr.microsoft.com/devcontainers/universal:linux

RUN set -eux; \
    TAG_NAME=$(curl -s https://api.github.com/repos/tsl0922/ttyd/releases/latest | jq -r .tag_name); \
    wget -q https://github.com/tsl0922/ttyd/releases/download/${TAG_NAME}/ttyd.i686 -O /usr/local/bin/ttyd; \
    chmod +x /usr/local/bin/ttyd; \
    ttyd --version

RUN set -eux; \
    npm install -g ts-node rtail; \
    mkdir /workspace; \
    chown 1000:1000 /workspace; \
    chmod 777 /workspace;

ENTRYPOINT []