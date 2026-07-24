"""TBS ONE entry point.

Android-safe RC1: the existing verified application remains in legacy.py.
Gunicorn continues to start with: gunicorn app:app
"""
from legacy import app

__all__ = ["app"]

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
