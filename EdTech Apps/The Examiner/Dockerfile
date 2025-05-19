FROM python:3.11-bookworm
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    patchelf \
    git \
    cmake \
    # X11 and graphics libraries - comprehensive list
    libgl1-mesa-dev \
    libegl1-mesa-dev \
    libxcb1-dev \
    libxcb-icccm4-dev \
    libxcb-image0-dev \
    libxcb-keysyms1-dev \
    libxcb-randr0-dev \
    libxcb-render-util0-dev \
    libxcb-shape0-dev \
    libxcb-shm0-dev \
    libxcb-sync-dev \
    libxcb-cursor0 \
    libxcb-xfixes0-dev \
    libxcb-xinerama0-dev \
    libxcb-xkb-dev \
    libxkbcommon-x11-dev \
    libxkbcommon-dev \
    libfontconfig1-dev \
    libfreetype6-dev \
    libdbus-1-dev \
    # Qt6 packages - critical for PySide6
    qt6-base-dev \
    qt6-tools-dev \
    qt6-tools-dev-tools \
    qt6-qpa-plugins \
    # Explicitly adding Qt runtime libraries
    libqt6gui6 \
    libqt6widgets6 \
    libqt6dbus6 \
    libqt6network6 \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file that includes PyInstaller and all dependencies
COPY new_requirements.txt ./requirements.txt

# Set build-time environment variables if any package (e.g., llama-cpp-python)
# needs to be compiled from source and requires specific linking.
# Using pthreads for BLAS linking consistency if llama-cpp-python compiles.
ENV CC="gcc -pthread"
ENV CXX="g++ -pthread"
ENV LDFLAGS="-pthread"
# CMAKE_ARGS might be needed for llama-cpp-python if it compiles and default BLAS setup is not desired
# e.g., ENV CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS"
# However, new_requirements.txt points to hashed wheels, likely pre-compiled.

# Install Python packages with flags to bypass hash verification
RUN pip install --no-cache-dir --no-deps --ignore-installed -r requirements.txt

# Unset build-time env vars if they are not needed for PyInstaller itself
ENV CC=""
ENV CXX=""
ENV LDFLAGS=""

# Copy the entire project context into the Docker image.
# This ensures all source files, spec file, assets, etc., are available.
COPY . .

# The PyInstaller command will be run via `docker run` as specified in the updated build.sh

# Add this to your Dockerfile after installing requirements
RUN pip install --no-cache-dir llama-cpp-python && \
    python3 -c "import llama_cpp; import os; \
    print(f'LLAMA-CPP DIR: {os.path.dirname(llama_cpp.__file__)}'); \
    found_libs = []; \
    for root, _, files in os.walk(os.path.dirname(llama_cpp.__file__)): \
        for file in files: \
            if file.endswith(('.so', '.dylib', '.dll')): \
                found_libs.append(os.path.join(root, file)); \
    print(f'Found llama-cpp libraries: {found_libs}'); \
    if not found_libs: print('ERROR: No llama-cpp libraries found!');"

# # Dockerfile for req-generator (let's assume you named it this or similar)
# FROM python:3.11-slim-bullseye
# WORKDIR /app
# RUN apt-get update && apt-get install -y \
#     patchelf \
#     libx11-xcb1 \
#     libxcb-xinerama0 \
#     libxcb-icccm4 \
#     libxcb-image0 \
#     libxcb-keysyms1 \
#     libxcb-render-util0 \
#     libxcb-xkb1 \
#     libxkbcommon-x11-0 \
#     build-essential \
#     cmake \
#     git \
#     && rm -rf /var/lib/apt/lists/*
    
# COPY requirements.txt .
    
# RUN pip install pip-tools
    
# ENV CMAKE_ARGS="-DCMAKE_EXE_LINKER_FLAGS='-pthread' -DCMAKE_SHARED_LINKER_FLAGS='-pthread' -DCMAKE_MODULE_LINKER_FLAGS='-pthread'"
    
# # Corrected CMD: Output to a new file, then cat the new file.
# CMD ["sh", "-c", "pip-compile --generate-hashes --resolver=backtracking -o requirements_new.txt requirements.txt && cat requirements_new.txt"]