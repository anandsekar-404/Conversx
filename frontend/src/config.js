/**
 * ConversX - Production Frontend Configuration
 * Resolves API Base URL from environment variables or falls back to relative origin.
 * Never hardcodes production hostnames or IPs into application code.
 */

export function getApiBaseUrl() {
  if (typeof window !== 'undefined' && window.ENV && window.ENV.VITE_API_BASE_URL) {
    return window.ENV.VITE_API_BASE_URL.replace(/\/+$/, '');
  }
  // Default to relative path or localhost during development
  return '';
}

export const API_BASE_URL = getApiBaseUrl();
