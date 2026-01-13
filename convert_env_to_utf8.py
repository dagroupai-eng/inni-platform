#!/usr/bin/env python3
"""
Convert .env file to UTF-8 encoding while preserving content
"""
import sys
import os

try:
    env_file = sys.argv[1] if len(sys.argv) > 1 else '.env'

    if not os.path.exists(env_file):
        print(f"[ERROR] File not found: {env_file}", file=sys.stderr)
        sys.exit(1)

    # Read file as binary
    try:
        with open(env_file, 'rb') as f:
            data = f.read()
    except Exception as e:
        print(f"[ERROR] Failed to read file: {e}", file=sys.stderr)
        sys.exit(1)

    # Try different encodings
    encodings = ['utf-8', 'cp949', 'latin-1', 'utf-16-le', 'utf-16-be', 'cp1252']
    content = None
    used_encoding = None

    for enc in encodings:
        try:
            content = data.decode(enc)
            used_encoding = enc
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    # If all encodings fail, use replace mode
    if content is None:
        content = data.decode('utf-8', errors='replace')
        used_encoding = 'utf-8 (with errors replaced)'

    # Write back as UTF-8
    try:
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[SUCCESS] Converted {env_file} from {used_encoding} to UTF-8")
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] Failed to write file: {e}", file=sys.stderr)
        sys.exit(1)

except Exception as e:
    print(f"[ERROR] Unexpected error: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)

