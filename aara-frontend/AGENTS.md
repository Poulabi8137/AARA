# AARA Frontend Development Guidelines

## Project Overview

This document provides comprehensive development guidelines for the AARA frontend project, built with Next.js 16, React 19, TypeScript, and a modern tech stack.

## Project Setup

### 1. Initial Environment Setup

```bash
# Create project
deploy-space create aara-frontend --template nextjs

# Navigate to project
deploy-space cd aara-frontend

# Install dependencies (including dev dependencies)
deploy-space npm install

# Install dev dependencies separately (if needed)
deploy-space npm install --only=dev
```

### 2. Environment Configuration

Create `.env.local` for local development:

```env
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/api/v1/ws
NEXT_PUBLIC_APP_NAME=AARA
NEXT_PUBLIC_APP_URL=http://localhost:3000

# Supabase Authentication (if used)
NEXT_PUBLIC_SUPABASE_URL=your-supabase-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key

# App Configuration
NEXT_PUBLIC_FEATURE_FLAGS=your-flags
NEXT_PUBLIC_ENVIRONMENT=development
```

### 3. Script Commands

| Command                      | Description                                |
| ---------------------------- | ------------------------------------------ |
| `deploy-space dev`           | Start development server with hot reload   |
| `deploy-space build`         | Build for production (optimized, minified) |
| `deploy-space start`         | Start production server                    |
| `deploy-space lint`          | Run ESLint + Prettier checks               |
| `deploy-space typecheck`     | TypeScript type checking                   |
| `deploy-space test`          | Run Vitest test suite                      |
| `deploy-space test:ui`       | Run Vitest with UI mode                    |
| `deploy-space test:coverage` | Run tests and generate coverage report     |

## Development Environment

### IDE Configuration

- **VS Code**: Recommended
- **Extensions**:
  - ESLint
  - Prettier - Code formatter
  - ES7 React & Next.js snippets
  - Git Lens
  - Imports
  - npm Intellisense
  - Path Intellisense

### Code Formatting

```json
// .prettierrc.json
{
  "semi": false,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100,
  "arrowParens": "always"
}
```

### Linting Configuration

```json
// .eslintrc.json
{
  "env": {
    "browser": true,
    "es2021": true,
    "node": true
  },
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react/recommended",
    "plugin:react-hooks/recommended",
    "prettier"
  ],
  "parserOptions": {
    "ecmaVersion": "latest",
    "sourceType": "module",
    "ecmaFeatures": {
      "jsx": true
    }
  },
  "plugins": ["@typescript-eslint", "react", "react-hooks", "prettier"],
  "rules": {
    "prettier/prettier": "error",
    "react/react-in-jsx-scope": "off",
    "@typescript-eslint/no-unused-vars": "error",
    "@typescript-eslint/explicit-function-return-type": "off",
    "react-hooks/rules-of-hooks": "error",
    "react-hooks/exhaustive-deps": "error"
  }
}
```

### TypeScript Configuration

```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolutionStrategy": "bundler",
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noImplicitAny": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "noImplicitReturns": true,
    "noFallthroughCaseInSwitch": true,
    "noUnusedTypeParameters": true,
    "exactOptionalPropertyTypes": true,
    "allowUnusedLabels": false,
    "allowUnreachableCode": false,
    "jsx": "react-jsx",
    "isolatedModules": true,
    "declaration": true,
    "declarationMap": true,
    "declarationDir": "types",
    "sourceMap": true,
    "inlineSources": true,
    "removeComments": true,
    "incremental": true,
    "tsBuildInfoFile": "./node_modules/.cache/tsbuildinfo"
  },
  "include": ["src/"],
  "exclude": ["node_modules", ".next", "dist"]
}
```

## Component Architecture

### Folder Structure

