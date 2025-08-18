# Error System Tabs

A comprehensive, tabbed interface for testing, demonstrating, and documenting the error handling system.

## Features

### **Error Testing Tab**
- **Comprehensive Error Testing**: Test all error types including FFmpeg, SRT, Docker, and Video errors
- **Error Scenarios**: Simulate real-world error conditions
- **Network & API Testing**: Test network timeouts, CORS errors, and authentication issues
- **Custom Error Codes**: Create and test custom error codes with context
- **Error Recovery**: Test error recovery and retry mechanisms
- **Quick Test All**: Run all error types sequentially for comprehensive testing

### 📚 **Examples Tab**
- **Code Examples**: Ready-to-use code snippets for different error types
- **Integration Examples**: Learn how to integrate error handling into your components
- **Best Practices**: See recommended patterns for error handling
- **Copy-Paste Ready**: All examples can be copied and used immediately

### 📖 **Documentation Tab**
- **Error Categories**: Standard HTTP error codes and their meanings
- **Custom Error Codes**: Application-specific error codes with solutions
- **Troubleshooting Guide**: Step-by-step solutions for common issues
- **Command References**: Useful commands for debugging and problem resolution

## Installation & Usage

### 1. Import the Component

```jsx
import ErrorSystemTabs from './ErrorSystemTabs';
```

### 2. Use in Your Application

```jsx
function App() {
  return (
    <div className="app">
      <ErrorSystemTabs />
    </div>
  );
}
```

### 3. Alternative: Use the Demo Component

```jsx
import ErrorSystemDemo from './ErrorSystemDemo';

function App() {
  return (
    <div className="app">
      <ErrorSystemDemo />
    </div>
  );
}
```

## Component Structure

```
ErrorSystemTabs/
├── ErrorSystemTabs.jsx      # Main tabbed component
├── ErrorSystemTabs.css      # Tab styling and layout
├── ErrorSystemDemo.jsx      # Demo wrapper component
├── ErrorSystemDemo.css      # Demo styling
└── README.md               # This documentation
```

## Available Tabs

### Testing Tab (`testing`)
- **Default tab** with comprehensive error testing capabilities
- Includes all functionality from the original `ErrorTestPanel`
- Perfect for developers and QA testing

### Examples Tab (`examples`)
- **Code examples** for all error types
- **Integration patterns** and best practices
- **Copy-paste ready** code snippets

### Documentation Tab (`documentation`)
- **Error code reference** (HTTP and custom codes)
- **Troubleshooting guides** for common issues
- **Command references** for debugging

## 🎨 Customization

### Styling
The component uses CSS custom properties and can be easily customized:

```css
/* Customize tab colors */
.tab-button.active {
  background: linear-gradient(135deg, #your-color-1, #your-color-2);
}

/* Customize header gradient */
.tabs-header {
  background: linear-gradient(135deg, #your-gradient-1, #your-gradient-2);
}
```

### Adding New Tabs
To add a new tab, modify the `tabs` array in `ErrorSystemTabs.jsx`:

```jsx
const tabs = [
  // ... existing tabs
  {
    id: 'new-tab',
    label: '🆕 New Tab',
    icon: '🆕',
    description: 'Description of the new tab'
  }
];
```

Then add the corresponding case in `renderTabContent()`:

```jsx
case 'new-tab':
  return <NewTabComponent />;
```

## 📱 Responsive Design

The component is fully responsive and works on:
- **Desktop**: Full tab layout with descriptions
- **Tablet**: Stacked tabs with responsive grids
- **Mobile**: Single-column layout with touch-friendly buttons

## 🔗 Dependencies

- **React**: 16.8+ (uses hooks)
- **CSS**: Modern CSS with flexbox and grid
- **Icons**: Emoji icons (no external icon libraries)

## Error Handler Integration

The component integrates seamlessly with the existing error handler system:

```jsx
import useErrorHandler from './useErrorHandler';

// All error testing functions are available
const {
  showError,
  showFFmpegError,
  showSRTError,
  showDockerError,
  // ... and more
} = useErrorHandler();
```

## Use Cases

### For Developers
- **Testing error handling** in development
- **Debugging error scenarios** before production
- **Learning error system** capabilities

### For QA Teams
- **Comprehensive error testing** across all error types
- **Regression testing** of error handling
- **User acceptance testing** of error messages

### For Documentation
- **Error code reference** for support teams
- **Troubleshooting guides** for users
- **Integration examples** for developers

## Migration from ErrorTestPanel

If you're currently using `ErrorTestPanel`, you can easily migrate:

```jsx
// Before
import ErrorTestPanel from './ErrorTestPanel';

// After
import ErrorSystemTabs from './ErrorSystemTabs';

// The testing tab contains all the same functionality
```

## 🎨 Theme Support

The component supports both light and dark themes through CSS variables:

```css
:root {
  --primary-color: #667eea;
  --secondary-color: #764ba2;
  --background-color: #ffffff;
  --text-color: #2d3748;
}

[data-theme="dark"] {
  --background-color: #1a202c;
  --text-color: #e2e8f0;
}
```

## Performance

- **Lazy loading**: Tab content is rendered only when needed
- **Optimized rendering**: Minimal re-renders with React hooks
- **CSS animations**: Hardware-accelerated transitions
- **Responsive images**: Optimized for different screen sizes

## 🤝 Contributing

To contribute to the error system tabs:

1. **Fork the repository**
2. **Create a feature branch**
3. **Make your changes**
4. **Test thoroughly** with different error scenarios
5. **Submit a pull request**

## 📄 License

This component is part of the Error System and follows the same license terms.

---

**Happy Error Testing!**

