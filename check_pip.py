#!/usr/bin/env python3
"""Check if pip is installed"""
try:
    import pip
    exit(0)
except ImportError:
    exit(1)

