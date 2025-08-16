# Configuration Files

This directory contains all configuration files organized by category:

## Directory Structure

### `/typescript/`
- `tsconfig.json` - Main TypeScript configuration
- `tsconfig.app.json` - Application-specific TypeScript settings
- `tsconfig.node.json` - Node.js/build tool TypeScript settings

### `/build/`
- `vite.config.ts` - Vite build configuration
- `postcss.config.js` - PostCSS configuration

### `/linting/`
- `eslint.config.js` - ESLint configuration

### `/styling/`
- `tailwind.config.ts` - Tailwind CSS configuration
- `components.json` - shadcn/ui component library configuration

## Usage

The root `tsconfig.json` references these configurations, and the `package.json` scripts are updated to use the new file locations.

## Benefits

- Cleaner root directory
- Logical grouping of related configurations
- Easier to maintain and understand
- Better separation of concerns
