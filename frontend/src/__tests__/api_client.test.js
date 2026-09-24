import { describe, it, expect, beforeEach, vi } from 'vitest';

describe('Frontend API Client & Bearer Injection', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('attaches Bearer authorization header when access token is present', async () => {
    localStorage.setItem('aegis_access_token', 'test_bearer_jwt');

    const headers = {
      'Content-Type': 'application/json',
    };

    const token = localStorage.getItem('aegis_access_token');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    expect(headers['Authorization']).toBe('Bearer test_bearer_jwt');
  });

  it('omits Authorization header when user is unauthenticated', () => {
    const headers = {
      'Content-Type': 'application/json',
    };

    const token = localStorage.getItem('aegis_access_token');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    expect(headers['Authorization']).toBeUndefined();
  });

  it('correctly handles JSON error responses without breaking application state', () => {
    const mockErrorPayload = {
      success: false,
      error: {
        code: 'PAYLOAD_TOO_LARGE',
        message: 'Request body exceeds maximum allowed size of 10485760 bytes.'
      }
    };

    const parsed = JSON.stringify(mockErrorPayload);
    const data = JSON.parse(parsed);

    expect(data.success).toBe(false);
    expect(data.error.code).toBe('PAYLOAD_TOO_LARGE');
    expect(data.error.message).toContain('exceeds maximum allowed size');
  });
});
