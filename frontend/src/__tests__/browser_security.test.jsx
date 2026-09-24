import { describe, it, expect } from 'vitest';

describe('Browser Security & Untrusted Input Sanitization', () => {
  it('safely escapes script tags in document text rendering', () => {
    const untrustedInput = '<script>alert("XSS")</script><b>Bold Text</b>';
    
    // Simulate safe HTML text escape helper
    const escapeHTML = (str) => {
      return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    };

    const sanitized = escapeHTML(untrustedInput);
    expect(sanitized).not.toContain('<script>');
    expect(sanitized).toContain('&lt;script&gt;');
  });

  it('rejects unsafe javascript: and data: URLs in navigation helpers', () => {
    const isSafeUrl = (url) => {
      if (!url || typeof url !== 'string') return false;
      const lower = url.trim().toLowerCase();
      if (lower.startsWith('javascript:') || lower.startsWith('data:') || lower.startsWith('vbscript:')) {
        return false;
      }
      return true;
    };

    expect(isSafeUrl('javascript:alert(1)')).toBe(false);
    expect(isSafeUrl('data:text/html;base64,PHNjcmlwdD4=')).toBe(false);
    expect(isSafeUrl('https://app.aegisai.enterprise/dashboard')).toBe(true);
    expect(isSafeUrl('/user/documents')).toBe(true);
  });
});
