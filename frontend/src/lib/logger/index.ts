import { Logger, createLogger } from './core';
import { ConsoleTransport, JsonTransport, BufferTransport, PerformanceTransport } from './transports';
import { contextStore } from './context';

// Re-export types
export type { LogLevel, LogEntry, LogContext, LogTransport, Span } from './types';
export { LOG_LEVELS } from './types';

// Re-export classes
export { Logger, createLogger } from './core';
export { ConsoleTransport, JsonTransport, BufferTransport, PerformanceTransport } from './transports';
export { contextStore } from './context';
export { setupHttpLogging, createHttpTimer } from './http';

// Re-export React utilities
export {
  LoggerProvider,
  useLogger,
  useComponentLogger,
  useTracedAsync,
  useActionLogger,
  usePerformance,
  useNavigationLogger,
  useGlobalErrorLogger,
  LoggingErrorBoundary,
  withLogger,
} from './react';

/** Default transports based on environment */
const createDefaultTransports = () => {
  const transports = [];

  if (import.meta.env.DEV) {
    // Development: pretty colored console
    transports.push(new ConsoleTransport({ collapsed: true }));
    transports.push(new PerformanceTransport());
  } else {
    // Production: structured JSON for log aggregation
    transports.push(new JsonTransport());
    
    // Buffer for batch sending (you can add your own onFlush handler)
    transports.push(new BufferTransport({
      maxSize: 50,
      onFlush: async (entries) => {
        // Example: send to logging service
        // await fetch('/api/logs', { method: 'POST', body: JSON.stringify(entries) });
        console.log(`[Logger] Flushed ${entries.length} log entries`);
      },
    }));
  }

  return transports;
};

/** Pre-configured root logger instance */
export const logger = createLogger({
  namespace: 'lingua',
  level: import.meta.env.DEV ? 'debug' : 'info',
  transports: createDefaultTransports(),
});

// Create namespaced loggers for common modules
export const loggers = {
  api: logger.scope('api'),
  srs: logger.scope('srs'),
  etymology: logger.scope('etymology'),
  morphology: logger.scope('morphology'),
  phonetics: logger.scope('phonetics'),
  glossing: logger.scope('glossing'),
  production: logger.scope('production'),
  auth: logger.scope('auth'),
  ui: logger.scope('ui'),
} as const;

/** Initialize logging system (call once at app startup) */
export const initLogger = (): Logger => {
  if (import.meta.env.DEV) {
    logger.info('Logging system initialized', {
      environment: 'development',
      level: 'debug',
    });
    
    // Expose logger globally for debugging
    (window as unknown as Record<string, unknown>).__logger = logger;
    (window as unknown as Record<string, unknown>).__loggers = loggers;
    (window as unknown as Record<string, unknown>).__logContext = contextStore;
  }

  return logger;
};

// Default export
export default logger;

