/**
 * ConversX Personal AI Coach Service (Client-Side).
 * 
 * Secure communications with /api/v1/ai-coach backend endpoints.
 * SECURITY GUARANTEES:
 * - NEVER persists raw API keys to localStorage, sessionStorage, IndexedDB, or cookies.
 * - All keys are encrypted at rest on the backend.
 * - Handles connection testing, status queries, preferred provider selection, and coaching requests.
 */

import { API_BASE_URL } from '../config.js';

export class AICoachService {
  constructor() {
    this.status = {
      openai: { connected: false, status: 'not_connected', masked_key: '', last_tested_at: null },
      gemini: { connected: false, status: 'not_connected', masked_key: '', last_tested_at: null },
      preferred_provider: 'openai'
    };
    this.isLoaded = false;
  }

  /**
   * Fetch current connection status from backend without exposing secrets.
   */
  async fetchStatus() {
    try {
      const token = this._getAuthToken();
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch(`${API_BASE_URL}/api/v1/ai-coach/status`, {
        method: 'GET',
        headers
      });

      if (res.ok) {
        const data = await res.json();
        this.status = data;
        this.isLoaded = true;
        return this.status;
      }
    } catch (e) {
      console.warn('Could not fetch AI coach status:', e.message);
    }

    // Default safe fallback if offline / unconfigured
    return this.status;
  }

  /**
   * Save an API key securely to the backend. Key is encrypted at rest and never cached in JS storage.
   */
  async connectProvider(provider, apiKey) {
    if (!apiKey || apiKey.trim().length < 8) {
      throw new Error('Please enter a valid API key.');
    }

    const token = this._getAuthToken();
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(`${API_BASE_URL}/api/v1/ai-coach/connect`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        provider: provider.toLowerCase(),
        api_key: apiKey.trim()
      })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to connect provider' }));
      throw new Error(err.detail || 'Failed to connect provider.');
    }

    const data = await res.json();
    await this.fetchStatus();
    return data;
  }

  /**
   * Test a provider connection. Returns sanitized status:
   * 'connected' | 'invalid' | 'rate_limited' | 'unavailable'
   */
  async testConnection(provider, optionalRawKey = null) {
    const token = this._getAuthToken();
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const body = { provider: provider.toLowerCase() };
    if (optionalRawKey) {
      body.api_key = optionalRawKey.trim();
    }

    const res = await fetch(`${API_BASE_URL}/api/v1/ai-coach/test`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body)
    });

    if (!res.ok) {
      return {
        status: 'unavailable',
        provider,
        message: 'The AI provider is currently unavailable.'
      };
    }

    const result = await res.json();
    await this.fetchStatus();
    return result;
  }

  /**
   * Permanently delete stored credentials for a provider.
   */
  async removeConnection(provider) {
    const token = this._getAuthToken();
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(`${API_BASE_URL}/api/v1/ai-coach/connection/${provider.toLowerCase()}`, {
      method: 'DELETE',
      headers
    });

    if (!res.ok) {
      throw new Error(`Failed to remove ${provider} connection.`);
    }

    await this.fetchStatus();
    return true;
  }

  /**
   * Set user preferred AI coach provider ('openai' or 'gemini').
   */
  async setPreferredProvider(provider) {
    const token = this._getAuthToken();
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(`${API_BASE_URL}/api/v1/ai-coach/preferred`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ provider: provider.toLowerCase() })
    });

    if (res.ok) {
      this.status.preferred_provider = provider.toLowerCase();
      return true;
    }
    return false;
  }

  /**
   * Request personalized AI coaching for a voice response.
   * If AI is not connected or provider fails, returns graceful fallback.
   */
  async requestCoaching({ transcript, scenario, communicationMetrics, speakingMetrics, providerOverride = null }) {
    if (!transcript || !transcript.trim()) {
      return null;
    }

    const token = this._getAuthToken();
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/ai-coach/coach`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          transcript,
          scenario,
          communication_metrics: communicationMetrics,
          speaking_metrics: speakingMetrics || null,
          provider: providerOverride
        })
      });

      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn('AI coaching request failed, continuing with ConversX core analysis:', e.message);
    }

    // Client-side fallback if backend is unreachable
    return this._clientFallbackCoaching(transcript, scenario, communicationMetrics);
  }

  /**
   * Client-side fallback coaching when backend / provider is offline.
   */
  _clientFallbackCoaching(transcript, scenario, metrics) {
    const clarity = (metrics && metrics.clarity) || 80;
    const filler = (metrics && metrics.filler_control) || 80;
    const mode = (typeof scenario === 'object' && scenario?.mode ? scenario.mode : typeof scenario === 'string' ? scenario : 'casual').toLowerCase();

    const strengths = [
        'Directly addressed the prompt with clear conceptual progression.',
        'Assertive delivery tone and coherent sentence structure.'
    ];
    if (clarity >= 85) strengths.push('Sharp syntactic articulation with precise vocabulary.');

    const improvements = [];
    if (filler < 80) improvements.push('Verbal hesitation detected; convert vocal fillers into 0.8s intentional silence.');
    improvements.push('Vary lexical emphasis when transitioning between core arguments.');

    const result = {
      status: 'fallback',
      is_ai_generated: false,
      provider: 'conversx_core',
      strengths,
      improvements,
      why_it_matters: 'Executive listeners equate intentional pauses with authority. Silent composure consistently outperforms speculative filler words.',
      next_time_actions: [
        'Pause and inhale silently rather than vocalizing hesitation.',
        'Lead with the bottom-line recommendation in your first two sentences.'
      ],
      stronger_phrasing: 'In summary, our key milestone is protected, and our contingency protocols ensure zero disruption.'
    };

    if (mode === 'interview') {
      result.interview_star = {
        situation: 'Identified the operational landscape and leadership challenge.',
        task: 'Defined measurable delivery targets under constraints.',
        action: 'Restructured dependencies to buffer risk.',
        result: 'Achieved on-time SLA with zero capital overrun.',
        likely_followup: 'How did you handle pushback from cross-functional stakeholders on that timeline?'
      };
    } else if (mode === 'presentation') {
      result.presentation_structure = {
        opening: 'Compelling bottom-line opening hook.',
        organization: 'Logical 3-part progression.',
        transitions: 'Explicit signposts between sections.',
        conclusion: 'Actionable executive call to action.'
      };
    }

    return result;
  }

  _getAuthToken() {
    if (typeof window !== 'undefined' && window.__conversx_jwt_token) {
      return window.__conversx_jwt_token;
    }
    if (typeof localStorage !== 'undefined') {
      return localStorage.getItem('conversx_token') || null;
    }
    return null;
  }
}

export const aiCoachService = new AICoachService();
