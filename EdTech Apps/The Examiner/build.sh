#!/bin/bash

echo "Starting Linux artifact build for The Examiner using Docker..."
APP_VERSION="1.0.3" # Updated version
PROJECT_ROOT_DIR=$(pwd) # Assuming this script is in the project root

# --- Configuration ---
DOCKER_BUILDER_IMAGE_NAME="examiner-linux-builder:${APP_VERSION}"
DOCKERFILE_FOR_BUILD_ENV="Dockerfile.buildenv" # Temporary Dockerfile for the build environment
REQUIREMENTS_FILE_FOR_BUILD="new_requirements.txt" # As per your request

# --- Output paths ---
PYINSTALLER_OUTPUT_DIR_NAME="Examiner" 
HOST_DIST_DIR="${PROJECT_ROOT_DIR}/dist"
HOST_BUILD_DIR="${PROJECT_ROOT_DIR}/build" 

LINUX_PACKAGE_NAME_BASE="Examiner-linux-${APP_VERSION}" # This will now use 1.0.1
LINUX_FINAL_ARCHIVE_NAME="${LINUX_PACKAGE_NAME_BASE}.tar.gz" # This will now use 1.0.1

# --- Cleanup of previous Linux artifacts ---
echo "[BUILD.SH] Cleaning up previous Linux build artifacts..."
rm -rf "${HOST_DIST_DIR}/${PYINSTALLER_OUTPUT_DIR_NAME}"
rm -rf "${HOST_DIST_DIR}/${LINUX_PACKAGE_NAME_BASE}"  
rm -f "${PROJECT_ROOT_DIR}/${LINUX_FINAL_ARCHIVE_NAME}" 
rm -rf "${HOST_BUILD_DIR}" 
rm -f "${PROJECT_ROOT_DIR}/${DOCKERFILE_FOR_BUILD_ENV}" 
echo "[BUILD.SH] Cleanup complete."

# --- Pre-build cleanup of macOS metadata files from the project source ---
echo "[BUILD.SH] Cleaning macOS metadata files (._* and .DS_Store) from project source..."
find "${PROJECT_ROOT_DIR}" -type f \( -name '._*' -o -name '.DS_Store' \) -print -delete
echo "[BUILD.SH] macOS metadata file cleanup complete."

# --- Create Dockerfile for the Build Environment ---
echo "[BUILD.SH] Generating ${DOCKERFILE_FOR_BUILD_ENV} for Linux build environment..."
cat << EOF > "${PROJECT_ROOT_DIR}/${DOCKERFILE_FOR_BUILD_ENV}"
FROM python:3.11-slim-bullseye

# Add bullseye-backports repository for Qt6
RUN echo 'deb http://deb.debian.org/debian bullseye-backports main' > /etc/apt/sources.list.d/backports.list

# Install build essentials, PyInstaller dependencies, and dev libraries
RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential \\
    patchelf \\
    git \\
    # General X11 and graphics dev libraries
    libgl1-mesa-dev \\
    libegl1-mesa-dev \\
    libxcb1-dev \\
    libxcb-icccm4-dev \\
    libxcb-image0-dev \\
    libxcb-keysyms1-dev \\
    libxcb-randr0-dev \\
    libxcb-render-util0-dev \\
    libxcb-shape0-dev \\
    libxcb-shm0-dev \\
    libxcb-sync-dev \\
    libxcb-xfixes0-dev \\
    libxcb-xinerama0-dev \\
    libxcb-xkb-dev \\
    libxkbcommon-x11-dev \\
    libxkbcommon-dev \\
    libfontconfig1-dev \\
    libfreetype6-dev \\
    libdbus-1-dev \\
    # --- Qt6 Development Packages from Bullseye Backports ---
    # Specify the target release for backported packages
    qt6-base-dev/bullseye-backports \\
    qt6-tools-dev/bullseye-backports \\
    qt6-tools-dev-tools/bullseye-backports \\
    # Also include runtime QPA plugins and cursor lib in build env
    # qt6-qpa-plugins is a metapackage; let's install specific ones if needed or see if base-dev pulls enough.
    # For Bullseye, Qt6 plugins might be more granular or part of base.
    # Let's try with qt6-base-dev first, it often pulls in necessary runtime components.
    # If platform plugins are missing later, we might need e.g. libqt6xcbqpa6/bullseye-backports
    # For now, focusing on the dev packages. PyInstaller hooks should pick up runtime deps.
    libqt6dbus6/bullseye-backports \\
    libqt6gui6/bullseye-backports \\
    libqt6widgets6/bullseye-backports \\
    libqt6network6/bullseye-backports \\
    # libxcb-cursor0 is fine from standard Bullseye repos
    libxcb-cursor0 \\
    # --- End Qt6 Development Packages ---
    # Add any other -dev packages potentially needed by your dependencies
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build_src

COPY ${REQUIREMENTS_FILE_FOR_BUILD} ./requirements.txt
RUN echo "[BUILDENV DOCKERFILE] Installing Python packages from ${REQUIREMENTS_FILE_FOR_BUILD}..."
# Ensure pip is up-to-date and setuptools is present, as these can sometimes cause issues with specific package installs
RUN pip install --no-cache-dir --upgrade pip setuptools
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure the runtime hook is available and executable if needed.
# PyInstaller looks for it relative to the spec file path during the PyInstaller execution.
RUN chmod +x pyi_rth_qt6.py || true 

CMD ["echo", "Build environment created. PyInstaller should be run via 'docker run' with specific commands."]
EOF

if [ ! -f "${PROJECT_ROOT_DIR}/${DOCKERFILE_FOR_BUILD_ENV}" ]; then
    echo "ERROR: Failed to create ${DOCKERFILE_FOR_BUILD_ENV}!"
    exit 1
