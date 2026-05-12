#!/bin/bash
export GIT_SSH_COMMAND="ssh -i /root/.ssh/botaovava_deploy -F /dev/null -o StrictHostKeyChecking=no -o IdentitiesOnly=yes"
cd /opt/vavabot4botscup
git pull origin main 2>&1 || true
