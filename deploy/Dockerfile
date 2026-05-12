FROM python:3.12-slim

# Runtime libs that TU's binary wheels need at runtime
# (epam.indigo → libxrender/libxext/libsm/libx11/libexpat;
#  faiss-cpu / numpy / scipy → libgomp;
#  build-time → gcc/g++ for anything that needs to compile)
RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc g++ \
      libxrender1 libxext6 libsm6 libx11-6 libexpat1 \
      libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/tu_src

# Copy only what pip install needs from the local TU fork. The build
# context is libs/tooluniverse/ (see docker-compose.yml `build.context`).
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

# Editable install so the package metadata + entry points are present
# under /app/tu_src; the source tree is what runs at import time.
RUN pip install --no-cache-dir -e .

# Trim build-only toolchain; runtime libs stay.
RUN apt-get purge -y gcc g++ && apt-get autoremove -y

ENV TOOLUNIVERSE_LOG_LEVEL=INFO \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# tooluniverse-smcp-server is the compat entry — it hard-codes
# search_enabled=True and loads all tool categories. If you need to
# tune (--no-search, --categories, etc.), switch to the richer
# tooluniverse-smcp entry with --transport http.
CMD ["tooluniverse-smcp-server", "--host", "0.0.0.0", "--port", "8000"]
