#!/bin/bash
mkdir -p /opt/clearml/config
echo "apiserver.default_company: default" > /opt/clearml/config/apiserver.conf
exec "$@"

