/**
 * Native Fetch-based API client for FSP IT-Talent Platform
 * Follows Ponytail principle: native fetch, zero external dependencies.
 * Features: Automatic JWT Bearer injection, singleflight token refresh on 401, single retry.
 */

const BASE_URL = '/api/v1';

export interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
  _retry?: boolean;
}

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

interface StoredTokens {
  accessToken: string | null;
  refreshToken: string | null;
}

function getStoredTokens(): StoredTokens {
  try {
    if (typeof localStorage !== 'undefined') {
      const raw = localStorage.getItem('fsp_auth_storage');
      if (raw) {
        const parsed = JSON.parse(raw);
        const state = parsed.state || parsed;
        return {
          accessToken: state?.accessToken || null,
          refreshToken: state?.refreshToken || null,
        };
      }
    }
  } catch {
    // Ignore storage parse error
  }
  return { accessToken: null, refreshToken: null };
}

function getAuthToken(): string | null {
  return getStoredTokens().accessToken;
}

function updateStoredTokens(newAccessToken: string, newRefreshToken?: string): void {
  try {
    if (typeof localStorage !== 'undefined') {
      const raw = localStorage.getItem('fsp_auth_storage');
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed.state) {
          parsed.state.accessToken = newAccessToken;
          if (newRefreshToken) parsed.state.refreshToken = newRefreshToken;
        } else {
          parsed.accessToken = newAccessToken;
          if (newRefreshToken) parsed.refreshToken = newRefreshToken;
        }
        localStorage.setItem('fsp_auth_storage', JSON.stringify(parsed));
      }
      if (typeof window !== 'undefined' && typeof window.dispatchEvent === 'function') {
        window.dispatchEvent(new Event('storage'));
      }
    }
  } catch {
    // Ignore storage errors in non-browser envs
  }
}

function clearAuthStorage(): void {
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem('fsp_auth_storage');
      if (typeof window !== 'undefined' && typeof window.dispatchEvent === 'function') {
        window.dispatchEvent(new Event('storage'));
      }
    }
  } catch {
    // Ignore storage errors in non-browser envs
  }
}

// Singleflight mutex promise to prevent concurrent duplicate refresh requests
let refreshInProgressPromise: Promise<string | null> | null = null;

async function executeTokenRefresh(): Promise<string | null> {
  const { refreshToken } = getStoredTokens();
  if (!refreshToken) {
    clearAuthStorage();
    return null;
  }

  try {
    const res = await fetch(`${BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!res.ok) {
      clearAuthStorage();
      return null;
    }

    const data = await res.json();
    const newAccessToken = data.access_token;
    const newRefreshToken = data.refresh_token || refreshToken;
    if (newAccessToken) {
      updateStoredTokens(newAccessToken, newRefreshToken);
      return newAccessToken;
    }
    clearAuthStorage();
    return null;
  } catch {
    clearAuthStorage();
    return null;
  }
}

async function requestRaw(endpoint: string, options: RequestOptions = {}): Promise<Response> {
  const { params, headers = {}, _retry = false, ...rest } = options;
  let url: string;
  if (endpoint.startsWith('http')) {
    url = endpoint;
  } else if (endpoint.startsWith(BASE_URL)) {
    url = endpoint;
  } else {
    url = `${BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
  }

  if (params) {
    const query = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined) query.append(k, String(v));
    }
    const qs = query.toString();
    if (qs) url += `${url.includes('?') ? '&' : '?'}${qs}`;
  }

  const { accessToken: initialAccessToken } = getStoredTokens();
  const isFormData = typeof FormData !== 'undefined' && rest.body instanceof FormData;
  const requestHeaders: Record<string, string> = {
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...(headers as Record<string, string>),
  };

  if (initialAccessToken && !requestHeaders['Authorization']) {
    requestHeaders['Authorization'] = `Bearer ${initialAccessToken}`;
  }

  try {
    const response = await fetch(url, {
      ...rest,
      headers: requestHeaders,
    });

    if (!response.ok) {
      const isAuthEndpoint =
        endpoint.includes('/auth/login') ||
        endpoint.includes('/auth/refresh');

      // 401 Unauthorized handling: attempt refresh and retry once
      if (response.status === 401 && !_retry && !isAuthEndpoint) {
        const { accessToken: currentAccessToken, refreshToken } = getStoredTokens();

        // If another concurrent request already refreshed the token in the meantime, retry immediately
        if (currentAccessToken && initialAccessToken && currentAccessToken !== initialAccessToken) {
          return await requestRaw(endpoint, {
            ...options,
            _retry: true,
            headers: {
              ...(headers as Record<string, string>),
              Authorization: `Bearer ${currentAccessToken}`,
            },
          });
        }

        if (refreshToken) {
          if (!refreshInProgressPromise) {
            refreshInProgressPromise = executeTokenRefresh().finally(() => {
              refreshInProgressPromise = null;
            });
          }

          const refreshedToken = await refreshInProgressPromise;
          if (refreshedToken) {
            return await requestRaw(endpoint, {
              ...options,
              _retry: true,
              headers: {
                ...(headers as Record<string, string>),
                Authorization: `Bearer ${refreshedToken}`,
              },
            });
          }
        }
      }

      // If refresh failed or not applicable, ensure storage is cleaned up on 401
      if (response.status === 401) {
        clearAuthStorage();
      }

      let errData: unknown;
      try {
        errData = await response.json();
      } catch {
        errData = await response.text();
      }
      throw new ApiError(`HTTP ${response.status}: ${response.statusText}`, response.status, errData);
    }

    return response;
  } catch (err: unknown) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(err instanceof Error ? err.message : 'Network request failed', 0, err);
  }
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const response = await requestRaw(endpoint, options);
  if (response.status === 204) {
    return {} as T;
  }
  return (await response.json()) as T;
}

