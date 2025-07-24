#!/usr/bin/env bash
set -ue -o pipefail

readonly BASE_DIR="$( cd "$( echo "${BASH_SOURCE[0]%/*}" )"; pwd )"
readonly OUT_DIR=${BASE_DIR}/build
readonly UI_DIR=${BASE_DIR}/ui
readonly OUT_FILE=${OUT_DIR}/dashboard
readonly API_SERVER_DIR=${BASE_DIR}/apiserver
mkdir -p "${OUT_DIR}"

if ! command -v npm -version &> /dev/null
then
  echo "npm could not be found"
  exit 1
fi

if ! command -v go version &> /dev/null
then
  echo "go language (the go executable) could not be found"
  exit 1
fi

(
cd "$UI_DIR"
npm ci
npm run build
rm -rf "${API_SERVER_DIR}/dist"
tar cz dist | tar -C "${API_SERVER_DIR}" -xz
)

cd "$BASE_DIR"
rm -f "${OUT_FILE}"

go build -o "${OUT_FILE}"

if [[ ! -f "${OUT_FILE}" ]]; then
  echo "Build Failed: file ${OUT_FILE} not found."
  exit 1
fi

echo "open-threads-reminder dashboard binary generated successfully at ${OUT_FILE}"
