"""
Advanced security module with enhanced JWT authentication.
Implements:
- JWT token generation and verification with refresh tokens
- Password hashing with bcrypt
- Token rotation and revocation
- Secure secret validation
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple, cast

import jwt
from flask import current_app, jsonify, request


class SecurityConfig:
    """Security configuration with validation."""
    
    def __init__(self):
        """Initialize security configuration from environment."""
        # JWT Configuration
        self.SECRET_KEY: str = os.getenv('JWT_SECRET_KEY') or ""
        self.ALGORITHM: str = os.getenv('JWT_ALGORITHM', 'HS256')
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
            os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', 15)
        )
        self.REFRESH_TOKEN_EXPIRE_DAYS: int = int(
            os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', 7)
        )
        
        # Password Configuration
        self.MIN_PASSWORD_LENGTH: int = int(
            os.getenv('MIN_PASSWORD_LENGTH', 12)
        )
        self.REQUIRE_SPECIAL_CHARS: bool = os.getenv(
            'REQUIRE_SPECIAL_CHARS', 'true'
        ).lower() == 'true'
        
        # Rate Limiting
        self.MAX_LOGIN_ATTEMPTS: int = int(
            os.getenv('MAX_LOGIN_ATTEMPTS', 5)
        )
        self.LOGIN_ATTEMPT_WINDOW_MINUTES: int = int(
            os.getenv('LOGIN_ATTEMPT_WINDOW_MINUTES', 15)
        )
        
        # Token Revocation
        self.ENABLE_TOKEN_REVOCATION: bool = os.getenv(
            'ENABLE_TOKEN_REVOCATION', 'true'
        ).lower() == 'true'
        
        self._validate()
    
    def _validate(self):
        """Validate security configuration."""
        if not self.SECRET_KEY:
            raise ValueError("JWT_SECRET_KEY environment variable not set")
        
        if len(self.SECRET_KEY) < 32:
            print("⚠️  WARNING: JWT_SECRET_KEY should be at least 32 characters")
        
        if self.MIN_PASSWORD_LENGTH < 12:
            print("⚠️  WARNING: MIN_PASSWORD_LENGTH should be at least 12")


class PasswordManager:
    """Handles password hashing and validation."""
    
    ROUNDS = 390000  # PBKDF2 iteration count
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using PBKDF2-HMAC-SHA256."""
        salt = secrets.token_hex(16)
        derived_key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            PasswordManager.ROUNDS,
        )
        return f"pbkdf2_sha256${PasswordManager.ROUNDS}${salt}${derived_key.hex()}"
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify password against PBKDF2 hash."""
        try:
            algorithm, rounds, salt, stored_digest = hashed.split('$', 3)
            if algorithm != 'pbkdf2_sha256':
                return False

            derived_key = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                int(rounds),
            )
            return hmac.compare_digest(derived_key.hex(), stored_digest)
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_password_strength(password: str, config: SecurityConfig) -> Tuple[bool, str]:
        """
        Validate password meets security requirements.
        
        Args:
            password: Password to validate
            config: Security configuration
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(password) < config.MIN_PASSWORD_LENGTH:
            return False, f"Password must be at least {config.MIN_PASSWORD_LENGTH} characters"
        
        if not any(char.isupper() for char in password):
            return False, "Password must contain at least one uppercase letter"
        
        if not any(char.isdigit() for char in password):
            return False, "Password must contain at least one digit"
        
        if config.REQUIRE_SPECIAL_CHARS:
            special_chars = "!@#$%^&*()-_=+[]{}|;:',.<>?/"
            if not any(char in special_chars for char in password):
                return False, "Password must contain at least one special character"
        
        return True, ""


