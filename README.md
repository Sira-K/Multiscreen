# Multi-Screen Video Streaming Management System

A comprehensive, open-source solution for managing multi-screen video streaming systems with support for SRT protocol, Docker containerization, and real-time client management.

## 🎯 Project Overview

This system enables organizations to create and manage video walls, digital signage networks, and multi-display streaming setups using recycled or heterogeneous displays. It's designed to be scalable, reliable, and easy to deploy across different hardware configurations.

## 🚀 Key Features

### Core Functionality
- **Multi-Screen Streaming**: Stream video content across multiple displays simultaneously
- **SRT Protocol Support**: Low-latency, reliable video streaming using SRT protocol
- **Client Management**: Real-time monitoring and control of streaming clients
- **Group Management**: Organize displays into logical groups for coordinated streaming
- **Video Management**: Upload, validate, and manage video content
- **Docker Integration**: Containerized deployment for easy scaling and management

### Advanced Capabilities
- **Real-time Monitoring**: Live status updates and performance metrics
- **Error Handling**: Comprehensive error management and logging system
- **Load Balancing**: Distribute streaming load across multiple servers
- **Failover Support**: Automatic recovery and redundancy
- **API-First Design**: RESTful API for integration with external systems

## 🏗️ Architecture

### Backend (Flask + Python)
```
backend/
├── app_config.py          # Application configuration
├── flask_app.py          # Main Flask application
├── blueprints/           # Modular route handlers
│   ├── client_management/    # Client registration and monitoring
│   ├── streaming/            # Video streaming endpoints
│   ├── group_management/     # Display group operations
│   ├── video_management/     # Video file handling
│   └── docker_management/    # Container orchestration
├── services/             # Business logic services
└── endpoints/            # API endpoint definitions
```

### Frontend (React + TypeScript)
```
frontend/
├── src/
│   ├── core/             # Core application components
│   ├── features/         # Feature-specific components
│   │   ├── ClientsTab/       # Client management interface
│   │   ├── StreamsTab/       # Streaming control interface
│   │   └── VideoFilesTab/    # Video file management
│   └── shared/           # Shared components and utilities
│       ├── ui/               # Reusable UI components
│       ├── API/              # API client and utilities
│       └── ErrorSystem/      # Error handling system
```

### Client (Python)
```
client/
├── client.py             # Main client application
├── requirements.txt      # Python dependencies
└── setup_client.sh      # Automated setup script
```

## 🔧 How It Works

### 1. System Setup
1. **Backend Server**: Deploy the Flask backend with Docker support
2. **Frontend Interface**: Access the React-based management interface
3. **Client Devices**: Install Python clients on Raspberry Pi or other devices

### 2. Client Registration
1. Clients connect to the server and register their display capabilities
2. Server assigns unique identifiers and tracks client status
3. Clients report their hardware specifications and streaming capabilities

### 3. Content Management
1. Upload video files through the web interface
2. System validates video format and creates streaming configurations
3. Content is organized into playlists and schedules

### 4. Streaming Operations
1. Create streaming groups by selecting displays and content
2. Configure streaming parameters (quality, protocol, synchronization)
3. Start streaming with real-time monitoring and control

### 5. Monitoring & Control
1. Real-time status updates for all clients and streams
2. Performance metrics and error reporting
3. Remote control capabilities for troubleshooting

## 🛠️ Technology Stack

### Backend
- **Python 3.8+**: Core application logic
- **Flask**: Web framework and API server
- **Gunicorn**: Production WSGI server
- **Docker**: Containerization and deployment
- **FFmpeg**: Video processing and streaming
- **SRT Protocol**: Low-latency video streaming

### Frontend
- **React 18**: Modern UI framework
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Utility-first styling
- **Vite**: Fast build tool and dev server
- **Shadcn/ui**: High-quality component library

### Client
- **Python 3.8+**: Cross-platform compatibility
- **Requests**: HTTP client for server communication
- **FFmpeg**: Video playback and streaming
- **Raspberry Pi OS**: Optimized for embedded displays

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Docker and Docker Compose
- Node.js 18+ (for frontend development)
- FFmpeg installed on client devices

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
python flask_app.py
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Client Setup
```bash
cd client
chmod +x setup_client.sh
./setup_client.sh
```

## 📖 Documentation

- **[Backend API Documentation](backend/README.md)**: Detailed API endpoints and configuration
- **[Frontend Development Guide](frontend/README.md)**: Component architecture and development
- **[Raspberry Pi Setup Guide](client/RASPBERRY_PI_SETUP.md)**: Complete client setup instructions
- **[Project Documentation](Documentations/)**: Research papers and technical documentation

## 🔍 Use Cases

### Digital Signage
- Shopping malls and retail environments
- Corporate lobbies and meeting rooms
- Transportation hubs and public spaces

### Video Walls
- Control rooms and monitoring centers
- Event venues and entertainment spaces
- Educational institutions and training facilities

### Multi-Display Setups
- Conference rooms and presentation spaces
- Exhibition halls and trade shows
- Home theater and gaming setups

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines for:
- Code style and standards
- Testing requirements
- Pull request process
- Issue reporting

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🆘 Support

- **Documentation**: Check the docs folder for detailed guides
- **Issues**: Report bugs and feature requests on GitHub
- **Community**: Join discussions in our community forums
- **Email**: Contact the development team for enterprise support

## 🔮 Roadmap

### Upcoming Features
- **AI-powered Content Optimization**: Automatic quality adjustment based on network conditions
- **Advanced Analytics**: Detailed performance metrics and usage analytics
- **Mobile App**: Native mobile applications for remote management
- **Cloud Integration**: AWS, Azure, and Google Cloud deployment options
- **Edge Computing**: Distributed processing for improved performance

### Long-term Vision
- **Global Scale**: Multi-region deployment and content delivery
- **Machine Learning**: Predictive maintenance and performance optimization
- **IoT Integration**: Smart display and sensor integration
- **Blockchain**: Decentralized content distribution and rights management

---

**Built with ❤️ by the OpenVideoWalls Team**

*Empowering organizations to create stunning multi-screen experiences with open-source technology.*
