ARG BUILD_FROM
FROM ${BUILD_FROM}

# Set working directory
WORKDIR /app

# Install system dependencies required for OpenCV on Debian Bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt || pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app /app/app
COPY static /app/static
COPY run.sh /app/run.sh

RUN chmod +x /app/run.sh

EXPOSE 1237

CMD ["/app/run.sh"]
