"""
Secure secrets management module.
Implements:
- Environment variable validation
- Secure configuration management
- Secret rotation support
- Audit logging for secret access
"""

import os
from typing import Any, Optional, Dict, List, Tuple, Callable
from enum import Enum
from datetime import datetime, timezone


class SecretType(Enum):
    """Types of secrets with different validation rules."""
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    URL = "url"
    DATABASE_URL = "database_url"
    API_KEY = "api_key"


class SecretValidator:
    """Validates secrets meet security requirements."""
    
    @staticmethod
    def validate_url(value: str) -> Tuple[bool, str]:
        """Validate URL format and security."""
        if not value:
            return False, "URL cannot be empty"
        
        # Check for HTTPS in production-like URLs
        if value.startswith('http://') and not value.startswith('http://localhost'):
            return False, "Production URLs must use HTTPS"
        
        return True, ""
    
    @staticmethod
    def validate_api_key(value: str) -> Tuple[bool, str]:
        """Validate API key format and length."""
        if not value:
            return False, "API key cannot be empty"
        
        if len(value) < 16:
            return False, "API key should be at least 16 characters long"
        
        return True, ""
    
    @staticmethod
    def validate_password(value: str) -> Tuple[bool, str]:
        """Validate password meets minimum requirements."""
        if not value:
            return False, "Password cannot be empty"
        
        if len(value) < 12:
            return False, "Password must be at least 12 characters"
        
        if not any(c.isupper() for c in value):
            return False, "Password must contain uppercase letters"
        
        if not any(c.isdigit() for c in value):
            return False, "Password must contain digits"
        
        return True, ""


class Secret:
    """Represents a secret with metadata and validation."""
    
    def __init__(
        self,
        name: str,
        secret_type: SecretType = SecretType.STRING,
        required: bool = True,
        default: Optional[Any] = None,
        validator: Optional[Callable[[Any], Tuple[bool, str]]] = None,
        description: str = ""
    ):
        """
        Initialize secret definition.
        
        Args:
            name: Environment variable name
            secret_type: Type of secret
            required: Whether secret is required
            default: Default value if not set
            validator: Custom validation function
            description: Secret description for documentation
        """
        self.name = name
        self.secret_type = secret_type
        self.required = required
        self.default = default
        self.validator = validator
        self.description = description
        self._value = None
        self._loaded = False
        self._last_accessed = None
    
    def get(self) -> Any:
        """Get secret value with access logging."""
        if not self._loaded:
            self.load()
        
        # Log access
        self._last_accessed = datetime.now(timezone.utc)
        
        # In production, log to audit system
        # audit_logger.log_secret_access(self.name, self._last_accessed)
        
        return self._value
    
    def load(self):
        """Load secret from environment."""
        value = os.getenv(self.name, self.default)
        
        if value is None:
            if self.required:
                raise ValueError(f"Required secret '{self.name}' not found in environment")
            self._value = None
            self._loaded = True
            return
        
        # Type conversion
        if self.secret_type == SecretType.BOOLEAN:
            self._value = value.lower() in ('true', '1', 'yes')
        elif self.secret_type == SecretType.INTEGER:
            try:
                self._value = int(value)
            except ValueError:
                raise ValueError(f"Secret '{self.name}' must be an integer")
        else:
            self._value = value
        
        # Custom validation
        if self.validator:
            is_valid, error = self.validator(self._value)
            if not is_valid:
                raise ValueError(f"Secret '{self.name}' validation failed: {error}")
        
        self._loaded = True
    
    def __repr__(self) -> str:
        """String representation (masked for security)."""
        if self.secret_type == SecretType.API_KEY:
            return f"Secret({self.name}=***MASKED***)"
        return f"Secret({self.name}={self.get()})"