class TokenManager:
    """Manages JWT token generation and verification."""
    
    def __init__(self, config: SecurityConfig):
        """Initialize token manager."""
        self.config = config
        self.revoked_tokens: set[str] = set()  # In production, use Redis
    
    def create_tokens(self, subject: str, role: str = "user") -> Dict[str, Any]:
        """
        Create access and refresh tokens.
        
        Args:
            subject: Token subject (usually username)
            role: User role
            
        Returns:
            Dictionary with access_token and refresh_token
        """
        now = datetime.now(timezone.utc)
        
        # Access token (short-lived)
        access_payload: Dict[str, Any] = {  # type: ignore[assignment]
            "sub": subject,
            "role": role,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=self.config.ACCESS_TOKEN_EXPIRE_MINUTES),
            "jti": secrets.token_urlsafe(16),  # JWT ID for revocation
        }
        
        # Refresh token (long-lived)
        refresh_payload: Dict[str, Any] = {  # type: ignore[assignment]
            "sub": subject,
            "role": role,
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=self.config.REFRESH_TOKEN_EXPIRE_DAYS),
            "jti": secrets.token_urlsafe(16),
        }
        
        secret_key = cast(str, self.config.SECRET_KEY)

        jwt_module: Any = jwt

        access_token = jwt_module.encode(
            access_payload,
            secret_key,
            algorithm=self.config.ALGORITHM
        )
        
        refresh_token = jwt_module.encode(
            refresh_payload,
            secret_key,
            algorithm=self.config.ALGORITHM
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": self.config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """
        Verify and decode JWT token.
        
        Args:
            token: JWT token to verify
            token_type: Expected token type (access or refresh)
            
        Returns:
            Decoded token payload or None if invalid
        """
        try:
            jwt_module: Any = jwt
            payload: Dict[str, Any] = cast(
                Dict[str, Any],
                jwt_module.decode(
                token,
                self.config.SECRET_KEY,
                algorithms=[self.config.ALGORITHM]
                )
            )
            
            # Verify token type
            if payload.get("type") != token_type:
                return None
            
            # Check if token is revoked
            if self.config.ENABLE_TOKEN_REVOCATION:
                jti = payload.get("jti")
                if jti in self.revoked_tokens:
                    return None
            
            return payload
        
        except jwt.ExpiredSignatureError:
            return None  # Token has expired
        except jwt.InvalidTokenError:
            return None  # Invalid token
    
    def revoke_token(self, token: str) -> bool:
        """
        Revoke a token (add to blacklist).
        
        Args:
            token: Token to revoke
            
        Returns:
            True if revoked successfully
        """
        if not self.config.ENABLE_TOKEN_REVOCATION:
            return False
        
        try:
            jwt_module: Any = jwt
            payload_data: Dict[str, Any] = cast(
                Dict[str, Any],
                jwt_module.decode(
                token,
                self.config.SECRET_KEY,
                algorithms=[self.config.ALGORITHM],
                options={"verify_exp": False}
                )
            )
            jti = payload_data.get("jti")
            if jti:
                self.revoked_tokens.add(jti)
                return True
        except jwt.InvalidTokenError:
            pass
        
        return False
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Generate new access token from refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New tokens or None if refresh token is invalid
        """
        payload = self.verify_token(refresh_token, token_type="refresh")
        if not payload:
            return None
        
        # Create new access token
        return self.create_tokens(
            subject=payload["sub"],
            role=payload.get("role", "user")
        )


def token_required(f: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to require valid access token.
    Extracts token from Authorization header.
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        token = None
        
        # Extract token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({"error": "Invalid authorization header"}), 401
        
        if not token:
            return jsonify({"error": "Missing authorization token"}), 401
        
        # Verify token
        token_manager: Any = getattr(current_app, "token_manager", None)
        if token_manager is None:
            return jsonify({"error": "Token manager unavailable"}), 500

        payload: Optional[Dict[str, Any]] = token_manager.verify_token(token, token_type="access")
        
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401
        
        # Store payload in request context
        request.user_id = payload.get("sub")  # type: ignore[attr-defined]
        request.user_role = payload.get("role")  # type: ignore[attr-defined]
        request.token_payload = payload  # type: ignore[attr-defined]
        
        return f(*args, **kwargs)
    
    return decorated_function


def admin_required(f: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to require admin role.
    Must be used after token_required.
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        if getattr(request, 'user_role', None) != "admin":
            return jsonify({"error": "Admin role required"}), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


class LoginAttemptTracker:
    """Track failed login attempts for brute force protection."""
    
    def __init__(self):
        self.attempts: Dict[str, list[datetime]] = {}  # In production, use Redis
    
    def record_attempt(self, username: str, config: SecurityConfig):
        """Record a failed login attempt."""
        if username not in self.attempts:
            self.attempts[username] = []
        
        self.attempts[username].append(datetime.now(timezone.utc))
        
        # Clean old attempts outside the window
        cutoff_time = datetime.now(timezone.utc) - timedelta(
            minutes=config.LOGIN_ATTEMPT_WINDOW_MINUTES
        )
        self.attempts[username] = [
            t for t in self.attempts[username] if t > cutoff_time
        ]
    
    def is_locked(self, username: str, config: SecurityConfig) -> bool:
        """Check if account is locked due to too many attempts."""
        if username not in self.attempts:
            return False
        
        # Clean old attempts
        cutoff_time = datetime.now(timezone.utc) - timedelta(
            minutes=config.LOGIN_ATTEMPT_WINDOW_MINUTES
        )
        self.attempts[username] = [
            t for t in self.attempts[username] if t > cutoff_time
        ]
        
        return len(self.attempts[username]) >= config.MAX_LOGIN_ATTEMPTS
    
    def reset_attempts(self, username: str):
        """Reset failed attempts for a user."""
        if username in self.attempts:
            self.attempts[username] = []


class AuditLogger:
    """Log security-relevant events for audit trail."""
    
    @staticmethod
    def log_login_success(username: str, ip_address: str, user_agent: str):
        """Log successful login."""
        timestamp = datetime.now(timezone.utc).isoformat()
        print(f"[AUDIT] {timestamp} - LOGIN_SUCCESS - User: {username}, IP: {ip_address}")
    
    @staticmethod
    def log_login_failure(username: str, ip_address: str, reason: str):
        """Log failed login."""
        timestamp = datetime.now(timezone.utc).isoformat()
        print(f"[AUDIT] {timestamp} - LOGIN_FAILURE - User: {username}, IP: {ip_address}, Reason: {reason}")
    
    @staticmethod
    def log_token_refresh(username: str, ip_address: str):
        """Log token refresh."""
        timestamp = datetime.now(timezone.utc).isoformat()
        print(f"[AUDIT] {timestamp} - TOKEN_REFRESH - User: {username}, IP: {ip_address}")
    
    @staticmethod
    def log_unauthorized_access(endpoint: str, ip_address: str, reason: str):
        """Log unauthorized access attempt."""
        timestamp = datetime.now(timezone.utc).isoformat()
        print(f"[AUDIT] {timestamp} - UNAUTHORIZED_ACCESS - Endpoint: {endpoint}, IP: {ip_address}, Reason: {reason}")