```
src/
├── components/                    # React components
│   ├── ui/                        # shadcn/ui primitives
│   ├── layout/                    # Layout components
│   ├── auth/                      # Authentication components
│   ├── workspace/                  # Workspace components
│   ├── papers/                    # Paper library components
│   ├── analysis/                  # Analysis components
│   ├── agents/                    # Agent workflow components
│   ├── ideas/                     # Idea generation components
│   ├── draft/                     # Draft editor components
│   ├── export/                     # Export components
│   ├── settings/                   # Settings components
│   └── shared/                     # Shared UI components
├── features/                       # Feature-specific compositions
│   ├── workspace-overview/        # Workspace overview feature
│   ├── paper-import-flow/         # Paper import feature
│   └── workflow-execution/        # Workflow execution feature
├── hooks/                         # Custom hooks
├── services/                      # API services
├── stores/                        # Zustand stores
├── providers/                     # React context providers
├── animations/                    # Motion variants
├── lib/                           # Utility functions
├── types/                         # Type definitions
├── utils/                         # Helper functions
└── config/                        # Project configuration
```

### Component Guidelines

#### Props Interface

- Use explicit interfaces instead of `any`
- Prefer `interface` for public APIs, `type` for unions/utility types
- Required props should be explicitly marked
- Default values for optional props using TypeScript defaults

#### Type Safety

```typescript
// Recommended
interface ButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: "default" | "destructive" | "outline";
  disabled?: boolean;
}

// Avoid this
interface BadButtonProps {
  children?: any;
  onClick?: Function;
  variant?: string;
  disabled?: boolean;
}
```

#### Generic Components

```typescript
interface GenericListProps<T extends { id: string }> {
  items: T[];
  renderItem: (item: T) => React.ReactNode;
  keyExtractor?: (item: T) => string;
}

function GenericList<T extends { id: string }>({
  items,
  renderItem,
  keyExtractor
}: GenericListProps<T>) {
  return (
    <div>
      {items.map((item) => (
        <div key={keyExtractor?.(item) ?? item.id}>
          {renderItem(item)}
        </div>
      ))}
    </div>
  );
}
```

### Component Naming Conventions

- **Components**: PascalCase (e.g., `WorkspaceCard`, `LoadingSpinner`)
- **Hooks**: camelCase (e.g., `useWindowSize`, `useLocalStorage`)
- **Types/Interfaces**: PascalCase (e.g., `User`, `ApiResponse`)
- **Constants/Enums**: UPPER_SNAKE_CASE (e.g., `HTTP_METHODS`, `API_ENDPOINTS`)

## State Management

### Global State (Zustand)

```typescript
// auth-store.ts
interface AuthStore {
  user: User | null;
  tokens: { access: string; refresh: string } | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  setTokens: (tokens: { access: string; refresh: string }) => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  tokens: null,
  isAuthenticated: false,
  isLoading: false,

  login: async (email, password) => {
    // Login logic here
  },
  logout: () => {
    // Logout logic here
  },
  setTokens: (tokens) => {
    // Set tokens
  },
}));
```

### Server State (TanStack Query)

```typescript
// queryClient.ts
import { QueryClient } from "@tanstack/react-query";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000, // 30 seconds
      gcTime: 5 * 60_000, // 5 minutes
      retry: 3, // 3 retries with backoff
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10000),
      refetchOnWindowFocus: true,
    },
    mutations: {
      retry: 1,
    },
  },
});

export default queryClient;
```

**Query Key Conventions:**

```typescript
// api/queries.ts
export const queryKeys = {
  workspaces: ["workspaces"],
  workspace: (id: string) => ["workspaces", id],
  workspaceProjects: (workspaceId: string) => [
    "workspaces",
    workspaceId,
    "projects",
  ],
  papers: ["papers"],
  paper: (id: string) => ["papers", id],
  workflows: ["workflows"],
  workflow: (id: string) => ["workflows", id],
  dashboard: ["dashboard"],
  dashboardWorkflow: (id: string) => ["dashboard", "workflows", id],
} as const;

// Usage:
const { data: workspaces } = useQuery({
  queryKey: queryKeys.workspaces,
  queryFn: () => fetchWorkspaces(),
});
```

## API Integration

### API Client

```typescript
// services/api-client.ts
import axios, { type AxiosRequestConfig, type AxiosResponse } from "axios";

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true,
});

// Request interceptor for auth
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    const originalRequest = error.config;

    // Handle 401 errors
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      // Attempt to refresh token
      try {
        await refreshToken();
        return apiClient(originalRequest);
      } catch (refreshError) {
        // Token refresh failed
        logout();
        window.location.href = "/login";
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  },
);

export default apiClient;
```

