ARG BUILD_FROM
FROM ${BUILD_FROM}

# Set working directory
WORKDIR /app

# Install system dependencies required for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app /app/app
COPY static /app/static
COPY run.sh /app/run.sh

RUN chmod +x /app/run.sh

EXPOSE 8000

CMD ["/app/run.sh"]
