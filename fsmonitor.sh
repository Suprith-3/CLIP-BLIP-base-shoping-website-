#!/bin/sh
echo "=== Running Render Memory Optimization Push ===" > push_log.txt
git config --unset core.fsmonitor >> push_log.txt 2>&1
git add . >> push_log.txt 2>&1
git commit -m "Optimize memory for Render: conditionally disable vision tower of CLIP at runtime" >> push_log.txt 2>&1
git push origin main >> push_log.txt 2>&1
rm -f fsmonitor.sh
echo "=== Finished ===" >> push_log.txt