### API Services

```typescript
// services/workspace-service.ts
import apiClient from "./api-client";

export interface Workspace {
  id: string;
  name: string;
  description?: string;
  ownerId: string;
  memberCount: number;
  status: "active" | "archived";
  createdAt: string;
  updatedAt: string;
}

export interface CreateWorkspaceData {
  name: string;
  description?: string;
}

export interface UpdateWorkspaceData {
  name?: string;
  description?: string;
  status?: "active" | "archived";
}

export const workspaceService = {
  // Get all workspaces
  getAll: () => apiClient.get<Workspace[]>("/workspaces"),

  // Get single workspace
  getOne: (id: string) => apiClient.get<Workspace>(`/workspaces/${id}`),

  // Create workspace
  create: (data: CreateWorkspaceData) =>
    apiClient.post<Workspace>("/workspaces", data),

  // Update workspace
  update: (id: string, data: UpdateWorkspaceData) =>
    apiClient.patch<Workspace>(`/workspaces/${id}`, data),

  // Delete workspace
  delete: (id: string) => apiClient.delete(`/workspaces/${id}`),

  // Add workspace member
  addMember: (workspaceId: string, userId: string, role: string) =>
    apiClient.post(`/workspaces/${workspaceId}/members`, { userId, role }),

  // Remove workspace member
  removeMember: (workspaceId: string, userId: string) =>
    apiClient.delete(`/workspaces/${workspaceId}/members/${userId}`),
};
```

## Component Library

### Base Components

#### Button

```typescript
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link' | 'success' | 'warning';
  size?: 'default' | 'sm' | 'lg' | 'icon';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, isLoading, leftIcon, rightIcon, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          buttonVariants({ variant, size, className })
        )}
        disabled={isLoading || props.disabled}
        {...props}
      >
        {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        {leftIcon && !isLoading && <span className="mr-2">{leftIcon}</span>}
        {props.children}
        {rightIcon && <span className="ml-2">{rightIcon}</span>}
      </button>\n    );
  }
);

Button.displayName = 'Button';
```

#### Card

```typescript
interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'glass' | 'elevated';
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = 'default', ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'rounded-lg border border-border bg-card p-6 shadow-sm',
          variant === 'glass' && 'bg-card/80 backdrop-blur-md',
          variant === 'elevated' && 'shadow-md hover:shadow-lg',
          className
        )}
        {...props}
      />
    );
  }
);

Card.displayName = 'Card';
```

#### Input

```typescript
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, error, leftIcon, rightIcon, ...props }, ref) => {
    return (
      <div className="relative">
        {leftIcon && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
            {leftIcon}
          </div>
        )}
        <input
          ref={ref}
          className={cn(
            'flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm',
            'ring-offset-background placeholder:text-muted-foreground',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
            'disabled:cursor-not-allowed disabled:opacity-50',
            leftIcon && 'pl-10',
            rightIcon && 'pr-10',
            error && 'border-destructive focus-visible:ring-destructive',
            className
          )}
          {...props}
        />
        {rightIcon && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground">
            {rightIcon}
          </div>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';
```

### Layout Components

#### AppShell

```typescript
interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <AppHeader />
      <div className="flex flex-1">
        <AppSidebar />
        <main className="flex-1 overflow-hidden p-4 md:p-6">
          <div className="mx-auto max-w-7xl">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
```

#### AppSidebar

```typescript
interface AppSidebarProps {
  collapsed?: boolean;
}

export function AppSidebar({ collapsed }: AppSidebarProps) {
  const { workspaces, setCurrentWorkspace } = useWorkspaceStore();

  return (
    <aside
      className={cn(
        'hidden md:flex h-full w-72 flex-col border-r bg-sidebar',
        collapsed && 'w-20'
      )}
    >
      <div className="flex h-14 items-center border-b px-4">
        <Logo collapsed={collapsed} />
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        <nav className="space-y-1">
          {workspaces.map((workspace) => (
            <WorkspaceNavItem
              key={workspace.id}
              workspace={workspace}
              collapsed={collapsed}
              onClick={() => setCurrentWorkspace(workspace.id)}
            />
          ))}
        </nav>
      </div>

      <div className="border-t p-4">
        <ThemeToggle collapsed={collapsed} />
      </div>
    </aside>
  );
}
```

