"""
AES-256 암호화 모듈
API 키 등 민감한 데이터의 안전한 저장을 위한 암호화 기능
"""

import os
import base64
import hashlib
from typing import Tuple, Optional

# cryptography 라이브러리 사용 (requirements.txt에 추가 필요)
try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("WARNING: cryptography 라이브러리가 설치되지 않았습니다. 암호화 기능을 사용할 수 없습니다.")

from config.settings import get_encryption_master_key


def _get_key_bytes() -> bytes:
    """마스터 키를 바이트로 변환합니다."""
    master_key = get_encryption_master_key()
    # SHA-256으로 32바이트 키 생성
    return hashlib.sha256(master_key.encode()).digest()


def encrypt_value(plaintext: str) -> Tuple[str, str]:
    """
    문자열을 AES-256-CBC로 암호화합니다.

    Args:
        plaintext: 암호화할 평문

    Returns:
        (암호화된 값 (base64), IV (base64))
    """
    if not CRYPTO_AVAILABLE:
        # cryptography가 없으면 base64로 인코딩만 (보안 약함)
        encoded = base64.b64encode(plaintext.encode()).decode()
        return encoded, ""

    key = _get_key_bytes()

    # 무작위 IV 생성
    iv = os.urandom(16)

    # AES-256-CBC 암호화
    cipher = Cipher(
        algorithms.AES(key),
        modes.CBC(iv),
        backend=default_backend()
    )
    encryptor = cipher.encryptor()

    # PKCS7 패딩
    padding_length = 16 - (len(plaintext.encode()) % 16)
    padded_data = plaintext.encode() + bytes([padding_length] * padding_length)

    encrypted = encryptor.update(padded_data) + encryptor.finalize()

    # Base64 인코딩
    encrypted_b64 = base64.b64encode(encrypted).decode()
    iv_b64 = base64.b64encode(iv).decode()

    return encrypted_b64, iv_b64


def decrypt_value(encrypted_value: str, iv: str) -> Optional[str]:
    """
    AES-256-CBC로 암호화된 문자열을 복호화합니다.

    Args:
        encrypted_value: 암호화된 값 (base64)
        iv: IV (base64)

    Returns:
        복호화된 평문 또는 None (실패 시)
    """
    if not encrypted_value:
        return None

    if not CRYPTO_AVAILABLE or not iv:
        # cryptography가 없으면 base64 디코딩만 시도
        try:
            return base64.b64decode(encrypted_value).decode()
        except Exception:
            return None

    try:
        key = _get_key_bytes()

        # Base64 디코딩
        encrypted_bytes = base64.b64decode(encrypted_value)
        iv_bytes = base64.b64decode(iv)

        # AES-256-CBC 복호화
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv_bytes),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()

        decrypted = decryptor.update(encrypted_bytes) + decryptor.finalize()

        # PKCS7 언패딩
        padding_length = decrypted[-1]
        plaintext = decrypted[:-padding_length].decode()

        return plaintext

    except Exception as e:
        print(f"복호화 오류: {e}")
        return None


def is_encryption_available() -> bool:
    """암호화 기능 사용 가능 여부를 반환합니다."""
    return CRYPTO_AVAILABLE


def generate_random_key(length: int = 32) -> str:
    """무작위 키를 생성합니다."""
    return base64.urlsafe_b64encode(os.urandom(length)).decode()[:length]