export async function downloadBlob(
  endpoint: string,
  defaultFilename: string = 'document.pdf'
): Promise<void> {
  const response = await requestRaw(endpoint, { method: 'GET' });
  const blob = await response.blob();

  let resolvedFilename = defaultFilename;
  const disposition = response.headers?.get ? response.headers.get('content-disposition') : null;
  if (disposition && defaultFilename === 'document.pdf') {
    const parts = disposition.split(';');
    for (const part of parts) {
      const trimmed = part.trim();
      if (trimmed.toLowerCase().startsWith('filename=')) {
        let rawName = trimmed.slice(9).trim();
        if ((rawName.startsWith('"') && rawName.endsWith('"')) || (rawName.startsWith("'") && rawName.endsWith("'"))) {
          rawName = rawName.slice(1, -1);
        }
        if (rawName) {
          resolvedFilename = rawName;
        }
        break;
      }
    }
  }

  const createUrl =
    (typeof window !== 'undefined' && window.URL?.createObjectURL) ||
    (typeof URL !== 'undefined' && typeof URL.createObjectURL === 'function' ? URL.createObjectURL : null);
  const revokeUrl =
    (typeof window !== 'undefined' && window.URL?.revokeObjectURL) ||
    (typeof URL !== 'undefined' && typeof URL.revokeObjectURL === 'function' ? URL.revokeObjectURL : null);

  const blobUrl = createUrl ? createUrl(blob) : null;

  try {
    if (typeof document !== 'undefined') {
      const link = document.createElement('a');
      link.style.display = 'none';
      if (blobUrl) {
        link.href = blobUrl;
      }
      link.download = resolvedFilename;
      document.body.appendChild(link);
      if (typeof link.click === 'function') {
        link.click();
      }
      document.body.removeChild(link);
    }
  } finally {
    if (blobUrl && revokeUrl) {
      setTimeout(() => {
        try {
          revokeUrl(blobUrl);
        } catch {
          // ignore cleanup errors in test environments
        }
      }, 100);
    }
  }
}

function serializeBody(body: unknown): BodyInit | undefined {
  if (body === undefined) return undefined;
  if (typeof FormData !== 'undefined' && body instanceof FormData) return body;
  return JSON.stringify(body);
}

export const api = {
  get: <T>(url: string, options?: RequestOptions) => request<T>(url, { ...options, method: 'GET' }),
  post: <T>(url: string, body?: unknown, options?: RequestOptions) =>
    request<T>(url, { ...options, method: 'POST', body: serializeBody(body) }),
  put: <T>(url: string, body?: unknown, options?: RequestOptions) =>
    request<T>(url, { ...options, method: 'PUT', body: serializeBody(body) }),
  patch: <T>(url: string, body?: unknown, options?: RequestOptions) =>
    request<T>(url, { ...options, method: 'PATCH', body: serializeBody(body) }),
  delete: <T>(url: string, options?: RequestOptions) => request<T>(url, { ...options, method: 'DELETE' }),
  downloadBlob: (endpoint: string, defaultFilename: string = 'document.pdf') =>
    downloadBlob(endpoint, defaultFilename),
};
