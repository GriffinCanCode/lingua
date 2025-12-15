import React, { createContext, useContext, useEffect, useRef, useCallback, Component, ErrorInfo, ReactNode } from 'react';
import type { Logger } from './core';
import { contextStore } from './context';

/** React context for logger */
const LoggerContext = createContext<Logger | null>(null);

/** Provider component to inject logger into React tree */
export const LoggerProvider: React.FC<{ logger: Logger; children: ReactNode }> = ({ logger, children }) => (
  <LoggerContext.Provider value={logger}>{children}</LoggerContext.Provider>
);

/** Hook to access the logger */
export const useLogger = (namespace?: string): Logger => {
  const logger = useContext(LoggerContext);
  if (!logger) throw new Error('useLogger must be used within LoggerProvider');
  return namespace ? logger.scope(namespace) : logger;
};

/** Hook for component lifecycle logging */
export const useComponentLogger = (componentName: string) => {
  const logger = useLogger(componentName);
  const mountTime = useRef(performance.now());
  const renderCount = useRef(0);

  useEffect(() => {
    logger.debug('Component mounted', { mountDuration: performance.now() - mountTime.current });
    return () => logger.debug('Component unmounted');
  }, [logger]);

  renderCount.current += 1;

  return {
    logger,
    renderCount: renderCount.current,
    logAction: (action: string, data?: Record<string, unknown>) => 
      logger.info(`Action: ${action}`, { ...data, component: componentName }),
  };
};

/** Hook to trace async operations */
export const useTracedAsync = (namespace?: string) => {
  const logger = useLogger(namespace);

  return useCallback(<T,>(
    operationName: string,
    asyncFn: () => Promise<T>,
    options?: { logResult?: boolean; logError?: boolean }
  ): Promise<T> => {
    const span = contextStore.startSpan(operationName);
    const start = performance.now();

    return asyncFn()
      .then((result) => {
        const duration = performance.now() - start;
        span.end({ success: true });
        logger.debug(`${operationName} completed`, { 
          duration,
          result: options?.logResult ? result : undefined,
        });
        return result;
      })
      .catch((error) => {
        const duration = performance.now() - start;
        span.end({ success: false, error: true });
        if (options?.logError !== false) {
          logger.error(`${operationName} failed`, error instanceof Error ? error : undefined, { duration });
        }
        throw error;
      });
  }, [logger]);
};

/** Hook for user action tracking */
export const useActionLogger = (namespace?: string) => {
  const logger = useLogger(namespace);

  return useCallback((
    action: string,
    metadata?: Record<string, unknown>
  ) => {
    contextStore.startTrace(action);
    logger.info(`User action: ${action}`, metadata);
  }, [logger]);
};

/** Hook for performance measurement */
export const usePerformance = (namespace?: string) => {
  const logger = useLogger(namespace);

  return {
    mark: (name: string) => {
      performance.mark(name);
    },
    measure: (name: string, startMark: string, endMark?: string) => {
      logger.measure(name, startMark, endMark);
    },
    time: <T,>(label: string, fn: () => T): T => {
      return logger.time(label, fn);
    },
    timeAsync: <T,>(label: string, fn: () => Promise<T>): Promise<T> => {
      return logger.timeAsync(label, fn);
    },
  };
};

/** Error boundary props */
interface ErrorBoundaryProps {
  logger: Logger;
  fallback?: ReactNode | ((error: Error, reset: () => void) => ReactNode);
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/** Error Boundary with integrated logging */
export class LoggingErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    const { logger, onError } = this.props;
    
    logger.fatal('React Error Boundary caught error', error, {
      componentStack: errorInfo.componentStack,
      digest: errorInfo.digest,
    });

    onError?.(error, errorInfo);
  }

  reset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    const { hasError, error } = this.state;
    const { fallback, children } = this.props;

    if (hasError && error) {
      if (typeof fallback === 'function') {
        return fallback(error, this.reset);
      }
      if (fallback) {
        return fallback;
      }
      return (
        <div style={{ padding: 20, background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8 }}>
          <h2 style={{ color: '#dc2626', margin: 0 }}>Something went wrong</h2>
          <pre style={{ color: '#7f1d1d', fontSize: 12, overflow: 'auto' }}>{error.message}</pre>
          <button
            onClick={this.reset}
            style={{
              marginTop: 12,
              padding: '8px 16px',
              background: '#dc2626',
              color: 'white',
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer',
            }}
          >
            Try again
          </button>
        </div>
      );
    }

    return children;
  }
}

/** HOC to wrap component with logging */
export const withLogger = <P extends object>(
  WrappedComponent: React.ComponentType<P & { logger: Logger }>,
  namespace: string
) => {
  const WithLogger: React.FC<Omit<P, 'logger'>> = (props) => {
    const logger = useLogger(namespace);
    return <WrappedComponent {...(props as P)} logger={logger} />;
  };
  
  WithLogger.displayName = `WithLogger(${WrappedComponent.displayName || WrappedComponent.name || 'Component'})`;
  return WithLogger;
};

/** Hook for navigation/route change logging */
export const useNavigationLogger = (namespace = 'navigation') => {
  const logger = useLogger(namespace);
  const previousPath = useRef<string>('');

  useEffect(() => {
    const handleNavigation = () => {
      const currentPath = window.location.pathname + window.location.search;
      if (previousPath.current && previousPath.current !== currentPath) {
        contextStore.startTrace('navigation');
        logger.info('Route changed', {
          from: previousPath.current,
          to: currentPath,
        });
      }
      previousPath.current = currentPath;
    };

    // Initial log
    handleNavigation();

    // Listen for history changes
    window.addEventListener('popstate', handleNavigation);
    
    // Intercept pushState/replaceState
    const originalPushState = history.pushState.bind(history);
    const originalReplaceState = history.replaceState.bind(history);
    
    history.pushState = (...args) => {
      originalPushState(...args);
      handleNavigation();
    };
    
    history.replaceState = (...args) => {
      originalReplaceState(...args);
      handleNavigation();
    };

    return () => {
      window.removeEventListener('popstate', handleNavigation);
      history.pushState = originalPushState;
      history.replaceState = originalReplaceState;
    };
  }, [logger]);
};

/** Hook for window error logging */
export const useGlobalErrorLogger = () => {
  const logger = useLogger('global');

  useEffect(() => {
    const handleError = (event: ErrorEvent) => {
      logger.error('Uncaught error', new Error(event.message), {
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
      });
    };

    const handleRejection = (event: PromiseRejectionEvent) => {
      logger.error('Unhandled promise rejection', 
        event.reason instanceof Error ? event.reason : new Error(String(event.reason))
      );
    };

    window.addEventListener('error', handleError);
    window.addEventListener('unhandledrejection', handleRejection);

    return () => {
      window.removeEventListener('error', handleError);
      window.removeEventListener('unhandledrejection', handleRejection);
    };
  }, [logger]);
};

