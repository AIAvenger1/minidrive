#!/usr/bin/env bash
set -euo pipefail
API="${API:-http://localhost:3000}"
U="${U:-bohdan}"; P="${P:-secret123}"
TOKEN=$(curl -sf -X POST "$API/auth/login" -H 'content-type: application/json' -d "{\"username\":\"$U\",\"password\":\"$P\"}" | python3 -c 'import sys,json;print(json.load(sys.stdin)["accessToken"])')
echo "login ok"
printf 'class Smoke {}\n' > /tmp/Smoke.cs
ID=$(curl -sf -X POST "$API/files" -H "Authorization: Bearer $TOKEN" -F file=@/tmp/Smoke.cs | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
echo "upload ok ($ID)"
curl -sf "$API/files" -H "Authorization: Bearer $TOKEN" | python3 -c 'import sys,json;print("list ok:", [f["name"] for f in json.load(sys.stdin)])'
curl -sf "$API/files/$ID/content" -H "Authorization: Bearer $TOKEN" | head -c 40; echo; echo "download ok"
curl -sf -X DELETE "$API/files/$ID" -H "Authorization: Bearer $TOKEN" -o /dev/null -w "delete %{http_code}\n"
