docker network create everyone-runner || true
docker run -dt \
    --net everyone-runner \
    --name runner-admin \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v `pwd`:/workspace/runner-admin \
    -w /workspace/runner-admin \
    -u 1000 \
    --entrypoint "" \
    mcr.microsoft.com/devcontainers/universal:linux python main.py
