# Multi-Screen Streaming Management Frontend

A modern React-based frontend for managing multi-screen video streaming systems, built with TypeScript, Vite, and shadcn/ui components.

## New Clean Folder Structure

The frontend has been reorganized with a cleaner, more logical structure:

```
frontend/src/
├── app/                    # App-level components and configuration
│   ├── App.tsx            # Main application component
│   ├── App.css            # Application-specific styles
│   ├── main.tsx           # Application entry point
│   └── vite-env.d.ts      # Vite environment types
├── components/             # Reusable UI components
│   ├── ui/                 # shadcn/ui component library
│   │   ├── GroupCard/      # Group card components
│   │   ├── button.tsx      # Button component
│   │   ├── card.tsx        # Card component
│   │   └── ...             # Other UI components
│   ├── layout/             # Layout components (currently empty)
│   └── common/             # Common components
│       ├── ErrorContext.jsx        # Error handling context
│       ├── ErrorNotification.jsx   # Error notifications
│       └── ...                     # Other common components
├── features/               # Feature-based modules
│   ├── streaming/          # Streaming management
│   │   ├── StreamsTab.tsx          # Main streaming component
│   │   ├── StreamsTabHeader.tsx    # Streaming header
│   │   ├── StreamsTabGroups.tsx    # Group management
│   │   ├── StreamsTabStats.tsx     # Statistics display
│   │   └── index.ts                # Feature exports
│   ├── clients/            # Client management
│   │   └── ClientsTab.tsx          # Client management interface
│   └── videos/             # Video management
│       └── VideoFilesTab.tsx       # Video file management
├── hooks/                  # Custom React hooks
│   ├── use-mobile.tsx              # Mobile detection hook
│   ├── useClientAssignment.ts      # Client assignment logic
│   ├── useGroupOperations.ts       # Group operations
│   └── useStreamingStatus.ts       # Streaming status management
├── lib/                    # Utilities and configurations
│   ├── api/                # API client and utilities
│   │   └── api.ts                  # API integration
│   ├── utils/              # Helper functions
│   │   └── utils.ts                # Utility functions
│   └── constants/          # App constants (currently empty)
├── types/                  # TypeScript type definitions
│   └── index.ts                    # Main type definitions
├── styles/                 # Global styles and CSS
│   └── index.css                   # Global CSS styles
└── pages/                  # Page components
    ├── Index.tsx                   # Main application page
    └── NotFound.tsx                # 404 error page
```

## Key Improvements in the New Structure

### **1. Logical Grouping**
- **`app/`** - Contains all app-level files (entry point, main app component)
- **`components/`** - All reusable UI components organized by purpose
- **`features/`** - Feature-based modules with clear separation of concerns
- **`hooks/`** - Centralized location for all custom React hooks
- **`lib/`** - Utility libraries and configurations
- **`types/`** - TypeScript definitions in one place
- **`styles/`** - Global styling and CSS
- **`pages/`** - Page-level components

### **2. Better Separation of Concerns**
- **UI Components** (`components/ui/`) - Pure UI components from shadcn/ui
- **Common Components** (`components/common/`) - Shared business logic components
- **Feature Modules** (`features/*/`) - Each feature is self-contained
- **Hooks** (`hooks/`) - All custom hooks in one location
- **Utilities** (`lib/`) - API, utilities, and constants

### **3. Improved Maintainability**
- Clear file locations make it easier to find and modify code
- Feature-based organization makes it easier to add new features
- Centralized hooks and utilities reduce duplication
- Better separation between UI components and business logic

### **4. Scalability**
- Easy to add new features by creating new directories in `features/`
- Simple to add new UI components in `components/ui/`
- Centralized hooks can be easily shared across features
- Clear structure makes onboarding new developers easier

## Getting Started

### Prerequisites
- Node.js 18+ 
- npm or yarn package manager
- Backend server running (see [Backend Setup](../backend/README.md))

### 1. Environment Configuration

**IMPORTANT**: You must create a `.env` file in the `frontend/` directory to configure the backend server connection.

#### Create `.env` File

In the `frontend/` directory, create a file named `.env`:

```bash
# Navigate to the frontend directory
cd frontend

# Create the .env file
touch .env
```

#### Configure Server Connection

Edit the `.env` file and add the backend server URL:

```env
# Backend API Configuration
VITE_API_BASE_URL=http://YOUR_SERVER_IP:5000
```

#### Example Configurations

