#!/bin/bash

# Smart Git Commit Tool - System-wide Installation Script
# This script installs the tool globally so you can use it from anywhere

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if running as root for system-wide installation
check_permissions() {
    if [[ $EUID -eq 0 ]]; then
        INSTALL_DIR="/usr/local/bin"
        CONFIG_DIR="/etc/smart-commit"
        print_info "Installing system-wide (requires root)"
    else
        INSTALL_DIR="$HOME/.local/bin"
        CONFIG_DIR="$HOME/.config/smart-commit"
        print_info "Installing for current user only"

        # Create user bin directory if it doesn't exist
        mkdir -p "$INSTALL_DIR"

        # Add to PATH if not already there
        if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
            print_warning "$INSTALL_DIR is not in your PATH"
            echo "Add this line to your ~/.bashrc or ~/.zshrc:"
            echo -e "${BLUE}export PATH=\"\$HOME/.local/bin:\$PATH\"${NC}"
            echo
        fi
    fi
}

# Check dependencies
check_dependencies() {
    print_step "Checking dependencies..."

    # Check Python 3
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed."
        exit 1
    fi
    print_info "Python 3: $(python3 --version)"

    # Check pip
    if ! command -v pip3 &> /dev/null && ! command -v pip &> /dev/null; then
        print_error "pip is required but not installed."
        exit 1
    fi

    # Check git
    if ! command -v git &> /dev/null; then
        print_error "Git is required but not installed."
        exit 1
    fi
    print_info "Git: $(git --version)"
}

# Install Python dependencies
install_python_deps() {
    print_step "Installing Python dependencies..."

    if command -v pip3 &> /dev/null; then
        pip3 install requests
    else
        pip install  requests
    fi

    print_info "Python dependencies installed"
}

# Create the main executable script
create_executable() {
    print_step "Creating executable script..."

    # Get the absolute path of the current directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    # Create the executable wrapper
    cat > "$INSTALL_DIR/smart-commit" << EOF
#!/usr/bin/env python3
"""
Smart Git Commit Tool - Global Executable
Installed from: $SCRIPT_DIR
"""

import sys
import os

# Add the installation directory to Python path
sys.path.insert(0, '$CONFIG_DIR')

# Import and run the main script
try:
    from smart_commit_main import main
    sys.exit(main())
except ImportError as e:
    print(f"Error: Could not import smart_commit_main: {e}")
    print(f"Installation may be corrupted. Please reinstall.")
    sys.exit(1)
EOF

    chmod +x "$INSTALL_DIR/smart-commit"
    print_info "Created executable: $INSTALL_DIR/smart-commit"
}

# Copy the main script
copy_main_script() {
    print_step "Installing main script..."

    mkdir -p "$CONFIG_DIR"

    # Copy the main Python script with a different name
    cp "smart_commit.py" "$CONFIG_DIR/smart_commit_main.py"

    # Copy other files
    cp "requirements.txt" "$CONFIG_DIR/"
    cp "README.md" "$CONFIG_DIR/"

    print_info "Main script installed to: $CONFIG_DIR"
}

# Create alias suggestions
create_aliases() {
    print_step "Creating convenient aliases..."

    ALIAS_FILE="$CONFIG_DIR/aliases.sh"
    cat > "$ALIAS_FILE" << 'EOF'
# Smart Commit Tool Aliases
# Add these to your ~/.bashrc or ~/.zshrc for convenience

# Main command
alias sc='smart-commit'

# Quick commit with auto-stage
alias sca='smart-commit -a'

# Quick commit with auto-stage and push
alias scap='smart-commit -a -p'

# Dry run
alias scd='smart-commit --dry-run'

# Custom message with auto-stage
alias scm='smart-commit -a -m'

# Interactive mode (same as sc, but explicit)
alias sci='smart-commit'
EOF

    print_info "Aliases created in: $ALIAS_FILE"
    echo
    print_warning "To use convenient aliases, add this to your shell config:"
    echo -e "${BLUE}source $ALIAS_FILE${NC}"
}

# Create uninstall script
create_uninstaller() {
    print_step "Creating uninstaller..."

    cat > "$CONFIG_DIR/uninstall.sh" << EOF
#!/bin/bash
# Smart Git Commit Tool - Uninstaller

echo "Removing Smart Git Commit Tool..."

# Remove executable
rm -f "$INSTALL_DIR/smart-commit"

# Remove configuration directory
rm -rf "$CONFIG_DIR"

echo "Smart Git Commit Tool has been uninstalled."
echo "You may want to remove any aliases from your shell configuration."
EOF

    chmod +x "$CONFIG_DIR/uninstall.sh"
    print_info "Uninstaller created: $CONFIG_DIR/uninstall.sh"
}

# Main installation process
main() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║              Smart Git Commit Tool Installer                ║"
    echo "║                   Global Installation                        ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    check_permissions
    check_dependencies
    install_python_deps
    copy_main_script
    create_executable
    create_aliases
    create_uninstaller

    echo
    print_success "Installation completed successfully!"
    echo
    echo -e "${CYAN}Usage:${NC}"
    echo -e "  ${BLUE}smart-commit${NC}          # Interactive mode"
    echo -e "  ${BLUE}smart-commit -a${NC}       # Auto-stage and commit"
    echo -e "  ${BLUE}smart-commit -a -p${NC}    # Auto-stage, commit, and push"
    echo -e "  ${BLUE}smart-commit --dry-run${NC} # See what would happen"
    echo
    echo -e "${CYAN}Setup your Gemini API key:${NC}"
    echo -e "  ${BLUE}export GEMINI_API_KEY=\"your-api-key-here\"${NC}"
    echo
    echo -e "${CYAN}Add convenient aliases:${NC}"
    echo -e "  ${BLUE}source $ALIAS_FILE${NC}"
    echo
    echo -e "${CYAN}To uninstall:${NC}"
    echo -e "  ${BLUE}$CONFIG_DIR/uninstall.sh${NC}"
    echo

    if [[ $EUID -ne 0 ]] && [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
        print_warning "Don't forget to add $INSTALL_DIR to your PATH!"
    fi
}

# Run the installer
main "$@"