## Design System

### Color Palette

```css
:root {
  --background: 0 0% 100%;
  --foreground: 240 10% 3.9%;
  --card: 0 0% 100%;
  --card-foreground: 240 10% 3.9%;
  --popover: 0 0% 100%;
  --popover-foreground: 240 10% 3.9%;
  --primary: 240 5.9% 10%;
  --primary-foreground: 0 0% 98%;
  --secondary: 240 4.8% 95.9%;
  --secondary-foreground: 240 5.9% 6.9%;
  --muted: 240 4.8% 95.9%;
  --muted-foreground: 240 3.8% 46.1%;
  --accent: 240 4.8% 95.9%;
  --accent-foreground: 240 5.9% 6.9%;
  --destructive: 0 84.2% 60.2%;
  --destructive-foreground: 0 0% 98%;
  --border: 240 5.9% 90%;
  --input: 240 5.9% 90%;
  --ring: 240 5.2% 33.9%;

  /* AARA-specific colors */
  --aura-accent: 262 83% 58%; /* purple-600 */
  --aura-accent-foreground: 0 0% 100%;
  --aura-accent-soft: 262 83% 58% / 15%;
  --aura-success: 142 71% 45%; /* green-600 */
  --aura-success-soft: 142 71% 45% / 15%;
  --aura-warning: 32 98% 56%; /* orange-500 */
  --aura-warning-soft: 32 98% 56% / 15%;
  --aura-error: 0 84% 60%; /* red-500 */
  --aura-error-soft: 0 84% 60% / 15%;
  --aura-info: 199 89% 48%; /* blue-500 */
  --aura-info-soft: 199 89% 48% / 15%;
}
```

### Typography

```css
:root {
  --font-sans:
    "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui,
    sans-serif;
  --font-mono: "JetBrains Mono", "Fira Code", "Cascadia Code", monospace;

  --text-xs: 0.75rem; /* 12px */
  --text-sm: 0.875rem; /* 14px */
  --text-base: 1rem; /* 16px */
  --text-lg: 1.125rem; /* 18px */
  --text-xl: 1.25rem; /* 20px */
  --text-2xl: 1.5rem; /* 24px */
  --text-3xl: 1.875rem; /* 30px */
  --text-4xl: 2.25rem; /* 36px */
  --text-5xl: 3rem; /* 48px */
}
```

### Spacing Scale

```css
:root {
  --space-0: 0;
  --space-1: 0.25rem; /* 4px */
  --space-2: 0.5rem; /* 8px */
  --space-3: 0.75rem; /* 12px */
  --space-4: 1rem; /* 16px */
  --space-5: 1.25rem; /* 20px */
  --space-6: 1.5rem; /* 24px */
  --space-7: 1.75rem; /* 28px */
  --space-8: 2rem; /* 32px */
  --space-9: 2.25rem; /* 36px */
  --space-10: 2.5rem; /* 40px */
  --space-11: 2.75rem; /* 44px */
  --space-12: 3rem; /* 48px */
  --space-14: 3.5rem; /* 56px */
  --space-16: 4rem; /* 64px */
  --space-20: 5rem; /* 80px */
  --space-24: 6rem; /* 96px */
  --space-28: 7rem; /* 112px */
  --space-32: 8rem; /* 128px */
}
```

### Border Radius

```css
:root {
  --radius: 0.375rem; /* 6px */
  --radius-sm: 0.25rem; /* 4px */
  --radius-md: 0.5rem; /* 8px */
  --radius-lg: 0.75rem; /* 12px */
  --radius-xl: 1rem; /* 16px */
  --radius-2xl: 1.5rem; /* 24px */
  --radius-full: 9999px;
}
```

### Shadows

