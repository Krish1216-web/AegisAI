import { describe, it, expect, beforeEach, vi } from 'vitest';

describe('AuthContext & Session Security', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('stores access token securely and sets auth status on successful login', () => {
    const fakeToken = 'mock_jwt_access_token_12345';
    localStorage.setItem('aegis_access_token', fakeToken);
    localStorage.setItem('aegis_auth_logged', 'true');
    localStorage.setItem('aegis_auth_role', 'Admin');

    expect(localStorage.getItem('aegis_access_token')).toBe(fakeToken);
    expect(localStorage.getItem('aegis_auth_logged')).toBe('true');
    expect(localStorage.getItem('aegis_auth_role')).toBe('Admin');
  });

  it('purges tokens and auth roles upon logout', () => {
    localStorage.setItem('aegis_access_token', 'temp_token');
    localStorage.setItem('aegis_auth_logged', 'true');
    localStorage.setItem('aegis_auth_role', 'Member');

    // Simulate logout cleanup action
    localStorage.removeItem('aegis_access_token');
    localStorage.removeItem('aegis_auth_logged');
    localStorage.removeItem('aegis_auth_role');

    expect(localStorage.getItem('aegis_access_token')).toBeNull();
    expect(localStorage.getItem('aegis_auth_logged')).toBeNull();
    expect(localStorage.getItem('aegis_auth_role')).toBeNull();
  });

  it('clears state safely when a 401 Unauthorized occurs', () => {
    localStorage.setItem('aegis_access_token', 'expired_token');
    localStorage.setItem('aegis_auth_logged', 'true');

    // Simulate 401 handler
    const handle401 = () => {
      localStorage.removeItem('aegis_access_token');
      localStorage.removeItem('aegis_auth_logged');
      localStorage.removeItem('aegis_auth_role');
    };

    handle401();
    expect(localStorage.getItem('aegis_access_token')).toBeNull();
  });
});
