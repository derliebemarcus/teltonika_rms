#!/usr/bin/env bash
set -euo pipefail

coverage_file="${1:-}"
if [[ -z "$coverage_file" || ! -f "$coverage_file" ]]; then
    echo "Usage: $0 <coverage.xml>" >&2
    exit 2
fi

: "${COVERALLS_REPO_TOKEN:?COVERALLS_REPO_TOKEN is required}"
: "${BUILD_NUMBER:?BUILD_NUMBER is required}"
: "${BUILD_URL:?BUILD_URL is required}"
: "${CAPTURED_SHA:?CAPTURED_SHA is required}"

case "$(uname -m)" in
    x86_64 | amd64)
        archives=(
            coveralls-linux-x86_64.tar.gz
            coveralls-linux.tar.gz
        )
        ;;
    aarch64 | arm64)
        archives=(coveralls-linux-aarch64.tar.gz)
        ;;
    *)
        echo "Unsupported architecture for Coveralls reporter: $(uname -m)" >&2
        exit 1
        ;;
esac

reporter_dir="$(mktemp -d)"
reporter_archive="$reporter_dir/coveralls.tar.gz"
trap 'rm -rf "$reporter_dir"' EXIT

reporter_downloaded=false
for archive in "${archives[@]}"; do
    for base_url in \
        "https://github.com/coverallsapp/coverage-reporter/releases/latest/download" \
        "https://coveralls.io"; do
        reporter_url="$base_url/$archive"
        echo "Downloading Coveralls reporter from $reporter_url"
        if curl \
            --fail \
            --silent \
            --show-error \
            --location \
            --retry 3 \
            --retry-all-errors \
            --output "$reporter_archive" \
            "$reporter_url"; then
            if tar -tzf "$reporter_archive" >/dev/null 2>&1; then
                reporter_downloaded=true
                break 2
            fi
            echo "Downloaded Coveralls archive is not a valid gzip tar file: $reporter_url" >&2
        fi
        rm -f "$reporter_archive"
    done
done

if [[ "$reporter_downloaded" != true ]]; then
    echo "Unable to download a valid Coveralls reporter archive." >&2
    exit 1
fi

tar -xzf "$reporter_archive" -C "$reporter_dir"
if [[ ! -f "$reporter_dir/coveralls" ]]; then
    echo "Coveralls reporter archive does not contain the coveralls binary." >&2
    exit 1
fi
chmod 700 "$reporter_dir/coveralls"

branch="${CHANGE_BRANCH:-${BRANCH_NAME:-main}}"
job_id="${BUILD_TAG:-$BUILD_NUMBER}"
export COVERALLS_GIT_COMMIT="$CAPTURED_SHA"
export COVERALLS_EVENT_TYPE="push"
if [[ -n "${CHANGE_ID:-}" ]]; then
    export COVERALLS_EVENT_TYPE="pull_request"
fi

args=(
    report
    "$coverage_file"
    --format=cobertura
    --base-path="$PWD"
    --build-number="$BUILD_NUMBER"
    --service-name=jenkins
    --service-job-id="$job_id"
    --service-build-url="$BUILD_URL"
    --service-job-url="${BUILD_URL}console"
    --service-branch="$branch"
)

if [[ -n "${CHANGE_ID:-}" ]]; then
    args+=(--service-pull-request="$CHANGE_ID")
fi

"$reporter_dir/coveralls" "${args[@]}"
