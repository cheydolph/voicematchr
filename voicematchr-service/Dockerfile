FROM python:3.11-slim

# The /data volume must be writable by UID 1001 on the host before first run:
#   sudo chown -R 1001:1001 ./data
RUN groupadd --system --gid 1001 appgroup \
    && useradd --system --uid 1001 --gid 1001 --no-create-home appuser

WORKDIR /app

# Re-run the discovery command if the base image is updated:
#   sudo docker run --rm python:3.11-slim bash -c \
#     "apt-get update -qq && apt-cache show libsndfile1 ffmpeg build-essential curl | grep '^Version'"
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1=1.2.2-2+deb13u1 \
    ffmpeg=7:7.1.5-0+deb13u1 \
    build-essential=12.12 \
    curl=8.14.1-2+deb13u3 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# To find the latest available CPU wheel, browse:
#   https://download.pytorch.org/whl/cpu/torch/
RUN pip install --no-cache-dir torch==2.5.1+cpu \
      --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appgroup app/ ./app/

USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3939"]