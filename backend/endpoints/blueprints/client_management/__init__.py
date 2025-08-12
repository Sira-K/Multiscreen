"""
Client Management Module
Simple initialization with CORS support
"""

from flask import Blueprint
from flask_cors import CORS

# Import the main client blueprint
from .client_blueprint import client_bp

# Enable CORS for client management
CORS(client_bp, resources={
    r"/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
        "supports_credentials": True
    }
})

__all__ = ['client_bp']