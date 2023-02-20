#!/bin/sh
set -e

if [ ! -f data/.initialized ]; then
    pip install -r /workspace/runner-admin/requirements.txt
fi

if [ ! -f data/public_key.asc ]; then
    gpg --quick-gen-key --batch --passphrase "" "${USER:-localuser}@${HOSTNAME:-localhost}"
    gpg --export --armor "${USER:-localuser}@${HOSTNAME:-localhost}" > data/public_key.asc
fi

exec gunicorn -w 4 -b 0.0.0.0 main:app
