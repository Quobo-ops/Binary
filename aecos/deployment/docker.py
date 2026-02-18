"""DockerBuilder — generates Dockerfile and docker-compose.yml."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_DOCKERFILE_TEMPLATE = """\
# AEC OS Dockerfile — multi-stage build
# Stage 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml ./
COPY aecos/ ./aecos/

RUN pip install --no-cache-dir --upgrade pip && \\
    pip install --no-cache-dir .

# Stage 2: Runtime
FROM python:3.12-slim AS runtime

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /build/aecos ./aecos
COPY pyproject.toml ./

# Create non-root user
RUN useradd --create-home aecos
USER aecos

ENV AECOS_ENV=production
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["python", "-m", "aecos"]
"""

_COMPOSE_TEMPLATE = """\
version: "3.9"

services:
  aecos:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - aecos-data:/app/data
    environment:
      - AECOS_ENV=production
    restart: unless-stopped
{extra_services}
volumes:
  aecos-data:
"""

_OLLAMA_SERVICE = """\
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-models:/root/.ollama
    restart: unless-stopped
"""

_OLLAMA_VOLUME = "  ollama-models:\n"


class DockerBuilder:
    """Generate Docker configuration files."""

    def generate_dockerfile(self, project_path: str | Path) -> Path:
        """Write a Dockerfile to the project root."""
        root = Path(project_path)
        path = root / "Dockerfile"
        path.write_text(_DOCKERFILE_TEMPLATE, encoding="utf-8")
        logger.info("Dockerfile generated: %s", path)
        return path

    def generate_compose(
        self,
        project_path: str | Path,
        services: list[str] | None = None,
    ) -> Path:
        """Write docker-compose.yml to the project root.

        Parameters
        ----------
        services:
            List of service names to include.
            ``'aecos'`` is always included.
            Optional: ``'ollama'``.
        """
        root = Path(project_path)
        svc_list = set(services or ["aecos"])

        extra = ""
        extra_volumes = ""
        if "ollama" in svc_list:
            extra += _OLLAMA_SERVICE
            extra_volumes += _OLLAMA_VOLUME

        content = _COMPOSE_TEMPLATE.format(extra_services=extra)
        if extra_volumes:
            content = content.rstrip() + "\n" + extra_volumes

        path = root / "docker-compose.yml"
        path.write_text(content, encoding="utf-8")
        logger.info("docker-compose.yml generated: %s", path)
        return path
