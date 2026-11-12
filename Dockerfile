FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SDL_VIDEODRIVER=dummy \
    SDL_AUDIODRIVER=dummy

WORKDIR /app

# Install minimal system dependencies for headless Pygame rendering & fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core \
    libsdl2-2.0-0 \
    libsdl2-image-2.0-0 \
    libsdl2-mixer-2.0-0 \
    libsdl2-ttf-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first for better layer caching in GitHub Actions
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project source and tests
COPY pytest.ini main.py ./
COPY mvc/ ./mvc/
COPY tests/ ./tests/

# Run the test suite by default
CMD ["pytest", "-v", "tests/test_game.py"]
