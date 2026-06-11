FROM mcr.microsoft.com/playwright/python:v1.55.0-noble AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_CACHE_DIR=/root/.cache/uv

WORKDIR /app

# Senior Team Optimization: Install uv cleanly via standalone script in the base layer
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Ensure uv is globally accessible in the system path
ENV PATH="/root/.local/bin/:${PATH}"