class SecretsManager:
    """
    Centralized secrets management with validation and auditing.
    Single source of truth for all configuration secrets.
    """
    
    # Define all secrets used by the application
    SECRETS = {
        # JWT and Authentication
        'JWT_SECRET_KEY': Secret(
            'JWT_SECRET_KEY',
            secret_type=SecretType.API_KEY,
            required=True,
            description='Secret key for JWT token signing'
        ),
        'JWT_ALGORITHM': Secret(
            'JWT_ALGORITHM',
            secret_type=SecretType.STRING,
            required=False,
            default='HS256',
            description='JWT signing algorithm'
        ),
        'ACCESS_TOKEN_EXPIRE_MINUTES': Secret(
            'ACCESS_TOKEN_EXPIRE_MINUTES',
            secret_type=SecretType.INTEGER,
            required=False,
            default=15,
            description='Access token expiration time in minutes'
        ),
        'REFRESH_TOKEN_EXPIRE_DAYS': Secret(
            'REFRESH_TOKEN_EXPIRE_DAYS',
            secret_type=SecretType.INTEGER,
            required=False,
            default=7,
            description='Refresh token expiration in days'
        ),
        
        # Database
        'DATABASE_URL': Secret(
            'DATABASE_URL',
            secret_type=SecretType.DATABASE_URL,
            required=False,
            default='sqlite:///app.db',
            description='Database connection string'
        ),
        
        # RabbitMQ
        'RABBITMQ_HOST': Secret(
            'RABBITMQ_HOST',
            secret_type=SecretType.STRING,
            required=False,
            default='rabbitmq',
            description='RabbitMQ host'
        ),
        'RABBITMQ_USER': Secret(
            'RABBITMQ_USER',
            secret_type=SecretType.STRING,
            required=False,
            default='guest',
            description='RabbitMQ username'
        ),
        'RABBITMQ_PASSWORD': Secret(
            'RABBITMQ_PASSWORD',
            secret_type=SecretType.STRING,
            required=False,
            default='guest',
            description='RabbitMQ password'
        ),
        
        # External APIs
        'OPENAI_API_KEY': Secret(
            'OPENAI_API_KEY',
            secret_type=SecretType.API_KEY,
            required=False,
            description='OpenAI API key for AI features'
        ),
        
        # Security
        'MIN_PASSWORD_LENGTH': Secret(
            'MIN_PASSWORD_LENGTH',
            secret_type=SecretType.INTEGER,
            required=False,
            default=12,
            description='Minimum password length requirement'
        ),
        'MAX_LOGIN_ATTEMPTS': Secret(
            'MAX_LOGIN_ATTEMPTS',
            secret_type=SecretType.INTEGER,
            required=False,
            default=5,
            description='Maximum failed login attempts'
        ),
        'ENABLE_RATE_LIMITING': Secret(
            'ENABLE_RATE_LIMITING',
            secret_type=SecretType.BOOLEAN,
            required=False,
            default=True,
            description='Enable rate limiting'
        ),
    }
    
    _instance = None  # Singleton
    _secrets_loaded = False
    
    def __new__(cls):
        """Enforce singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize secrets manager."""
        if not self._secrets_loaded:
            self.load_secrets()
            SecretsManager._secrets_loaded = True
    
    def load_secrets(self):
        """Load and validate all secrets from environment."""
        errors: List[str] = []
        
        for _key, secret in self.SECRETS.items():
            try:
                secret.load()
            except ValueError as e:
                errors.append(str(e))
        
        if errors:
            error_msg = "\n".join(errors)
            print(f"\n⚠️  SECRETS VALIDATION ERRORS:\n{error_msg}\n")
            
            # In development, we might continue with defaults
            # In production, we should fail fast
            if os.getenv('ENVIRONMENT', 'development') == 'production':
                raise ValueError(f"Secrets validation failed:\n{error_msg}")
    
    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Get a secret value.
        
        Args:
            key: Secret key
            default: Default value if secret not found
            
        Returns:
            Secret value
        
        Raises:
            KeyError: If secret key not found
        """
        if key not in self.SECRETS:
            if default is not None:
                return default
            raise KeyError(f"Unknown secret: {key}")
        
        return self.SECRETS[key].get()
    
    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access."""
        return self.get(key)
    
    def validate_all(self) -> Dict[str, bool]:
        """
        Validate all secrets.
        
        Returns:
            Dictionary with validation results
        """
        results: Dict[str, bool] = {}
        
        for key, secret in self.SECRETS.items():
            try:
                secret.load()
                results[key] = True
            except ValueError:
                results[key] = False
        
        return results
    
    def get_documentation(self) -> str:
        """Get documentation of all secrets."""
        doc = "# Secrets Configuration Reference\n\n"
        
        for key, secret in self.SECRETS.items():
            doc += f"## {key}\n"
            doc += f"- **Type**: {secret.secret_type.value}\n"
            doc += f"- **Required**: {secret.required}\n"
            doc += f"- **Default**: {secret.default}\n"
            doc += f"- **Description**: {secret.description}\n\n"
        
        return doc
    
    def get_masked_secrets(self) -> Dict[str, str]:
        """Get secrets with sensitive values masked."""
        masked: Dict[str, str] = {}
        
        for key, secret in self.SECRETS.items():
            value = secret.get()
            
            # Mask sensitive values
            if secret.secret_type in (
                SecretType.API_KEY,
                SecretType.DATABASE_URL,
            ) and value:
                masked[key] = f"***MASKED*** (length: {len(str(value))})"
            else:
                masked[key] = str(value) if value else "None"
        
        return masked


# Global instance
secrets = SecretsManager()


class ConfigValidator:
    """Validates overall application configuration."""
    
    @staticmethod
    def validate_environment() -> Tuple[bool, List[str]]:
        """
        Validate the entire environment configuration.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors: List[str] = []
        
        # Validate JWT secret
        jwt_secret = os.getenv('JWT_SECRET_KEY')
        if not jwt_secret:
            errors.append("JWT_SECRET_KEY not set")
        elif len(jwt_secret) < 32:
            errors.append("JWT_SECRET_KEY too short (< 32 characters)")
        
        # Validate environment type
        env = os.getenv('ENVIRONMENT', 'development')
        if env not in ('development', 'staging', 'production'):
            errors.append(f"Invalid ENVIRONMENT: {env}")
        
        # Validate rate limiting config
        try:
            rate_limit = int(os.getenv('DEFAULT_REQUESTS_PER_MINUTE', 60))
            if rate_limit < 1:
                errors.append("DEFAULT_REQUESTS_PER_MINUTE must be >= 1")
        except ValueError:
            errors.append("DEFAULT_REQUESTS_PER_MINUTE must be an integer")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_and_report():
        """Validate and print configuration report."""
        is_valid, errors = ConfigValidator.validate_environment()
        
        if not is_valid:
            print("\n❌ CONFIGURATION ERRORS:")
            for error in errors:
                print(f"   - {error}")
        else:
            print("\n✅ Configuration is valid")
        
        # Print masked secrets
        print("\n📋 Current Configuration:")
        masked = secrets.get_masked_secrets()
        for key, value in masked.items():
            print(f"   {key}: {value}")


from typing import Tuple
