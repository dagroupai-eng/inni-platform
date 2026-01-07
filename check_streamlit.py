#!/usr/bin/env python3
"""Check if streamlit is installed"""
try:
    import streamlit
    exit(0)
except ImportError:
    exit(1)

