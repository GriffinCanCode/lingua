import type { LogLevel, LogEntry, LogTransport, LogContext, SerializedError, Span } from './types';
import { LOG_LEVELS } from './types';
import { contextStore } from './context';
import { ConsoleTransport } from './transports';

/** Serialize an Error for structured logging */
const serializeError = (err: Error): SerializedError => ({
  name: err.name,
  message: err.message,
  stack: err.stack,
  cause: err.cause instanceof Error ? serializeError(err.cause) : undefined,
});

/** Core Logger class */
export class Logger {
  private level: LogLevel;
  private namespace: string;
  private transports: LogTransport[];
  private context: LogContext;
  private enabled: boolean;

  constructor(options: {
    level?: LogLevel;
    namespace?: string;
    transports?: LogTransport[];
    context?: LogContext;
    enabled?: boolean;
  } = {}) {
    this.level = options.level ?? (import.meta.env.DEV ? 'debug' : 'info');
    this.namespace = options.namespace ?? 'app';
    this.transports = options.transports ?? [new ConsoleTransport()];
    this.context = options.context ?? {};
    this.enabled = options.enabled ?? true;
  }

  /** Create a child logger with additional namespace */
  child(namespace: string, context?: LogContext): Logger {
    return new Logger({
      level: this.level,
      namespace: `${this.namespace}:${namespace}`,
      transports: this.transports,
      context: { ...this.context, ...context },
      enabled: this.enabled,
    });
  }

  /** Create a scoped logger for a specific component */
  scope(namespace: string): Logger {
    return this.child(namespace);
  }

  private shouldLog(level: LogLevel): boolean {
    return this.enabled && LOG_LEVELS[level] >= LOG_LEVELS[this.level];
  }

  private write(
    level: LogLevel,
    message: string,
    data?: Record<string, unknown>,
    error?: Error
  ): void {
    if (!this.shouldLog(level)) return;

    const ctx = contextStore.get();
    const entry: LogEntry = {
      level,
      timestamp: new Date().toISOString(),
      namespace: this.namespace,
      message,
      data,
      context: { ...this.context, ...ctx },
      error: error ? serializeError(error) : undefined,
      traceId: ctx.traceId,
      spanId: ctx.spanId,
    };

    for (const transport of this.transports) {
      try {
        transport.write(entry);
      } catch (e) {
        console.error(`Logger transport "${transport.name}" failed:`, e);
      }
    }
  }

  trace(message: string, data?: Record<string, unknown>): void {
    this.write('trace', message, data);
  }

  debug(message: string, data?: Record<string, unknown>): void {
    this.write('debug', message, data);
  }

  info(message: string, data?: Record<string, unknown>): void {
    this.write('info', message, data);
  }

  warn(message: string, data?: Record<string, unknown>): void {
    this.write('warn', message, data);
  }

  error(message: string, error?: Error | Record<string, unknown>, data?: Record<string, unknown>): void {
    if (error instanceof Error) {
      this.write('error', message, data, error);
    } else {
      this.write('error', message, error);
    }
  }

  fatal(message: string, error?: Error | Record<string, unknown>, data?: Record<string, unknown>): void {
    if (error instanceof Error) {
      this.write('fatal', message, data, error);
    } else {
      this.write('fatal', message, error);
    }
  }

  /** Log with a specific level */
  log(level: LogLevel, message: string, data?: Record<string, unknown>): void {
    this.write(level, message, data);
  }

  /** Time an operation */
  time<T>(label: string, fn: () => T): T {
    const start = performance.now();
    try {
      const result = fn();
      const duration = performance.now() - start;
      this.debug(`${label} completed`, { duration });
      return result;
    } catch (e) {
      const duration = performance.now() - start;
      this.error(`${label} failed`, e instanceof Error ? e : undefined, { duration });
      throw e;
    }
  }

  /** Time an async operation */
  async timeAsync<T>(label: string, fn: () => Promise<T>): Promise<T> {
    const start = performance.now();
    try {
      const result = await fn();
      const duration = performance.now() - start;
      this.debug(`${label} completed`, { duration });
      return result;
    } catch (e) {
      const duration = performance.now() - start;
      this.error(`${label} failed`, e instanceof Error ? e : undefined, { duration });
      throw e;
    }
  }

  /** Start a traced span */
  span(name: string, attributes?: Record<string, unknown>): Span {
    const span = contextStore.startSpan(name, attributes);
    this.debug(`Span started: ${name}`, attributes);
    
    const originalEnd = span.end;
    span.end = (endAttributes?: Record<string, unknown>) => {
      const duration = performance.now() - span.startTime;
      this.debug(`Span ended: ${name}`, { duration, ...endAttributes });
      originalEnd(endAttributes);
    };

    return span;
  }

  /** Start a new trace */
  startTrace(name: string): string {
    const traceId = contextStore.startTrace(name);
    this.info(`Trace started: ${name}`, { traceId });
    return traceId;
  }

  /** Set user context */
  setUser(userId: string): void {
    contextStore.setUser(userId);
    this.info('User context set', { userId });
  }

  /** Clear user context */
  clearUser(): void {
    this.info('User context cleared');
    contextStore.clearUser();
  }

  /** Flush all buffered logs */
  async flush(): Promise<void> {
    for (const transport of this.transports) {
      await transport.flush?.();
    }
  }

  /** Log a table (useful for data exploration) */
  table(data: unknown[], columns?: string[]): void {
    if (!this.shouldLog('debug')) return;
    console.table(data, columns);
  }

  /** Create a performance measure between two marks */
  measure(name: string, startMark: string, endMark?: string): void {
    if (typeof performance === 'undefined' || !performance.measure) return;
    
    try {
      const measure = endMark 
        ? performance.measure(name, startMark, endMark)
        : performance.measure(name, startMark);
      
      this.debug(`Performance: ${name}`, { duration: measure.duration });
    } catch {
      // Marks may not exist
    }
  }
}

/** Create root logger instance */
export const createLogger = (options?: ConstructorParameters<typeof Logger>[0]): Logger => {
  return new Logger(options);
};

