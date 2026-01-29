FROM python:3.14.2-slim

# Specify WORKDIR
WORKDIR /app

# Configure non-privileged user
ARG UID=10001
RUN adduser \
  --disabled-password \
  --gecos "" \
  --home "/nonexistent" \
  --shell "/sbin/nologin" \
  --no-create-home \
  --uid "${UID}" \
  appuser

# Download dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
  --mount=type=bind,source=requirements.txt,target=requirements.txt \
  python -m pip install -r requirements.txt

# Switch to unprivileged user and run
USER appuser
COPY src/ .
EXPOSE 5000
CMD ["python3", "main.py"]

