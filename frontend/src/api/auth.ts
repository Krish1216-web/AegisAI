import { request } from './client';
import { Token, User } from './types';

export async function login(username: string, password: string): Promise<Token> {
  const body = new URLSearchParams();
  body.append('username', username);
  body.append('password', password);

  return request<Token>('/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: body.toString(),
  });
}

export async function register(username: string, email: string, password: string): Promise<User> {
  return request<User>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({
      username,
      email,
      password,
      role_name: 'User',
    }),
  });
}

export async function logout(): Promise<void> {
  return request<void>('/auth/logout', {
    method: 'POST',
  });
}

export async function getMe(): Promise<User> {
  return request<User>('/auth/me', {
    method: 'GET',
  });
}
