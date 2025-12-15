import type { LogContext, Span } from './types';

/** Generate a unique ID for tracing */
const generateId = (): string => {
  const timestamp = Date.now().toString(36);
  const random = Math.random().toString(36).slice(2, 10);
  return `${timestamp}-${random}`;
};

/** Session context store */
class ContextStore {
  private sessionId: string;
  private userId?: string;
  private activeSpans: Map<string, Span> = new Map();
  private currentTraceId?: string;
  private currentSpanId?: string;

  constructor() {
    this.sessionId = this.initSessionId();
  }

  private initSessionId(): string {
    const stored = sessionStorage.getItem('__lingua_session_id');
    if (stored) return stored;
    const id = generateId();
    sessionStorage.setItem('__lingua_session_id', id);
    return id;
  }

  get(): LogContext {
    return {
      sessionId: this.sessionId,
      userId: this.userId,
      traceId: this.currentTraceId,
      spanId: this.currentSpanId,
    };
  }

  setUser(userId: string): void {
    this.userId = userId;
  }

  clearUser(): void {
    this.userId = undefined;
  }

  /** Start a new trace (e.g., for a user action or page navigation) */
  startTrace(_name: string): string {
    this.currentTraceId = generateId();
    this.currentSpanId = undefined;
    return this.currentTraceId;
  }

  /** Create a span within the current trace */
  startSpan(name: string, attributes: Record<string, unknown> = {}): Span {
    const spanId = generateId();
    const parentSpanId = this.currentSpanId;
    
    if (!this.currentTraceId) {
      this.currentTraceId = generateId();
    }

    const span: Span = {
      id: spanId,
      name,
      startTime: performance.now(),
      parentId: parentSpanId,
      attributes,
      end: (endAttributes?: Record<string, unknown>) => {
        this.endSpan(spanId, endAttributes);
      },
    };

    this.activeSpans.set(spanId, span);
    this.currentSpanId = spanId;

    return span;
  }

  private endSpan(spanId: string, attributes?: Record<string, unknown>): void {
    const span = this.activeSpans.get(spanId);
    if (!span) return;

    if (attributes) {
      Object.assign(span.attributes, attributes);
    }

    this.activeSpans.delete(spanId);
    
    // Restore parent span as current
    if (span.parentId) {
      this.currentSpanId = span.parentId;
    } else {
      this.currentSpanId = undefined;
    }
  }

  getSpan(spanId: string): Span | undefined {
    return this.activeSpans.get(spanId);
  }

  getCurrentSpan(): Span | undefined {
    return this.currentSpanId ? this.activeSpans.get(this.currentSpanId) : undefined;
  }
}

export const contextStore = new ContextStore();

