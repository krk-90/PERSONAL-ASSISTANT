#!/bin/sh
set -eu

exec /usr/bin/supervisord -c /etc/supervisor/conf.d/personal-assistant.conf