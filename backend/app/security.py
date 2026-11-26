"""RF_01 / CU_01 · Hash de contraseñas y firma de sesiones JWT."""
from datetime import datetime, timedelta, timezone
from hashlib import pbkdf2_hmac
from hmac import compare_digest
import base64
import os

import jwt

from app.config import settings
from app.models import User


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    iterations = 320000
    digest = pbkdf2_hmac('sha256', password.encode(), salt, iterations)
    return f"{iterations}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        n, s, digest = stored.split('$')
        actual = pbkdf2_hmac('sha256', password.encode(), base64.b64decode(s), int(n))
        return compare_digest(actual, base64.b64decode(digest))
    except (ValueError, TypeError):
        return False


def create_token(user: User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=8)
    return jwt.encode({'sub': str(user.id), 'role': user.role, 'exp': exp}, settings.jwt_secret, algorithm='HS256')
