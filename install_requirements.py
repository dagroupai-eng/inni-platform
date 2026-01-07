#!/usr/bin/env python3
"""
Install requirements.txt packages
"""
import sys
import subprocess
import os

requirements_file = sys.argv[1] if len(sys.argv) > 1 else 'requirements.txt'

if not os.path.exists(requirements_file):
    sys.stderr.write("ERROR: {} not found\n".format(requirements_file))
    sys.exit(1)

try:
    # Run pip install with all output captured
    result = subprocess.run(
        [sys.executable, '-m', 'pip', 'install', '-r', requirements_file, '--prefer-binary'],
        capture_output=True,
        text=True,
        check=False
    )
    
    # Exit with pip's return code
    sys.exit(result.returncode)
except Exception as e:
    sys.stderr.write("ERROR: {}\n".format(e))
    sys.exit(1)

