#!/bin/bash
# Build script for Render.com deployment
# This script runs database migrations before starting the application

set -e  # Exit on error

echo "Running database migrations..."
alembic upgrade head

echo "Migrations completed successfully!"
