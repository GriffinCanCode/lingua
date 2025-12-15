import type { LogEntry, LogLevel, LogTransport } from './types';

/** ANSI-style colors for browser console */
const COLORS: Record<LogLevel, { badge: string; text: string }> = {
  trace: { badge: '#6b7280', text: '#9ca3af' },
  debug: { badge: '#3b82f6', text: '#60a5fa' },
  info: { badge: '#10b981', text: '#34d399' },
  warn: { badge: '#f59e0b', text: '#fbbf24' },
  error: { badge: '#ef4444', text: '#f87171' },
  fatal: { badge: '#dc2626', text: '#fca5a5' },
};

const LEVEL_ICONS: Record<LogLevel, string> = {
  trace: '⋯',
  debug: '⚙',
  info: 'ℹ',
  warn: '⚠',
  error: '✖',
  fatal: '💥',
};

/** Format duration in human-readable form */
const formatDuration = (ms: number): string => {
  if (ms < 1) return `${(ms * 1000).toFixed(0)}μs`;
  if (ms < 1000) return `${ms.toFixed(1)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
};

/** Pretty console transport with colors and grouping */
export class ConsoleTransport implements LogTransport {
  name = 'console';
  private collapsed: boolean;

  constructor(options: { collapsed?: boolean } = {}) {
    this.collapsed = options.collapsed ?? true;
  }

  write(entry: LogEntry): void {
    const { level, namespace, message, data, error, duration, context } = entry;
    const colors = COLORS[level];
    const icon = LEVEL_ICONS[level];

    // Build styled prefix
    const badgeStyle = `background:${colors.badge};color:white;padding:2px 6px;border-radius:3px;font-weight:600;`;
    const nsStyle = `color:${colors.text};font-weight:500;`;
    const msgStyle = `color:#e5e7eb;`;
    const dimStyle = `color:#6b7280;font-size:11px;`;

    // Build log line parts
    const parts: string[] = [];
    const styles: string[] = [];

    // Level badge
    parts.push(`%c${icon} ${level.toUpperCase()}`);
    styles.push(badgeStyle);

    // Namespace
    parts.push(`%c[${namespace}]`);
    styles.push(nsStyle);

    // Message
    parts.push(`%c${message}`);
    styles.push(msgStyle);

    // Duration if present
    if (duration !== undefined) {
      parts.push(`%c(${formatDuration(duration)})`);
      styles.push(dimStyle);
    }

    const hasDetails = data || error || (context && Object.keys(context).length > 0);
    const logFn = this.getLogFn(level);

    if (hasDetails) {
      const groupFn = this.collapsed ? console.groupCollapsed : console.group;
      groupFn.call(console, parts.join(' '), ...styles);

      if (context && Object.keys(context).length > 0) {
        console.log('%c◉ Context', 'color:#8b5cf6;font-weight:600;', context);
      }
      if (data) {
        console.log('%c◉ Data', 'color:#06b6d4;font-weight:600;', data);
      }
      if (error) {
        console.log('%c◉ Error', 'color:#ef4444;font-weight:600;');
        console.error(this.reconstructError(error));
      }

      console.groupEnd();
    } else {
      logFn.call(console, parts.join(' '), ...styles);
    }
  }

  private getLogFn(level: LogLevel): typeof console.log {
    switch (level) {
      case 'trace':
      case 'debug':
        return console.debug;
      case 'info':
        return console.info;
      case 'warn':
        return console.warn;
      case 'error':
      case 'fatal':
        return console.error;
    }
  }

  private reconstructError(serialized: { name: string; message: string; stack?: string }): Error {
    const err = new Error(serialized.message);
    err.name = serialized.name;
    if (serialized.stack) err.stack = serialized.stack;
    return err;
  }
}

/** JSON transport for structured logging (production/debugging) */
export class JsonTransport implements LogTransport {
  name = 'json';
  private pretty: boolean;

  constructor(options: { pretty?: boolean } = {}) {
    this.pretty = options.pretty ?? false;
  }

  write(entry: LogEntry): void {
    const output = this.pretty 
      ? JSON.stringify(entry, null, 2) 
      : JSON.stringify(entry);
    
    const logFn = entry.level === 'error' || entry.level === 'fatal' 
      ? console.error 
      : console.log;
    
    logFn(output);
  }
}

/** Buffer transport for collecting logs (useful for sending batches) */
export class BufferTransport implements LogTransport {
  name = 'buffer';
  private buffer: LogEntry[] = [];
  private maxSize: number;
  private onFlush?: (entries: LogEntry[]) => void | Promise<void>;

  constructor(options: { maxSize?: number; onFlush?: (entries: LogEntry[]) => void | Promise<void> } = {}) {
    this.maxSize = options.maxSize ?? 100;
    this.onFlush = options.onFlush;
  }

  write(entry: LogEntry): void {
    this.buffer.push(entry);
    if (this.buffer.length >= this.maxSize) {
      this.flush();
    }
  }

  async flush(): Promise<void> {
    if (this.buffer.length === 0) return;
    const entries = [...this.buffer];
    this.buffer = [];
    await this.onFlush?.(entries);
  }

  getBuffer(): LogEntry[] {
    return [...this.buffer];
  }

  clear(): void {
    this.buffer = [];
  }
}

/** Performance marks transport for browser DevTools Performance tab */
export class PerformanceTransport implements LogTransport {
  name = 'performance';

  write(entry: LogEntry): void {
    if (typeof performance === 'undefined' || !performance.mark) return;

    const markName = `[${entry.level}] ${entry.namespace}: ${entry.message}`;
    
    try {
      performance.mark(markName, {
        detail: {
          level: entry.level,
          namespace: entry.namespace,
          data: entry.data,
          traceId: entry.traceId,
        },
      });
    } catch {
      // Older browsers may not support detail
      performance.mark(markName);
    }
  }
}

