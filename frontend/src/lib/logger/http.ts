import type { AxiosInstance, AxiosError, InternalAxiosRequestConfig, AxiosResponse } from 'axios';
import type { Logger } from './core';
import { contextStore } from './context';

/** Extended config with timing metadata */
interface TimedAxiosConfig extends InternalAxiosRequestConfig {
  __startTime?: number;
  __spanId?: string;
}

/** Format bytes to human-readable size */
const formatBytes = (bytes: number): string => {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)}MB`;
};

/** Redact sensitive headers */
const SENSITIVE_HEADERS = ['authorization', 'cookie', 'x-api-key'];
const redactHeaders = (headers: Record<string, string>): Record<string, string> => {
  const redacted: Record<string, string> = {};
  for (const [key, value] of Object.entries(headers)) {
    redacted[key] = SENSITIVE_HEADERS.includes(key.toLowerCase()) 
      ? '[REDACTED]' 
      : value;
  }
  return redacted;
};

/** Truncate large payloads for logging */
const truncatePayload = (payload: unknown, maxLength = 1000): unknown => {
  if (!payload) return payload;
  const str = typeof payload === 'string' ? payload : JSON.stringify(payload);
  if (str.length <= maxLength) return payload;
  return `${str.slice(0, maxLength)}... [truncated ${str.length - maxLength} chars]`;
};

/** Setup HTTP logging interceptors for Axios */
export const setupHttpLogging = (axios: AxiosInstance, logger: Logger): void => {
  const httpLogger = logger.scope('http');

  // Request interceptor
  axios.interceptors.request.use(
    (config: TimedAxiosConfig) => {
      config.__startTime = performance.now();
      
      // Start a span for this request
      const span = contextStore.startSpan(`HTTP ${config.method?.toUpperCase()} ${config.url}`);
      config.__spanId = span.id;

      // Add trace headers for distributed tracing
      const ctx = contextStore.get();
      if (ctx.traceId) {
        config.headers.set('X-Trace-ID', ctx.traceId);
      }
      if (ctx.spanId) {
        config.headers.set('X-Span-ID', ctx.spanId);
      }

      httpLogger.debug(`→ ${config.method?.toUpperCase()} ${config.url}`, {
        method: config.method?.toUpperCase(),
        url: config.url,
        params: config.params,
        headers: config.headers ? redactHeaders(config.headers as unknown as Record<string, string>) : undefined,
        body: config.data ? truncatePayload(config.data) : undefined,
      });

      return config;
    },
    (error: AxiosError) => {
      httpLogger.error('Request setup failed', error);
      return Promise.reject(error);
    }
  );

  // Response interceptor
  axios.interceptors.response.use(
    (response: AxiosResponse) => {
      const config = response.config as TimedAxiosConfig;
      const duration = config.__startTime ? performance.now() - config.__startTime : 0;
      
      // End the span
      if (config.__spanId) {
        const span = contextStore.getSpan(config.__spanId);
        span?.end({ status: response.status });
      }

      const size = response.headers['content-length'] 
        ? parseInt(response.headers['content-length'], 10)
        : JSON.stringify(response.data).length;

      const statusEmoji = response.status < 300 ? '✓' : '⚠';
      
      httpLogger.info(`← ${statusEmoji} ${response.status} ${config.method?.toUpperCase()} ${config.url}`, {
        method: config.method?.toUpperCase(),
        url: config.url,
        status: response.status,
        statusText: response.statusText,
        duration,
        size: formatBytes(size),
        data: truncatePayload(response.data),
      });

      return response;
    },
    (error: AxiosError) => {
      const config = error.config as TimedAxiosConfig | undefined;
      const duration = config?.__startTime ? performance.now() - config.__startTime : 0;

      // End the span with error
      if (config?.__spanId) {
        const span = contextStore.getSpan(config.__spanId);
        span?.end({ status: error.response?.status ?? 0, error: true });
      }

      if (error.response) {
        // Server responded with error status
        httpLogger.error(`← ✖ ${error.response.status} ${config?.method?.toUpperCase()} ${config?.url}`, error, {
          method: config?.method?.toUpperCase(),
          url: config?.url,
          status: error.response.status,
          statusText: error.response.statusText,
          duration,
          responseData: truncatePayload(error.response.data),
        });
      } else if (error.request) {
        // Request made but no response
        httpLogger.error(`← ✖ NO RESPONSE ${config?.method?.toUpperCase()} ${config?.url}`, error, {
          method: config?.method?.toUpperCase(),
          url: config?.url,
          duration,
          message: error.message,
        });
      } else {
        // Request setup error
        httpLogger.error('Request configuration error', error);
      }

      return Promise.reject(error);
    }
  );
};

/** Create HTTP timing decorator for manual fetch calls */
export const createHttpTimer = (logger: Logger) => {
  const httpLogger = logger.scope('http');

  return async <T>(
    label: string,
    fetchFn: () => Promise<Response>
  ): Promise<T> => {
    const start = performance.now();
    const span = contextStore.startSpan(`HTTP ${label}`);

    try {
      const response = await fetchFn();
      const duration = performance.now() - start;
      
      if (!response.ok) {
        httpLogger.warn(`← ⚠ ${response.status} ${label}`, {
          status: response.status,
          statusText: response.statusText,
          duration,
        });
      } else {
        httpLogger.debug(`← ✓ ${response.status} ${label}`, {
          status: response.status,
          duration,
        });
      }

      span.end({ status: response.status });
      return response.json() as Promise<T>;
    } catch (e) {
      const duration = performance.now() - start;
      httpLogger.error(`← ✖ ${label}`, e instanceof Error ? e : undefined, { duration });
      span.end({ error: true });
      throw e;
    }
  };
};

