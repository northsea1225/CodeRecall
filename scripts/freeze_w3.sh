#!/bin/bash
set -e
echo '=== W3 Freeze Check ==='
echo '[1/4] Backend pytest...'
cd /Users/hfish/Claude_chat/协同码力/backend
.venv/bin/python -m pytest -q
echo '[2/4] Frontend vitest...'
cd /Users/hfish/Claude_chat/协同码力/frontend
npx vitest run
echo '[3/4] TypeScript check...'
npx tsc --noEmit
echo '[4/4] Production build...'
npm run build
echo '=== W3 Freeze: ALL GREEN ==='
