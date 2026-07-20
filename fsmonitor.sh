#!/bin/sh
git config --unset core.fsmonitor
git add -A
git commit -m "Clean up temporary scripts"
git push origin main
rm -f fsmonitor.sh
