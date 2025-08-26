# Multi-Screen Streaming Management Frontend

A modern React-based frontend for managing multi-screen video streaming systems, built with TypeScript, Vite, and shadcn/ui components.

## Architecture

The frontend follows a clean, component-based architecture with organized configuration:

```
frontend/
├── src/                    # Source code
│   ├── core/              # Core application files
│   │   ├── App.tsx            # Main application component
│   │   ├── main.tsx           # Application entry point
│   │   ├── App.css            # Application-specific styles
│   │   ├── index.css          # Global styles
│   │   ├── vite-env.d.ts      # Vite environment types
│   │   └── pages/             # Page components
│   │       ├── Index.tsx          # Main application page
│   │       └── NotFound.tsx       # 404 error page
│   ├── features/           # Feature-specific components
│   │   ├── StreamsTab/         # Streaming management interface
│   │   │   ├── StreamsTab.tsx      # Main streaming component
│   │   │   ├── StreamsTabHeader.tsx # Streaming header
│   │   │   ├── StreamsTabGroups.tsx # Group management
│   │   │   ├── StreamsTabStats.tsx  # Statistics display
│   │   │   └── hooks/              # Streaming-specific hooks
│   │   ├── ClientsTab.tsx      # Client management interface
│   │   └── VideoFilesTab.tsx   # Video file management
│   └── shared/             # Shared utilities and components
│       ├── ui/                 # shadcn/ui component library
│       │   ├── GroupCard/          # Group card components
│       │   ├── button.tsx          # Button component
│       │   ├── card.tsx            # Card component
│       │   └── ...                 # Other UI components
│       ├── ErrorSystem/        # Error handling and notifications
│       │   ├── ErrorContext.jsx     # Error context provider
│       │   ├── ErrorNotification.jsx # Error display
│       │   └── useErrorHandler.js   # Error handling hook
│       ├── hooks/              # Custom React hooks
│       │   └── use-mobile.tsx      # Mobile responsiveness hook
│       ├── API/                # API integration
│       │   ├── api.ts              # API client configuration
│       │   └── utils.ts            # API utility functions
│       └── types/               # TypeScript type definitions
│           └── index.ts            # Main type definitions
├── config/                 # Configuration files
│   ├── build/                  # Build configuration
│   │   └── vite.config.ts      # Vite build settings
│   ├── typescript/             # TypeScript configuration
│   │   ├── tsconfig.app.json   # App-specific TS config
│   │   └── tsconfig.node.json  # Node.js TS config
│   ├── styling/                # Styling configuration
│   │   ├── tailwind.config.ts  # Tailwind CSS config
│   │   └── components.json     # shadcn/ui config
│   └── linting/                # Code quality
│       └── eslint.config.js    # ESLint configuration
├── public/                 # Static assets
│   ├── placeholder.svg         # Placeholder image
│   ├── robots.txt              # SEO configuration
│   └── UB.ico                  # Favicon
├── dist/                    # Build output (generated)
├── node_modules/            # Dependencies (generated)
├── index.html               # Main HTML template
├── error_lookup.html        # Error lookup interface
├── package.json             # Dependencies and scripts
├── postcss.config.js        # PostCSS configuration
└── tsconfig.json            # Root TypeScript config
```

## Features

### **Streaming Management**
- **StreamsTab** - Create and manage streaming groups
- **Real-time Updates** - Live streaming status monitoring
- **Group Operations** - Create, edit, and delete streaming groups
- **Client Assignment** - Assign clients to streaming groups

### **Client Management**
- **ClientsTab** - Monitor and manage connected clients
- **Client Status** - Real-time client connection status
- **Client Assignment** - Assign clients to specific groups
- **Performance Monitoring** - Track client performance metrics

### **Video Management**
- **VideoFilesTab** - Upload and manage video content
- **File Validation** - Video file format and quality validation
- **Storage Management** - Organize and categorize video files
- **Upload Interface** - Drag-and-drop file uploads

### **Error System**
- **Error Context** - Centralized error state management
- **Error Notifications** - User-friendly error messages
- **Error Logging** - Comprehensive error tracking
- **Recovery Options** - Automatic error recovery

## Quick Start

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Start Development Server
```bash
npm run dev
```

The application will be available at `http://localhost:5173`

### 3. Build for Production
```bash
npm run build
```

### 4. Preview Production Build
```bash
npm run preview
```

## Technology Stack

### **Core Framework**
- **React 18** - Modern React with hooks and concurrent features
- **TypeScript** - Type-safe JavaScript development
- **Vite** - Fast build tool and development server

### **UI Components**
- **shadcn/ui** - High-quality, accessible component library
- **Radix UI** - Unstyled, accessible component primitives
- **Tailwind CSS** - Utility-first CSS framework
- **Lucide React** - Beautiful, consistent icon library

### **State Management**
- **React Query (TanStack Query)** - Server state management
- **React Context** - Local state management
- **React Router** - Client-side routing

