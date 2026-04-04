#!/bin/bash
# ============================================
# SignFlow DMG Build Script
# ============================================
# This script automates the entire DMG build process
# Usage: ./build_dmg.sh [options]
# Options:
#   --clean     : Clean previous builds first
#   --no-dmg    : Only build .app, skip DMG creation
#   --sign      : Sign the app (requires CODESIGN_IDENTITY env)
#   --install   : Install required dependencies first
# ============================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================
# Configuration
# ============================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SPEC_FILE="$SCRIPT_DIR/SignFlow.spec"
BUILD_DIR="$SCRIPT_DIR/build"
DIST_DIR="$SCRIPT_DIR/dist"
CRT_DIR="$SCRIPT_DIR/crt"

# ============================================
# Parse Arguments
# ============================================
CLEAN_BUILD=false
SKIP_DMG=false
SIGN_APP=false
INSTALL_DEPS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --clean)
            CLEAN_BUILD=true
            shift
            ;;
        --no-dmg)
            SKIP_DMG=true
            shift
            ;;
        --sign)
            SIGN_APP=true
            shift
            ;;
        --install)
            INSTALL_DEPS=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--clean] [--no-dmg] [--sign] [--install]"
            exit 1
            ;;
    esac
done

# ============================================
# Helper Functions
# ============================================
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    log_info "Checking requirements..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 not found. Please install Python 3.10+"
        exit 1
    fi
    
    # Check if venv exists and activate
    VENV_PATH="$PROJECT_ROOT/.venv-build"
    if [ -d "$VENV_PATH" ]; then
        log_info "Activating virtual environment..."
        source "$VENV_PATH/bin/activate"
    else
        log_warning "Virtual environment not found at $VENV_PATH"
        log_info "Using system Python"
    fi
    
    # Check PyInstaller
    if ! python3 -c "import PyInstaller" 2>/dev/null; then
        log_warning "PyInstaller not installed. Installing..."
        pip3 install pyinstaller
    fi
    
    # Check required packages
    log_info "Checking required packages..."
    REQUIRED_PACKAGES=("mediapipe" "torch" "cv2" "numpy" "packaging")
    for pkg in "${REQUIRED_PACKAGES[@]}"; do
        if ! python3 -c "import $pkg" 2>/dev/null; then
            log_warning "Package '$pkg' not installed. Installing..."
            pip3 install "$pkg"
        fi
    done
    
    log_success "Requirements check passed"
}

clean_build() {
    if [ "$CLEAN_BUILD" = true ]; then
        log_info "Cleaning previous builds..."
        rm -rf "$BUILD_DIR"
        rm -rf "$DIST_DIR"
        log_success "Build directories cleaned"
    fi
}

install_dependencies() {
    if [ "$INSTALL_DEPS" = true ]; then
        log_info "Installing dependencies..."
        
        # Activate venv if exists
        VENV_PATH="$PROJECT_ROOT/.venv-build"
        if [ -d "$VENV_PATH" ]; then
            source "$VENV_PATH/bin/activate"
        fi
        
        # Install from requirements if exists
        if [ -f "$PROJECT_ROOT/Overlay/requirements.txt" ]; then
            log_info "Installing from requirements.txt..."
            pip3 install -r "$PROJECT_ROOT/Overlay/requirements.txt"
        fi
        
        # Install additional build requirements
        log_info "Installing PyInstaller and build dependencies..."
        pip3 install pyinstaller
        
        log_success "Dependencies installed"
    fi
}

# ============================================
# Main Build Process
# ============================================

echo ""
echo "========================================"
echo "  SignFlow DMG Build Script"
echo "========================================"
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Step 1: Check requirements
check_requirements

# Step 2: Install dependencies if requested
if [ "$INSTALL_DEPS" = true ]; then
    install_dependencies
fi

# Step 3: Clean if requested
clean_build

# Step 3: Create build/dist directories
mkdir -p "$BUILD_DIR"
mkdir -p "$DIST_DIR"

# Step 4: Run PyInstaller
log_info "Building SignFlow.app with PyInstaller..."
cd "$SCRIPT_DIR"

python3 -m PyInstaller "$SPEC_FILE" --noconfirm --clean

if [ -d "$DIST_DIR/SignFlow.app" ]; then
    log_success "App bundle created: $DIST_DIR/SignFlow.app"
else
    log_error "Build failed - no app bundle found"
    exit 1
fi

# Step 5: Optional - Sign the app
if [ "$SIGN_APP" = true ]; then
    if [ -z "$CODESIGN_IDENTITY" ]; then
        log_error "CODESIGN_IDENTITY environment variable not set"
        log_info "Set it with: export CODESIGN_IDENTITY='Developer ID Application: Name (TEAMID)'"
        exit 1
    fi
    
    log_info "Signing app with identity: $CODESIGN_IDENTITY"
    codesign --force --deep --sign "$CODESIGN_IDENTITY" --options runtime "$DIST_DIR/SignFlow.app"
    log_success "App signed"
fi

# Step 6: Create DMG (unless skipped)
if [ "$SKIP_DMG" = false ]; then
    log_info "Creating DMG..."
    cd "$CRT_DIR"
    
    if [ -f "./make_product_dmg.sh" ]; then
        chmod +x ./make_product_dmg.sh
        # Pass the actual app path (from mac_builder/dist) and desired DMG output location
        APP_INPUT="$DIST_DIR/SignFlow.app"
        DMG_OUTPUT="$DIST_DIR/SignFlow-mac.dmg"
        ./make_product_dmg.sh "$APP_INPUT" "$DMG_OUTPUT"
        
        # Check if DMG was created
        if [ -f "$DMG_OUTPUT" ]; then
            log_success "DMG created: $DMG_OUTPUT"
        else
            log_warning "DMG script ran but no DMG found at expected location"
        fi
    else
        log_warning "make_product_dmg.sh not found, creating simple DMG..."
        hdiutil create -volname "SignFlow" -srcfolder "$DIST_DIR/SignFlow.app" -ov -format UDZO "$DIST_DIR/SignFlow-mac.dmg"
        log_success "Simple DMG created: $DIST_DIR/SignFlow-mac.dmg"
    fi
fi

# ============================================
# Summary
# ============================================
echo ""
echo "========================================"
echo "  Build Complete!"
echo "========================================"
echo ""
echo "Output files:"
echo "  App:   $DIST_DIR/SignFlow.app"

if [ "$SKIP_DMG" = false ]; then
    echo "  DMG:   $DIST_DIR/SignFlow-mac.dmg"
fi

echo ""
echo "To run the app:"
echo "  open $DIST_DIR/SignFlow.app"
echo ""