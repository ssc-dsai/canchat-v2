#!/usr/bin/env bash
# Stop on first error
set -e

# Get the input directory (default to empty)
searchDir="${1:-}"

# Define target directory
reportDir="playwright-report"

# Function: ensure unzip is installed
ensure_unzip_installed() {
    if command -v unzip >/dev/null 2>&1; then
        return
    fi

    echo "⚙️ 'unzip' not found — attempting to install it..."
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update -y && sudo apt-get install -y unzip
    elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y unzip
    elif command -v yum >/dev/null 2>&1; then
        sudo yum install -y unzip
    elif command -v apk >/dev/null 2>&1; then
        sudo apk add unzip
    elif command -v zypper >/dev/null 2>&1; then
        sudo zypper install -y unzip
    else
        echo "❌ Could not automatically install 'unzip'. Please install it manually."
        exit 1
    fi
}

if [[ -n "$searchDir" ]]; then
    # Find the most recent zip file matching the pattern in the given directory
    latestZip=$(ls -t "$searchDir"/playwright-report-*.zip 2>/dev/null | head -n 1 || true)

    if [[ -z "$latestZip" ]]; then
        echo "❌ No matching 'playwright-report-*.zip' files found in: $searchDir"
        exit 1
    fi

    echo "📦 Found latest report archive: $latestZip"

    # Remove the old report directory if it exists
    if [[ -d "$reportDir" ]]; then
        echo "🗑️ Removing existing directory: $reportDir"
        rm -rf "$reportDir"
    fi

    mkdir -p "$reportDir"
    ensure_unzip_installed

    echo "📂 Extracting $(basename "$latestZip") to $reportDir..."
    unzip -q "$latestZip" -d "$reportDir"
else
    echo "ℹ️ No directory provided — using existing '$reportDir' folder."
    if [[ ! -d "$reportDir" ]]; then
        echo "❌ No existing '$reportDir' directory found."
        exit 1
    fi
fi

# Show the Playwright report
echo "🚀 Launching Playwright report..."
npx playwright show-report "$reportDir"
