#!/usr/bin/env bash
set -e

# -------- CONFIG --------
# One-liner example:
# bash -c "$(curl -fsSL https://raw.githubusercontent.com/Beermaster90/ShellySmartEnergy/main/Initial_ShellySmartEnergy_Setup.sh)"
# Default install path uses the current working directory.
REPO_URL="${REPO_URL:-https://github.com/Beermaster90/ShellySmartEnergy.git}"
TARGET_DIR="${TARGET_DIR:-$PWD/ShellySmartEnergy}"
# Optional: pass TARGET_DIR as first arg
if [ -n "${1-}" ]; then
    TARGET_DIR="$1"
fi
# ------------------------

echo "=== ShellySmartEnergy setup starting ==="
echo "This script will update packages, install Docker/Python deps, clone the repo,"
echo "create a venv, and install Python requirements."

# 1. Update system
echo "Updating system packages..."
sudo apt-get update -y

# 1b. Install Docker if missing
if ! command -v docker >/dev/null 2>&1; then
    echo "Docker not found. Installing Docker..."
    sudo apt-get install -y docker.io
else
    echo "Docker already installed."
fi

# 1c. Add current user to docker group and refresh session
if ! getent group docker >/dev/null 2>&1; then
    sudo groupadd docker
fi
if ! id -nG "$USER" | grep -qw docker; then
    echo "Adding $USER to docker group..."
    sudo usermod -aG docker "$USER"
else
    echo "$USER already in docker group."
fi
if command -v newgrp >/dev/null 2>&1; then
    echo "Refreshing docker group membership for this session..."
    newgrp docker <<'EOF'
true
EOF
fi

# 2. Install required system packages
echo "Installing required system packages..."
sudo apt-get install -y \
    git \
    python3 \
    python3-pip \
    python3-venv

# 3. Clone repository
if [ -d "$TARGET_DIR" ]; then
    echo "Target directory already exists: $TARGET_DIR"
    echo "Skipping clone."
else
    echo "Cloning repository into $TARGET_DIR..."
    git clone "$REPO_URL" "$TARGET_DIR"
fi

cd "$TARGET_DIR"

# 4. Create virtual environment (recommended)
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# 5. Install Python dependencies
if [ -f "requirements.txt" ]; then
    echo "Installing Python requirements..."
    pip install --upgrade pip
    pip install -r requirements.txt
else
    echo "No requirements.txt found, skipping Python deps."
fi

echo "=== Setup complete ==="
echo "To activate the environment later:"
echo "source $TARGET_DIR/venv/bin/activate"
