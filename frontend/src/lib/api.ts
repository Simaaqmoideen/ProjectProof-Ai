const API_BASE = '/api/v1';

export interface ApiError {
  code: string;
  message: string;
  details?: Array<{ field: string; issue: string }>;
  request_id?: string;
}

export class ApiException extends Error {
  code: string;
  status: number;
  details: Array<{ field: string; issue: string }>;
  requestId?: string;

  constructor(status: number, error: ApiError) {
    super(error.message || 'API request failed');
    this.name = 'ApiException';
    this.status = status;
    this.code = error.code || 'unknown_error';
    this.details = error.details || [];
    this.requestId = error.request_id;
  }
}

let isRefreshing = false;
let refreshSubscribers: Array<(token: string) => void> = [];

function onRefreshed(token: string) {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
}

export async function apiRequest<T = any>(
  endpoint: string,
  options: RequestInit = {},
  retry = true
): Promise<T> {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  const defaultHeaders: Record<string, string> = {
    'Accept': 'application/json',
  };

  // Only set Content-Type to application/json if not FormData
  if (!(options.body instanceof FormData)) {
    defaultHeaders['Content-Type'] = 'application/json';
  }

  // Retrieve access token from localStorage
  const token = localStorage.getItem('access_token');
  if (token) {
    defaultHeaders['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    credentials: 'include', // Include refresh cookie
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  });

  if (response.status === 401 && retry && !endpoint.includes('/auth/login') && !endpoint.includes('/auth/refresh')) {
    if (!isRefreshing) {
      isRefreshing = true;
      try {
        const refreshRes = await fetch(`${API_BASE}/auth/refresh`, {
          method: 'POST',
          credentials: 'include',
        });
        if (refreshRes.ok) {
          const data = await refreshRes.json();
          if (data.access_token) {
            localStorage.setItem('access_token', data.access_token);
            onRefreshed(data.access_token);
            isRefreshing = false;
            return apiRequest<T>(endpoint, options, false);
          }
        }
      } catch (err) {
        // Refresh failed
      }
      isRefreshing = false;
      localStorage.removeItem('access_token');
      localStorage.removeItem('current_user');
      window.dispatchEvent(new Event('auth:logout'));
    } else {
      // Wait for current refresh to complete
      return new Promise<T>((resolve, reject) => {
        refreshSubscribers.push(() => {
          apiRequest<T>(endpoint, options, false).then(resolve).catch(reject);
        });
      });
    }
  }

  if (!response.ok) {
    let errorData: ApiError;
    try {
      const json = await response.json();
      errorData = json.error || { code: 'error', message: json.detail || 'Request failed' };
    } catch {
      errorData = { code: 'error', message: response.statusText || 'Network response error' };
    }
    throw new ApiException(response.status, errorData);
  }

  // Check if response has content
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return (await response.json()) as T;
  }
  return {} as T;
}