**Local Development (Backend running locally):**
```env
VITE_API_BASE_URL=http://localhost:5000
```

**Production/Remote Server:**
```env
VITE_API_BASE_URL=http://your-server-domain.com:5000
```

#### Important Notes:
- Replace `YOUR_SERVER_IP` with the actual IP address where your backend server is running
- The port number (`:5000`) should match your backend server configuration
- The variable name **must** be prefixed with `VITE_` for Vite to include it in the build
- Do not add quotes around the URL value
- Make sure the backend server is accessible from your development machine

### 2. Install Dependencies

```bash
cd frontend
npm install
```

### 3. Start Development Server

```bash
npm run dev
```

The application will be available at `http://localhost:5173`

**Verify Connection**: When you open the application, it should connect to your backend server. Check the browser's developer console (F12) for any connection errors.

### 4. Build for Production

```bash
npm run build
```

### 5. Preview Production Build

```bash
npm run preview
```

## Environment Variables

The frontend uses environment variables to configure API connections and other settings:

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `VITE_API_BASE_URL` | Backend server URL | Yes | `http://192.168.1.100:5000` |

**Note**: Only variables prefixed with `VITE_` are accessible in the frontend code for security reasons.

## Troubleshooting

### Common Issues

** "Cannot connect to backend" or API errors:**
- Check that your `.env` file exists and contains the correct server URL
- Verify the backend server is running and accessible
- Test the connection by visiting the backend URL in your browser
- Check for firewall or network issues

** Environment variables not loading:**
- Ensure the variable name starts with `VITE_`
- Restart the development server after changing `.env`
- Check that there are no extra spaces or quotes around values

** CORS errors in browser console:**
- The backend server needs to be configured to allow requests from your frontend URL
- Check the backend CORS configuration

### Testing Backend Connection

You can test if your backend is accessible by:

1. **Browser test**: Visit `http://YOUR_SERVER_IP:5000` in your browser
2. **Command line test**: `curl http://YOUR_SERVER_IP:5000/api/health` (if health endpoint exists)

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

### **App Level**
- **App.tsx** - Application root with providers and routing
- **main.tsx** - Application entry point

### **Page Components**
- **Index.tsx** - Main page with tabbed interface
- **NotFound.tsx** - 404 error page

### **Feature Components**
- **Streaming Feature** (`features/streaming/`):
  - StreamsTab - Main streaming interface
  - StreamsTabHeader - Group creation and management
  - StreamsTabGroups - Group display and operations
  - StreamsTabStats - Statistics and metrics
- **Clients Feature** (`features/clients/`):
  - ClientsTab - Client monitoring and management
- **Videos Feature** (`features/videos/`):
  - VideoFilesTab - Video file management interface

### **Shared Components**
- **UI Component Library** (`components/ui/`) - shadcn/ui components
- **Common Components** (`components/common/`) - Business logic components
- **Error System** - Centralized error handling and notifications

### **Custom Hooks**
- **use-mobile** - Mobile device detection
- **useClientAssignment** - Client assignment logic
- **useGroupOperations** - Group management operations
- **useStreamingStatus** - Streaming status management

### **Utilities and API**
- **API Integration** (`lib/api/`) - Backend communication
- **Utility Functions** (`lib/utils/`) - Helper functions
- **Type Definitions** (`types/`) - TypeScript interfaces

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
5. Test changes thoroughly before submitting
6. Follow the new folder structure for organizing code

## Support

- Check the browser developer console for detailed error messages
- Review the backend logs if API calls are failing
- Ensure all environment variables are correctly configured
- Verify network connectivity between frontend and backend

## Migration Notes

If you're working with the old structure, here's how files were reorganized:

- `src/core/*` → `src/app/*` (app-level files)
- `src/core/pages/*` → `src/pages/*` (page components)
- `src/core/index.css` → `src/styles/index.css` (global styles)
- `src/shared/ui/*` → `src/components/ui/*` (UI components)
- `src/shared/API/*` → `src/lib/api/*` (API utilities)
- `src/shared/types/*` → `src/types/*` (type definitions)
- `src/shared/hooks/*` → `src/hooks/*` (custom hooks)
- `src/shared/ErrorSystem/*` → `src/components/common/*` (error handling)
- `src/features/StreamsTab/*` → `src/features/streaming/*` (streaming feature)
- `src/features/ClientsTab.tsx` → `src/features/clients/ClientsTab.tsx`
- `src/features/VideoFilesTab.tsx` → `src/features/videos/VideoFilesTab.tsx`