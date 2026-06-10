# syntax=docker/dockerfile:1.7

FROM mcr.microsoft.com/playwright/python:v1.55.0-noble AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_CACHE_DIR=/root/.cache/uv

WORKDIR /app

# Install uv once in base layer
RUN pip install uv