fi
echo "[BUILD.SH] ${DOCKERFILE_FOR_BUILD_ENV} created successfully."

# --- Build the Docker Image for the Build Environment ---
echo "[BUILD.SH] Building Docker image: ${DOCKER_BUILDER_IMAGE_NAME}..."
# Build specifically for linux/amd64 to ensure compatibility with older x86_64 systems
docker build --platform linux/amd64 -t "${DOCKER_BUILDER_IMAGE_NAME}" -f "${PROJECT_ROOT_DIR}/${DOCKERFILE_FOR_BUILD_ENV}" "${PROJECT_ROOT_DIR}"
if [ $? -ne 0 ]; then
    echo "ERROR: Docker image build (${DOCKER_BUILDER_IMAGE_NAME}) for platform linux/amd64 failed!"
    exit 1
fi
echo "[BUILD.SH] Docker builder image ${DOCKER_BUILDER_IMAGE_NAME} for platform linux/amd64 built successfully."

# --- Run PyInstaller inside the Docker Container ---
echo "[BUILD.SH] Running PyInstaller inside Docker container (target: linux/amd64)..."
mkdir -p "${HOST_DIST_DIR}"
mkdir -p "${HOST_BUILD_DIR}"

docker run --rm \
    -v "${PROJECT_ROOT_DIR}:/app" \
    -v "${HOST_DIST_DIR}:/app/dist" \
    -v "${HOST_BUILD_DIR}:/app/build" \
    "${DOCKER_BUILDER_IMAGE_NAME}" \
    bash -c "cd /app && python -m PyInstaller --distpath /app/dist --workpath /app/build examiner.spec"

if [ $? -ne 0 ]; then
    echo "ERROR: PyInstaller build inside Docker failed!"
    exit 1
fi

# --- Packaging the Linux Application ---
PYINSTALLER_OUTPUT_PATH="${HOST_DIST_DIR}/${PYINSTALLER_OUTPUT_DIR_NAME}"

if [ -d "${PYINSTALLER_OUTPUT_PATH}" ]; then
    echo "[BUILD.SH] Packaging Linux application from ${PYINSTALLER_OUTPUT_PATH}..."
    TARGET_PACKAGE_DIR="${HOST_DIST_DIR}/${LINUX_PACKAGE_NAME_BASE}"
    rm -rf "${TARGET_PACKAGE_DIR}" 
    mkdir -p "${TARGET_PACKAGE_DIR}"
    echo "[BUILD.SH] Copying application files from ${PYINSTALLER_OUTPUT_PATH} to ${TARGET_PACKAGE_DIR}/${PYINSTALLER_OUTPUT_DIR_NAME}/"
    cp -R "${PYINSTALLER_OUTPUT_PATH}/." "${TARGET_PACKAGE_DIR}/${PYINSTALLER_OUTPUT_DIR_NAME}/"

    if [ -f "${PROJECT_ROOT_DIR}/install.sh" ]; then
        echo "[BUILD.SH] Copying install.sh to ${TARGET_PACKAGE_DIR}/"
        cp "${PROJECT_ROOT_DIR}/install.sh" "${TARGET_PACKAGE_DIR}/"
        chmod +x "${TARGET_PACKAGE_DIR}/install.sh"

        # Create the installer .desktop file
        INSTALLER_DESKTOP_FILE_NAME="Install The Examiner.desktop"
        echo "[BUILD.SH] Creating installer .desktop file: ${TARGET_PACKAGE_DIR}/${INSTALLER_DESKTOP_FILE_NAME}"
        cat << EOF_INSTALLER_DESKTOP > "${TARGET_PACKAGE_DIR}/${INSTALLER_DESKTOP_FILE_NAME}"
[Desktop Entry]
Version=1.0
Name=Install The Examiner
Comment=Run this to install The Examiner AI Tutor
Type=Application
Exec=./install.sh
Icon=utilities-terminal
Terminal=true
Categories=Utility;
StartupNotify=true
EOF_INSTALLER_DESKTOP
        chmod +x "${TARGET_PACKAGE_DIR}/${INSTALLER_DESKTOP_FILE_NAME}"
    else
        echo "WARNING: install.sh not found in project root (${PROJECT_ROOT_DIR}). It will not be included in the archive."
    fi
    echo "[BUILD.SH] Creating archive ./${LINUX_FINAL_ARCHIVE_NAME} from directory dist/${LINUX_PACKAGE_NAME_BASE}..."
    # Exclude macOS specific metadata files and other unwanted patterns from the tar archive
    (cd "${HOST_DIST_DIR}" && tar \
        --exclude='._*' \
        --exclude='.DS_Store' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='*.pyo' \
        -czvf "../${LINUX_FINAL_ARCHIVE_NAME}" "${LINUX_PACKAGE_NAME_BASE}")
    if [ $? -eq 0 ]; then
        echo "[BUILD.SH] Linux package created successfully: ./${LINUX_FINAL_ARCHIVE_NAME}"
    else
        echo "ERROR: Failed to create Linux archive ./${LINUX_FINAL_ARCHIVE_NAME}."
    fi
    rm -rf "${TARGET_PACKAGE_DIR}"
else
    echo "ERROR: PyInstaller output directory ${PYINSTALLER_OUTPUT_PATH} not found after build!"
    exit 1
fi

rm -f "${PROJECT_ROOT_DIR}/${DOCKERFILE_FOR_BUILD_ENV}"
echo "[BUILD.SH] Linux build and packaging script finished successfully."
echo "The Linux artifact is: ./${LINUX_FINAL_ARCHIVE_NAME}"