### **Form Handling**
- **React Hook Form** - Performant form library
- **Zod** - TypeScript-first schema validation
- **Hookform Resolvers** - Form validation integration

### **Development Tools**
- **ESLint** - Code quality and consistency
- **PostCSS** - CSS processing and optimization
- **SWC** - Fast JavaScript/TypeScript compiler

## Component Architecture

### **Core Components**
- **App.tsx** - Application root with providers and routing
- **main.tsx** - Application entry point
- **Index.tsx** - Main page with tabbed interface
- **NotFound.tsx** - 404 error page

### **Feature Components**
- **StreamsTab** - Streaming group management with sub-components:
  - StreamsTabHeader - Group creation and management
  - StreamsTabGroups - Group display and operations
  - StreamsTabStats - Statistics and metrics
  - Custom hooks for data management
- **ClientsTab** - Client monitoring and management
- **VideoFilesTab** - Video file management interface

### **Shared Components**
- **UI Component Library** - shadcn/ui components organized by functionality
- **GroupCard Components** - Reusable group display components
- **Error System** - Centralized error handling and notifications
- **Custom Hooks** - Reusable React hooks
- **API Integration** - Backend communication utilities
- **Type Definitions** - TypeScript interfaces and types

### **Error Handling**
- **ErrorProvider** - Centralized error context
- **ErrorNotification** - User-facing error display
- **Error Boundaries** - Graceful error recovery

## Configuration

### **Build Configuration**
- **Vite** - Fast development and optimized builds
- **TypeScript** - Strict type checking and modern JS features
- **PostCSS** - CSS processing and optimization

### **Styling Configuration**
- **Tailwind CSS** - Utility-first CSS framework
- **shadcn/ui** - Component library configuration
- **Responsive Design** - Mobile-first approach

### **Code Quality**
- **ESLint** - Code style and quality enforcement
- **TypeScript** - Type safety and IntelliSense
- **Prettier** - Code formatting (via ESLint)

## API Integration

### **Backend Communication**
- **REST API** - HTTP-based communication with backend
- **Real-time Updates** - Live data synchronization
- **Error Handling** - Graceful API error management

### **Data Management**
- **React Query** - Server state caching and synchronization
- **Optimistic Updates** - Immediate UI feedback
- **Background Refetching** - Automatic data updates

## Development Workflow

### **Local Development**
1. Start development server with `npm run dev`
2. Make changes to source files
3. View live updates in browser
4. Use React DevTools for debugging

### **Code Quality**
1. ESLint automatically checks code quality
2. TypeScript provides type safety
3. Pre-commit hooks ensure code consistency
4. Automated testing (when implemented)

### **Building and Deployment**
1. Run `npm run build` for production build
2. Test production build with `npm run preview`
3. Deploy `dist/` folder to web server
4. Configure environment variables for production

## Browser Support

- **Modern Browsers** - Chrome, Firefox, Safari, Edge
- **Mobile Support** - Responsive design for all devices
- **Progressive Enhancement** - Graceful degradation for older browsers

## Performance

- **Code Splitting** - Automatic route-based code splitting
- **Lazy Loading** - Components loaded on demand
- **Optimized Bundles** - Tree-shaking and minification
- **Fast Refresh** - Instant updates during development

## Contributing

1. Follow the established code style and patterns
2. Use TypeScript for all new code
3. Implement proper error handling
4. Add appropriate TypeScript types
5. Test changes thoroughly before committing

## Troubleshooting

### **Common Issues**
- **Port Conflicts** - Change port in `vite.config.ts`
- **Type Errors** - Check TypeScript configuration
- **Build Failures** - Clear `node_modules` and reinstall
- **Styling Issues** - Verify Tailwind CSS configuration

### **Getting Help**
- Check the browser console for errors
- Review TypeScript compiler output
- Consult component library documentation
- Review API integration logs

## Directory Organization

### **Core Directory (`src/core/`)**
Contains the main application files that are essential for the app to run:
- **App.tsx** - Main application component with routing and providers
- **main.tsx** - Application entry point and React rendering
- **pages/** - Main page components (Index, NotFound)
- **Styles** - Global and application-specific CSS

### **Features Directory (`src/features/`)**
Organized by business functionality, each feature is self-contained:
- **StreamsTab/** - Complete streaming management functionality
- **ClientsTab.tsx** - Client monitoring and management
- **VideoFilesTab.tsx** - Video file handling and uploads

### **Shared Directory (`src/shared/`)**
Reusable components and utilities used across multiple features:
- **ui/** - shadcn/ui component library and custom UI components
- **ErrorSystem/** - Centralized error handling for the entire application
- **hooks/** - Custom React hooks for common functionality
- **API/** - Backend communication and data fetching
- **types/** - TypeScript type definitions shared across features

### **Benefits of This Structure**
- **Clear Separation** - Core, features, and shared code are logically separated
- **Feature Isolation** - Each feature can be developed independently
- **Code Reusability** - Shared components reduce duplication
- **Easy Navigation** - Developers can quickly find what they need
- **Scalable Architecture** - Easy to add new features without affecting existing code
