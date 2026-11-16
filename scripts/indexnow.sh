#!/usr/bin/env bash
# Tells IndexNow (Bing, Yandex, Naver, Seznam, Yep; not Google) which URLs changed. Run after the deploy is live,
# never before: the engines fetch the key file and the pages right away.
#
#   ./scripts/indexnow.sh                      # pages whose index.html changed in the last commit (HEAD~1..HEAD)
#   ./scripts/indexnow.sh abc123..HEAD      # pages changed in a git range
#   ./scripts/indexnow.sh https://icgor.mm-apps.com/ https://icgor.mm-apps.com/beslenme-skoru/
#   DRY_RUN=1 ./scripts/indexnow.sh …          # print the request, send nothing
#
# The key is public by design (build.py INDEXNOW_KEY; the build writes /<key>.txt). 200 or 202 = accepted.
set -euo pipefail
cd "$(dirname "$0")/.."

read -r BASE KEY < <(python3 -c 'import build; print(build.SITE_URL.rstrip("/"), build.INDEXNOW_KEY)')
HOST="${BASE#https://}"

urls=()
if [[ $# -gt 0 && "$1" == https://* ]]; then
  urls=("$@")
else
  range="${1:-HEAD~1..HEAD}"
  while IFS= read -r file; do
    [[ "$file" == *index.html ]] || continue
    [[ -f "$file" ]] || continue                       # deleted pages are left to the crawlers (404)
    urls+=("$BASE/${file%index.html}")
  done < <(git diff --name-only "$range" -- '*index.html')
fi

if [[ ${#urls[@]} -eq 0 ]]; then
  echo "no changed pages"
  exit 0
fi

body="$(python3 -c 'import json, sys; print(json.dumps({"host": sys.argv[1], "key": sys.argv[2], "keyLocation": f"https://{sys.argv[1]}/{sys.argv[2]}.txt", "urlList": sys.argv[3:]}))' "$HOST" "$KEY" "${urls[@]}")"

if [[ -n "${DRY_RUN:-}" ]]; then
  echo "$body"
  exit 0
fi

# The key file must already be live, or every engine rejects the request.
curl -fsS -o /dev/null "$BASE/$KEY.txt" || { echo "key file $BASE/$KEY.txt is not reachable; deploy first" >&2; exit 1; }
code="$(curl -sS -X POST "https://api.indexnow.org/indexnow" -H "Content-Type: application/json; charset=utf-8" \
  --data "$body" -o /dev/null -w "%{http_code}")"
echo "IndexNow: HTTP $code for ${#urls[@]} URL(s)"
[[ "$code" == 200 || "$code" == 202 ]]