```css
:root {
  --shadow-xs: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.1);
  --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1);
  --shadow-xl: 0 20px 25px rgba(0, 0, 0, 0.1);
  --shadow-2xl: 0 25px 50px rgba(0, 0, 0, 0.15);

  /* AARA-specific shadows */
  --shadow-glow: 0 0 20px rgba(108, 92, 231, 0.15);
  --shadow-glow-hover: 0 0 30px rgba(108, 92, 231, 0.25);
  --shadow-glow-success: 0 0 20px rgba(0, 214, 143, 0.15);
  --shadow-glow-warning: 0 0 20px rgba(255, 170, 0, 0.15);
}
```

## Animation & Motion

### Motion Configuration

```typescript
// motion-config.ts
import { MotionConfig } from "framer-motion";

export const animationConfig: MotionConfig = {
  reduceMotion: "user",
  transition: {
    type: "spring",
    damping: 20,
    stiffness: 100,
    mass: 1,
  },
  variants: {
    fade: {
      initial: { opacity: 0 },
      animate: { opacity: 1 },
      exit: { opacity: 0 },
    },
    slideUp: {
      initial: { opacity: 0, y: 20 },
      animate: { opacity: 1, y: 0 },
      exit: { opacity: 0, y: -20 },
    },
    scale: {
      initial: { opacity: 0, scale: 0.95 },
      animate: { opacity: 1, scale: 1 },
      exit: { opacity: 0, scale: 0.95 },
    },
  },
};
```

### Animation Guidelines

#### Micro-interactions

```typescript
// Hover effects
const hoverAnimation = {
  scale: 1.05,
  transition: { duration: 0.2, ease: "easeInOut" },
};

// Button click
const tapAnimation = {
  scale: 0.95,
  transition: { duration: 0.1, ease: "easeInOut" },
};
```

#### Page Transitions

```typescript
// Page transition variants
const pageTransitionVariants = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -10 },
  transition: { duration: 0.3, ease: "easeOut" },
};
```

#### Modal Transitions

```typescript
// Modal animation variants
const modalVariants = {
  hidden: { opacity: 0, scale: 0.95, y: -20 },
  visible: { opacity: 1, scale: 1, y: 0, transition: { duration: 0.2 } },
  exit: { opacity: 0, scale: 0.95, y: -20, transition: { duration: 0.15 } },
};
```

## State Management

### Zustand Configuration

```typescript
// stores/auth-store.ts
import { create } from "zustand";
import { devtools } from "zustand/middleware";

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  setUser: (user: User) => void;
}

export const useAuthStore = create<AuthState>()(
  devtools((set) => ({
    user: null,
    isAuthenticated: false,
    isLoading: false,

    login: async (email, password) => {
      set({ isLoading: true });
      try {
        const response = await loginUser(email, password);
        set({
          user: response.user,
          isAuthenticated: true,
          isLoading: false,
        });
      } catch (error) {
        set({ isLoading: false });
        throw error;
      }
    },

    logout: () => {
      logoutUser();
      set({ user: null, isAuthenticated: false });
    },

    setUser: (user) => {
      set({ user, isAuthenticated: !!user });
    },
  })),
);
```

### TanStack Query Configuration

```typescript
// lib/query-client.ts
import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      gcTime: 1000 * 60 * 10, // 10 minutes
      retry: 3,
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 30000),
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
    },
    mutations: {
      retry: 1,
      onError: (error) => {
        console.error("Mutation error:", error);
        // Global error handling
      },
    },
  },
});
```

## Routing

### Route Configuration

```typescript
// app/(dashboard)/workspace/[workspaceId]/page.tsx
import { notFound } from '@/lib/utils';
import { workspaceService } from '@/services/workspace-service';
import { useQuery } from '@tanstack/react-query';

export default function WorkspacePage({
  params: { workspaceId }
}: { params: { workspaceId: string } }) {
  const { data: workspace, isLoading, error } = useQuery({
    queryKey: ['workspace', workspaceId],
    queryFn: () => workspaceService.getOne(workspaceId),
    staleTime: 1000 * 60 * 5,
    throwOnError: true,
  });

  if (isLoading) return <div>Loading workspace...</div>;

  if (error) return notFound();

  if (!workspace) return null;

  return <WorkspaceOverview workspace={workspace} />;
}
```

### Protected Route

