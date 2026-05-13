#!/bin/bash
cd /opt/vavabot4botscup
git stash 2>/dev/null
git pull origin main 2>&1 || true
git stash drop 2>/dev/null || true
