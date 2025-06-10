# Application Image
FROM aicoder-base

LABEL maintainer="mkaragiannop@juniper.net"

# Set timezone
RUN ln -sf /usr/share/zoneinfo/Europe/Athens /etc/localtime && \
    echo "Europe/Athens" > /etc/timezone && \
    # Add a non-root user with a home directory
    groupadd -r appgroup && \
    useradd -r -g appgroup -m -d /home/aicoderuser aicoderuser && \
    mkdir -p /home/aicoderuser/.cache && \
    # Set permissions for the home directory
    chown -R aicoderuser:appgroup /home/aicoderuser

ADD ./huggingface_cache /home/aicoderuser/.cache/huggingface

# Set working directory for package installation
WORKDIR /build

# Copy only the requirements file first
COPY app/requirements.txt /build/requirements.txt

# Install Python packages with caching
RUN --mount=type=cache,target=/home/ubuntu/.cache \
    pip install --no-cache-dir --prefix=/install \
    -r /build/requirements.txt

# Set the Python PATH so non-root users can access the installed packages
ENV PATH="/usr/local/bin:/install/bin:$PATH" \
    PYTHONPATH="/install/lib/python3.11/site-packages"

# Set working directory for the app
WORKDIR /app

# Copy the rest of the application files
COPY --chown=aicoderuser:appgroup app /app
COPY bumpversion.cfg /app

# Set permissions for the application directory
RUN chmod +x runme.sh && chown -R aicoderuser:appgroup /app

# Switch to non-root user
USER aicoderuser

# Run the application
ENTRYPOINT ["/bin/bash", "/app/runme.sh"]
