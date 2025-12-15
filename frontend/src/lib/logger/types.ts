/** Log severity levels */
export type LogLevel = 'trace' | 'debug' | 'info' | 'warn' | 'error' | 'fatal';

/** Numeric severity for filtering */
export const LOG_LEVELS: Record<LogLevel, number> = {
  trace: 10,
  debug: 20,
  info: 30,
  warn: 40,
  error: 50,
  fatal: 60,
} as const;

/** Structured log entry */
export interface LogEntry {
  level: LogLevel;
  timestamp: string;
  namespace: string;
  message: string;
  data?: Record<string, unknown>;
  context?: LogContext;
  error?: SerializedError;
  duration?: number;
  traceId?: string;
  spanId?: string;
}

/** Serialized error for structured output */
export interface SerializedError {
  name: string;
  message: string;
  stack?: string;
  cause?: SerializedError;
}

/** Context passed through log calls */
export interface LogContext {
  sessionId?: string;
  userId?: string;
  traceId?: string;
  spanId?: string;
  parentSpanId?: string;
  component?: string;
  action?: string;
  [key: string]: unknown;
}

/** HTTP request metadata for logging */
export interface HttpRequestLog {
  method: string;
  url: string;
  headers?: Record<string, string>;
  params?: Record<string, unknown>;
  body?: unknown;
  startTime: number;
}

/** HTTP response metadata for logging */
export interface HttpResponseLog {
  status: number;
  statusText: string;
  headers?: Record<string, string>;
  duration: number;
  size?: number;
}

/** Transport interface for extensible log destinations */
export interface LogTransport {
  name: string;
  write(entry: LogEntry): void | Promise<void>;
  flush?(): void | Promise<void>;
}

/** Logger configuration */
export interface LoggerConfig {
  level: LogLevel;
  namespace: string;
  transports: LogTransport[];
  context?: LogContext;
  enabled?: boolean;
}

/** Span for tracing operations */
export interface Span {
  id: string;
  name: string;
  startTime: number;
  parentId?: string;
  attributes: Record<string, unknown>;
  end(attributes?: Record<string, unknown>): void;
}