```typescript
// components/auth-guard.tsx
'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/auth-store';

interface AuthGuardProps {
  children: React.ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const { isAuthenticated } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

  // Show loading state while checking auth
  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    );
  }

  return <>{children}</>;
}
```

## Utilities

### API Client

```typescript
// services/api-client.ts
import axios from "axios";

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true,
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token
    const token = localStorage.getItem("auth_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    const originalRequest = error.config;

    // Handle token refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        await refreshToken();
        return apiClient(originalRequest);
      } catch (refreshError) {
        // Refresh failed
        logout();
        window.location.href = "/login";
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  },
);

export default apiClient;
```

### Error Handler

```typescript
// lib/error-handler.ts
import { apiClient } from './api-client';

export interface AppError {
  message: string;
  status?: number;
  code?: string;
  details?: Record<string, unknown>;
}

export class AppErrorHandler {
  private static instance: AppErrorHandler;

  static getInstance(): AppErrorHandler {
    if (!AppErrorHandler.instance) {
      AppErrorHandler.instance = new AppErrorHandler();\n      }
    return AppErrorHandler.instance;
  }

  async handle(error: unknown): Promise<never> {
    const appError = this.normalizeError(error);

    // Log error
    console.error('App error:', appError);

    // Show toast notification
    this.showErrorToast(appError);

    // Handle specific error types
    switch (appError.status) {
      case 401:
        this.handleUnauthorized(appError);
        break;
      case 403:
        this.handleForbidden(appError);
        break;
      case 404:
        this.handleNotFound(appError);
        break;
      case 429:
        this.handleRateLimit(appError);
        break;
      case 500:
        this.handleServerError(appError);
        break;
    }

    // Re-throw for components to handle
    throw appError;
  }

  private normalizeError(error: unknown): AppError {
    if (axios.isAxiosError(error)) {
      return {
        message: error.response?.data?.message || error.message || 'Unknown error',
        status: error.response?.status,
        code: error.response?.data?.code,
        details: error.response?.data?.details,
      };
    }

    if (error instanceof Error) {
      return {
        message: error.message,
        status: 500,
      };
    }

    return {
      message: 'Unknown error occurred',
      status: 500,
    };
  }

  private showErrorToast(error: AppError): void {
    // Implementation depends on toast library
    // Example: toast.error(error.message, { duration: 5000 });
  }

  private handleUnauthorized(error: AppError): void {
    // Clear auth tokens
    localStorage.removeItem('auth_token');
    // Redirect to login
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
  }

  private handleForbidden(error: AppError): void {
    // Show insufficient permissions message
  }

  private handleNotFound(error: AppError): void {
    // Redirect to 404 page
    if (typeof window !== 'undefined') {
      window.location.href = '/not-found';
    }
  }

  private handleRateLimit(error: AppError): void {
    // Show rate limit message with retry after
  }

  private handleServerError(error: AppError): void {
    // Show generic server error message
  }
}
```

## Testing

### Vitest Configuration

```typescript
// vitest.config.ts
import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";
import { resolve } from "path";

export default defineConfig({
  plugins: [vue()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    coverage: {
      reporter: ["text", "json", "html"],
      exclude: ["node_modules/", "src/test/"],
    },
    include: ["**/*.{test,spec}.{js,ts,jsx,tsx}"],
    exclude: ["node_modules/", "dist/"],
  },
  resolve: {
    alias: {
      "@": resolve(__dirname, "./src"),
    },
  },
});
```

### Test Structure Example

```typescript
// components/ui/button.test.tsx
import { describe, it, expect, render, screen, userEvent } from '@/lib/test-utils'
import { Button } from './button'

describe('Button Component', () => {
  it('renders with correct text', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByRole('button')).toHaveTextContent('Click me')
  })

  it('calls onClick when clicked', async () => {
    const handleClick = vi.fn()
    render(<Button onClick={handleClick}>Click me</Button>)
    await userEvent.click(screen.getByRole('button'))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('can be disabled', () => {
    render(<Button disabled>Click me</Button>)
    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('shows loading state', () => {
    render(<Button isLoading>Loading</Button>)
    expect(screen.getByRole('button')).toHaveAttribute('disabled')
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument()
  })

  it('applies correct variant class', () => {
    render(<Button variant="destructive">Delete</Button>)
    expect(screen.getByRole('button')).toHaveClass('bg-destructive')
  })
});
```

