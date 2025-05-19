#!/bin/bash

echo "Starting Linux artifact build for The Examiner using Docker..."
APP_VERSION="1.0.0" # Or read from a configuration file
PROJECT_ROOT_DIR=$(pwd) # Assuming this script is in the project root

# --- Configuration ---
DOCKER_BUILDER_IMAGE_NAME="examiner-linux-builder:${APP_VERSION}"
DOCKERFILE_FOR_BUILD_ENV="Dockerfile.buildenv" # Temporary Dockerfile for the build environment
REQUIREMENTS_FILE_FOR_BUILD="new_requirements.txt" # As per your request

# --- Output paths ---
PYINSTALLER_OUTPUT_DIR_NAME="Examiner" 
HOST_DIST_DIR="${PROJECT_ROOT_DIR}/dist"
HOST_BUILD_DIR="${PROJECT_ROOT_DIR}/build" 

LINUX_PACKAGE_NAME_BASE="Examiner-linux-${APP_VERSION}"
LINUX_FINAL_ARCHIVE_NAME="${LINUX_PACKAGE_NAME_BASE}.tar.gz"

# --- Cleanup of previous Linux artifacts ---
echo "[BUILD.SH] Cleaning up previous Linux build artifacts..."
rm -rf "${HOST_DIST_DIR}/${PYINSTALLER_OUTPUT_DIR_NAME}"
rm -rf "${HOST_DIST_DIR}/${LINUX_PACKAGE_NAME_BASE}"  
rm -f "${PROJECT_ROOT_DIR}/${LINUX_FINAL_ARCHIVE_NAME}" 
rm -rf "${HOST_BUILD_DIR}" 
rm -f "${PROJECT_ROOT_DIR}/${DOCKERFILE_FOR_BUILD_ENV}" 
echo "[BUILD.SH] Cleanup complete."

# --- Create Dockerfile for the Build Environment ---
echo "[BUILD.SH] Generating ${DOCKERFILE_FOR_BUILD_ENV} for Linux build environment..."
cat << EOF > "${PROJECT_ROOT_DIR}/${DOCKERFILE_FOR_BUILD_ENV}"
FROM python:3.11-bookworm

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
    # --- Corrected Qt6 Development Packages for Bookworm ---
    qt6-base-dev \\
    qt6-tools-dev \\
    qt6-tools-dev-tools \\
    # Also include runtime QPA plugins and cursor lib in build env
    # as PyInstaller might inspect them or need them for hooks.
    qt6-qpa-plugins \\
    libxcb-cursor0 \\
    # --- End Qt6 Development Packages ---
    # Add any other -dev packages potentially needed by your dependencies
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build_src

COPY ${REQUIREMENTS_FILE_FOR_BUILD} ./requirements.txt
RUN echo "[BUILDENV DOCKERFILE] Installing Python packages from ${REQUIREMENTS_FILE_FOR_BUILD}..."
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
# Build for the host architecture. If on ARM Mac, this will be ARM.
# If you needed an x86_64 Linux build specifically, you'd add --platform linux/amd64 here.
docker build -t "${DOCKER_BUILDER_IMAGE_NAME}" -f "${PROJECT_ROOT_DIR}/${DOCKERFILE_FOR_BUILD_ENV}" "${PROJECT_ROOT_DIR}"
if [ $? -ne 0 ]; then
    echo "ERROR: Docker image build (${DOCKER_BUILDER_IMAGE_NAME}) failed!"
    exit 1
fi
echo "[BUILD.SH] Docker builder image ${DOCKER_BUILDER_IMAGE_NAME} built successfully."

# --- Run PyInstaller inside the Docker Container ---
echo "[BUILD.SH] Running PyInstaller inside Docker container..."
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
    echo "[BUILD.SH] Copying application files from ${PYINSTALLER_OUTPUT_PATH} to ${TARGET_PACKAGE_DIR}/"
    cp -R "${PYINSTALLER_OUTPUT_PATH}/." "${TARGET_PACKAGE_DIR}/"
    if [ -f "${PROJECT_ROOT_DIR}/install.sh" ]; then
        echo "[BUILD.SH] Copying install.sh to ${TARGET_PACKAGE_DIR}/"
        cp "${PROJECT_ROOT_DIR}/install.sh" "${TARGET_PACKAGE_DIR}/"
        chmod +x "${TARGET_PACKAGE_DIR}/install.sh"
    else
        echo "WARNING: install.sh not found in project root (${PROJECT_ROOT_DIR}). It will not be included in the archive."
    fi
    echo "[BUILD.SH] Creating archive ./${LINUX_FINAL_ARCHIVE_NAME} from directory dist/${LINUX_PACKAGE_NAME_BASE}..."
    (cd "${HOST_DIST_DIR}" && tar -czvf "../${LINUX_FINAL_ARCHIVE_NAME}" "${LINUX_PACKAGE_NAME_BASE}")
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