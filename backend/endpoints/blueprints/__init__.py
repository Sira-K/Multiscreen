# Import packages
from flask import Blueprint

# Import blueprints
from .client_management import client_bp
from .video_management import video_bp
from .docker_management import docker_bp

# Import stream_management last to avoid circular imports
from .stream_management import stream_bp