### Testing Utilities

```typescript
// src/lib/test-utils.ts
import { beforeEach, afterEach } from 'vitest'
import { cleanup, render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Create a fresh QueryClient for each test
const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      cacheTime: 0,
    },
    mutations: {
      retry: false,
    },
  },
})

export const TestWrapper = ({ children }: { children: React.ReactNode }) => {
  const queryClient = createTestQueryClient()

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

// Re-export everything from testing-library
export * from '@testing-library/react'
export { cleanup, render }
export { default as userEvent } from '@testing-library/user-event'
export { TestWrapper }
```

## Development Workflow

### Branch Strategy

- **main**: Production-ready code
- **develop**: Continuous integration
- **feature/**: Feature development branches
- **release/**: Release preparation

### Pull Request Template

```markdown
## Summary

[Brief description of the changes]

## Changes

- Fixed bug in [component name]
- Added new feature [feature name]
- Updated tests for [component name]
- Improved error handling for [scenario]

## Testing

- [x] Unit tests added for [component]
- [x] Integration tests passing
- [x] TypeScript type checking passed
- [x] ESLint linting passed
- [x] Prettier formatting passed

## Deployment Notes

- Breaking changes: [None / Breaking changes listed]
- Environment variables: [List any required env vars]
- Database migrations: [None / List required]

## Reviewers

- [ ] Code Quality
- [ ] Functionality
- [ ] Documentation
- [ ] Accessibility
```

### Commit Message Guidelines

- Conventional Commits format: `<type>(<scope>): <description>`
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
- Examples:
  - `feat(auth): add login token refresh mechanism`
  - `fix(components/button): resolve accessibility issue`
  - `docs(components/ui): update component documentation`
  - `style(components/card): format spacing and margins`
  - `refactor(auth/store): improve state management logic`
  - `test(components/form): add validation tests`
  - `chore(deps): update dependencies to latest versions`

### Code Review Checklist

#### Before Merging

- [ ] Code follows project style guide (ESLint)
- [ ] Code is properly formatted (Prettier)
- [ ] TypeScript types are valid (typecheck)
- [ ] Tests pass (test suite)
- [ ] Documentation updated
- [ ] Components are accessible (a11y audit)
- [ ] Performance considerations addressed
- [ ] Dependencies are up to date
- [ ] Branch is up-to-date with main
- [ ] Signed commit message

#### Merge Requirements

- [ ] All CI checks passing
- [ ] Code review completed
- [ ] Pull request description filled
- [ ] Appropriate reviewers assigned
- [ ] Branch protection rules met

### Local Development Checklist

#### Before Starting

- [ ] Dependencies installed (`npm install`)
- [ ] Environment variables configured (`.env.local`)
- [ ] ESLint formatting fixed (`npm run lint -- --fix`)
- [ ] TypeScript types valid (`npm run typecheck`)

#### During Development

- [ ] Follow component architecture guidelines
- [ ] Write tests for new functionality
- [ ] Commit frequently with descriptive messages
- [ ] Update documentation as needed
- [ ] Check accessibility for new components

#### Before PR

- [ ] Code passes all linting/formatting
- [ ] TypeScript compilation succeeds
- [ ] Tests pass locally
- [ ] Code reviewed by team
- [ ] Documentation updated

## Monitoring & Observability

### Error Tracking

```typescript
// components/error-boundary.tsx
import { Component, ErrorInfo, ReactNode } from 'react'

interface ErrorBoundaryProps {
  children: ReactNode
  fallback?: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  error?: Error
  errorInfo?: ErrorInfo
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({
      error,
      errorInfo,
    })

    // Log error to external service
    logErrorToService(error, errorInfo)

    // Send to internal monitoring
    reportErrorToMonitoring(error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="error-boundary">
          <h2>Something went wrong</h2>
          <p>Please try again later.</p>
          <button onClick={() => this.setState({ hasError: false, error: undefined, errorInfo: undefined })}>
            Try again
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
```

### Performance Monitoring

#### Core Web Vitals

Track using Vercel Analytics or similar:

- **Largest Contentful Paint (LCP)**: Should be < 2.5s
- **First Input Delay (FID)**: Should be < 100ms
- **Cumulative Layout Shift (CLS)**: Should be < 0.1

### Accessibility Testing

#### Automated Testing

```bash
# Install axe-core for automated accessibility testing
npm install -D @axe-core/playwright

# Run accessibility tests in CI
npm run test:accessibility
```

#### Manual Testing Checklist

- [ ] Keyboard navigation works for all interactive elements
- [ ] Focus indicators are visible
- [ ] Screen reader announcements are appropriate
- [ ] Color contrast meets WCAG AA standards
- [ ] Text alternatives provided for images
- [ ] Form fields have proper labels
- [ ] Error messages are clear and actionable
- [ ] Page structure is semantic

## Security

### API Security

- Use HTTPS for all API calls
- Implement rate limiting
- Sanitize all user inputs
- Validate and sanitize all API responses
- Use JWT for authentication
- Implement proper error handling without information leakage

### Client-Side Security

- Store sensitive data in httpOnly cookies
- Use Content Security Policy headers
- Implement CSRF protection for state-changing operations
- Validate all user inputs before processing

### Deployment Security

- Use environment-specific configuration
- Secure environment variables
- Enable security headers
- Regular dependency updates
- Security audits and penetration testing

## Deployment

### Environment Configuration

```bash
# .env.example
NEXT_PUBLIC_API_URL=https://api.example.com/v1
NEXT_PUBLIC_WS_URL=wss://api.example.com/v1/ws
NEXT_PUBLIC_APP_NAME=AARA
NEXT_PUBLIC_APP_URL=https://app.example.com

# Supabase Authentication
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key

# App Settings
NEXT_PUBLIC_FEATURE_FLAGS=experimental/ui-optimized/performance-monitoring
NEXT_PUBLIC_ENVIRONMENT=production
NEXT_PUBLIC_LOG_LEVEL=info
```

### Production Build

```bash
# Build for production
npm run build

# Start production server
npm start
```

### Monitoring & Alerting

- Set up monitoring for API endpoints
- Track performance metrics
- Monitor error rates
- Set up alerts for critical issues

## Support & Maintenance

### Incident Response

1. **Immediate Response**: Acknowledge incident within 5 minutes
2. **Root Cause Analysis**: Identify and document the cause
3. **Resolution**: Implement fix or workaround
4. **Post-incident Review**: Analyze response and improve processes

### Documentation Updates

- Update component documentation
- Update API documentation
- Update deployment procedures
- Update troubleshooting guides

### Knowledge Base

- Maintain troubleshooting guides
- Document common issues and solutions
- Keep component usage examples
- Update deployment procedures

## Code Style Guide

### Indentation

- Use 2 spaces for indentation (not tabs)
- No trailing whitespace

### Line Length

- Keep lines under 100 characters
- Break long strings and comments into multiple lines

### Quotes

- Use single quotes for strings
- Double quotes for JSX attributes

### Semicolons

- Use semicolons for statement termination
- Omit semicolons in certain cases for cleaner code

### Naming Conventions

- Variables and functions: camelCase
- Types and interfaces: PascalCase
- Constants and enums: UPPER_SNAKE_CASE
- Files: kebab-case for components, snake_case for utilities

### Import Statements

```typescript
// Correct
import { Button } from "./button";
import { useAuthStore } from "@/stores/auth-store";

// Incorrect
import { Button } from "./button";
import { useAuthStore } from "@/stores/auth-store";
```

### File Organization

- Component files: `[component-name].tsx`
- Test files: `[component-name].test.tsx` or `[component-name].spec.tsx`
- Storybook stories: `[component-name].stories.tsx`

This document provides a comprehensive development guideline for the AARA frontend project, ensuring consistency, quality, and maintainability across all development activities.

By following these guidelines, the team can build a robust, scalable, and user-friendly React application that meets all requirements and provides an excellent user experience.

---

This completes the frontend foundation implementation. The next phase (Phase 7.3+) will build upon this foundation to implement the actual features and functionality.
