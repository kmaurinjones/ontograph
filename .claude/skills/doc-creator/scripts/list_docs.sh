#!/usr/bin/env bash
# List current documentation structure without reading file contents

set -euo pipefail

# Check if docs/ directory exists
if [ ! -d "docs" ]; then
    echo "No docs/ directory found in current project."
    exit 0
fi

echo "Current documentation structure:"
echo "================================"
echo ""

# Use ls -R to list recursively, but format cleanly
ls -R docs/ | awk '
/:$/&&f{s=$0;f=0}
/:$/&&!f{sub(/:$/,"");s=$0;f=1;next}
NF&&f{ print s"/"$0 }
'

echo ""
echo "================================"
echo "Total documentation files: $(find docs -type f -name '*.md' | wc -l | tr -d ' ')"
