# The Engineer AI Tutor - Linux Build Environment
# Creates consistent Linux builds using Docker

FROM --platform=linux/amd64 python:3.11-bookworm
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV QT_QPA_PLATFORM=offscreen
RUN apt-get update && apt-get install -y \
    # Build tools
    build-essential \
    cmake \
    git \
    patchelf \
    pkg-config \
    \
    # Qt6 and graphics libraries
    qt6-base-dev \
    qt6-tools-dev \
    qt6-qpa-plugins \
    libqt6gui6 \
    libqt6widgets6 \
    libqt6dbus6 \
    libqt6svg6-dev \
    libqt6printsupport6 \
    libqt6opengl6-dev \
    \
    # X11 and graphics support
    libgl1-mesa-dev \
    libegl1-mesa-dev \
    libxcb1-dev \
    libxcb-icccm4-dev \
    libxcb-image0-dev \
    libxcb-keysyms1-dev \
    libxcb-randr0-dev \
    libxcb-render0-dev \
    libxcb-render-util0-dev \
    libxcb-shape0-dev \
    libxcb-sync-dev \
    libxcb-util1 \
    libxcb-xfixes0-dev \
    libxcb-xinerama0-dev \
    libxcb-xkb-dev \
    libxkbcommon-dev \
    libxkbcommon-x11-dev \
    \
    # Audio and multimedia (for potential future features)
    libasound2-dev \
    libpulse-dev \
    \
    # Font rendering
    libfontconfig1-dev \
    libfreetype6-dev \
    \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir pyinstaller>=5.7.0
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || true
RUN pip install --no-cache-dir PySide6==6.8.0.2 || pip install --no-cache-dir PySide6>=6.4.0
RUN pip install --no-cache-dir sqlalchemy>=2.0.0
RUN pip install --no-cache-dir groq>=0.5.0 || true
RUN pip install --no-cache-dir requests>=2.31.0
RUN pip install --no-cache-dir python-dotenv
RUN pip install --no-cache-dir llama-cpp-python==0.3.9 || \
    pip install --no-cache-dir llama-cpp-python || \
    echo "llama-cpp-python installation failed - local AI will be disabled"
RUN pip install --no-cache-dir firebase-admin || true
RUN pip install --no-cache-dir pymongo || true
RUN pip install --no-cache-dir aiohttp>=3.8.0 || true
RUN pip install --no-cache-dir loguru>=0.7.0 || true

COPY . .

RUN mkdir -p dist build hooks

RUN chmod +x src/main.py 2>/dev/null || true

CMD ["pyinstaller", "--clean", "engineer.spec"]

LABEL maintainer="The Engineer: Emmanue Sibanda"
LABEL description="The Engineer is an AI Tutor to help kids build engineer projects."
LABEL version="1.0.0" 