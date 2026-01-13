#!/usr/bin/env python3
"""Check if app.py exists"""
import sys
import os

app_file = sys.argv[1] if len(sys.argv) > 1 else 'app.py'

if os.path.exists(app_file):
    sys.exit(0)
else:
    sys.exit(1)

