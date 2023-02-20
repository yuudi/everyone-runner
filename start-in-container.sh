docker network create everyone-runner || true
docker run -dt \
    --net everyone-runner \
    --name runner-admin \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v `pwd`:/workspace/runner-admin \
    -w /workspace/runner-admin \
    -u 1000 \
    --entrypoint "" \
    --restart unless-stopped \
    -e BASE_IMAGE="mcr.microsoft.com/devcontainers/universal:linux" \
    -e BASE_URL="http://127.0.0.1:5000" \
    -e API_SECRET="your-secret" \
    mcr.microsoft.com/devcontainers/universal:linux /workspace/runner-admin/entry.sh
