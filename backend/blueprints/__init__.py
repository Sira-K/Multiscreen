# Import packages
from flask import Blueprint

# Import blueprints
from .client_management import client_bp
from .video_management import video_bp
from .docker_management import docker_bp

# Import streaming modules
from .streaming import multi_stream_bp, split_stream_bp