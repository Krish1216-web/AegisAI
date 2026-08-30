export const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '') + '/api/v1';

let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

function subscribeTokenRefresh(cb: (token: string) => void) {
  refreshSubscribers.push(cb);
}

function onRefreshed(token: string) {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
}

export class ApiRequestError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
    this.name = 'ApiRequestError';
  }
}

interface RequestOptions extends RequestInit {
  timeout?: number;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const { timeout = 30000, ...initOptions } = options;

  const headers = new Headers(initOptions.headers || {});
  if (!headers.has('Content-Type') && !(initOptions.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const token = localStorage.getItem('aegis_access_token');
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);

  const finalOptions: RequestInit = {
    ...initOptions,
    headers,
    signal: controller.signal,
  };

  try {
    const response = await fetch(url, finalOptions);
    clearTimeout(id);

    if (response.status === 401 && !path.includes('/auth/login') && !path.includes('/auth/refresh')) {
      // Handle automatic token refresh rotation (RTR)
      if (!isRefreshing) {
        isRefreshing = true;
        try {
          const refreshRes = await fetch(`${API_BASE_URL}/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
          });

          if (refreshRes.ok) {
            const data = await refreshRes.json();
            localStorage.setItem('aegis_access_token', data.access_token);
            isRefreshing = false;
            onRefreshed(data.access_token);
          } else {
            isRefreshing = false;
            localStorage.removeItem('aegis_access_token');
            localStorage.removeItem('aegis_auth_logged');
            localStorage.removeItem('aegis_auth_role');
            window.location.hash = '/login';
            throw new ApiRequestError(401, 'UNAUTHORIZED', 'Session expired. Please log in.');
          }
        } catch (refreshErr) {
          isRefreshing = false;
          throw refreshErr;
        }
      }

      return new Promise<T>((resolve, reject) => {
        subscribeTokenRefresh((newToken) => {
          headers.set('Authorization', `Bearer ${newToken}`);
          fetch(url, { ...finalOptions, headers })
            .then(async (res) => {
              if (res.ok) {
                resolve((await res.json()) as T);
              } else {
                reject(await parseError(res));
              }
            })
            .catch(reject);
        });
      });
    }

    if (!response.ok) {
      throw await parseError(response);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return (await response.json()) as T;
  } catch (error: any) {
    clearTimeout(id);
    if (error.name === 'AbortError') {
      throw new ApiRequestError(408, 'TIMEOUT', 'Request timed out.');
    }
    throw error;
  }
}

async function parseError(response: Response): Promise<ApiRequestError> {
  try {
    const errorData = await response.json();
    const code = errorData.error?.code || 'UNKNOWN_ERROR';
    const message = errorData.error?.message || response.statusText || 'An unexpected error occurred.';
    return new ApiRequestError(response.status, code, message);
  } catch {
    return new ApiRequestError(
      response.status,
      'SERVER_ERROR',
      `Server returned ${response.status}: ${response.statusText || 'Internal Server Error'}`
    );
  }
}
