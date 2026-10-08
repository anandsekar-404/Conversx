/**
 * Firebase Client Integration & Moderation Rule Service.
 * Conforms to Master Prompt Section 2, Section 8, Section 9, and Section 10.
 *
 * Firebase Firestore is the centralized source of truth for:
 * - badWords
 * - harassmentPatterns
 * - categories
 * - severityLevels
 * - improvementSuggestions
 *
 * Implements graceful offline/fallback handling so the client never crashes.
 */

// Default configuration placeholder - users supply their Firebase Web config via env or config object
export const defaultFirebaseConfig = {
  apiKey: typeof window !== 'undefined' && window.__FIREBASE_CONFIG__?.apiKey || 'AIzaSy_MOCK_KEY_FOR_DEV_RULE_CACHING',
  authDomain: typeof window !== 'undefined' && window.__FIREBASE_CONFIG__?.authDomain || 'conversx-moderation.firebaseapp.com',
  projectId: typeof window !== 'undefined' && window.__FIREBASE_CONFIG__?.projectId || 'conversx-moderation',
  storageBucket: typeof window !== 'undefined' && window.__FIREBASE_CONFIG__?.storageBucket || 'conversx-moderation.appspot.com',
  messagingSenderId: typeof window !== 'undefined' && window.__FIREBASE_CONFIG__?.messagingSenderId || '1234567890',
  appId: typeof window !== 'undefined' && window.__FIREBASE_CONFIG__?.appId || '1:1234567890:web:abcdef'
};

class FirebaseRuleService {
  constructor() {
    this.initialized = false;
    this.firestore = null;
    this.auth = null;
    this.useBackendApi = true; // Default to backend API proxy which manages Firestore / caching
  }

  async init(customConfig = null) {
    if (this.initialized) return;

    // Check if Firebase SDK is available via CDN or bundler
    if (typeof window !== 'undefined' && window.firebase) {
      try {
        const config = customConfig || defaultFirebaseConfig;
        if (!window.firebase.apps.length) {
          window.firebase.initializeApp(config);
        }
        this.firestore = window.firebase.firestore();
        this.auth = window.firebase.auth();
        this.initialized = true;
        this.useBackendApi = false;
        console.log('[FirebaseService] Direct Firestore initialized successfully.');
      } catch (err) {
        console.warn('[FirebaseService] Firestore direct init failed; falling back to Backend API:', err.message);
        this.useBackendApi = true;
      }
    } else {
      // Use Backend API proxy for rule operations
      this.useBackendApi = true;
    }
  }

  /**
   * Fetch all active rules from Firestore or Backend API proxy.
   */
  async fetchAllRules() {
    if (this.useBackendApi) {
      try {
        const res = await fetch('/api/v1/moderation/rules');
        if (res.ok) {
          return await res.json();
        }
      } catch (e) {
        console.warn('[FirebaseService] Backend API rules fetch failed:', e);
      }
      return null;
    }

    if (!this.firestore) return null;

    try {
      const [badWordsSnap, patternsSnap, categoriesSnap, severitySnap, suggestionsSnap] = await Promise.all([
        this.firestore.collection('badWords').where('active', '==', true).get(),
        this.firestore.collection('harassmentPatterns').where('active', '==', true).get(),
        this.firestore.collection('categories').get(),
        this.firestore.collection('severityLevels').orderBy('level', 'asc').get(),
        this.firestore.collection('improvementSuggestions').get()
      ]);

      const badWords = badWordsSnap.docs.map(doc => ({ id: doc.id, ...doc.data() }));
      const harassmentPatterns = patternsSnap.docs.map(doc => ({ id: doc.id, ...doc.data() }));
      const categories = categoriesSnap.docs.map(doc => doc.id);
      const severityLevels = severitySnap.docs.map(doc => doc.data());
      const improvementSuggestions = {};
      suggestionsSnap.docs.forEach(doc => {
        improvementSuggestions[doc.id] = doc.data();
      });

      return {
        bad_words: badWords,
        harassment_patterns: harassmentPatterns,
        categories,
        severity_levels: severityLevels,
        improvement_suggestions: improvementSuggestions
      };
    } catch (err) {
      console.error('[FirebaseService] Firestore query error:', err);
      return null;
    }
  }

  /**
   * Admin: Add a bad word rule.
   */
  async addBadWord(wordData) {
    if (this.useBackendApi) {
      const res = await fetch('/api/v1/moderation/admin/rules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rule_type: 'word', ...wordData })
      });
      return await res.json();
    }
    const docRef = await this.firestore.collection('badWords').add({
      ...wordData,
      active: wordData.active ?? true,
      createdAt: new Date().toISOString()
    });
    return { id: docRef.id, ...wordData };
  }

  /**
   * Admin: Add a harassment pattern phrase rule.
   */
  async addHarassmentPattern(phraseData) {
    if (this.useBackendApi) {
      const res = await fetch('/api/v1/moderation/admin/rules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rule_type: 'phrase', ...phraseData })
      });
      return await res.json();
    }
    const docRef = await this.firestore.collection('harassmentPatterns').add({
      ...phraseData,
      active: phraseData.active ?? true,
      createdAt: new Date().toISOString()
    });
    return { id: docRef.id, ...phraseData };
  }

  /**
   * Admin: Delete rule.
   */
  async deleteRule(ruleType, ruleId) {
    if (this.useBackendApi) {
      const res = await fetch(`/api/v1/moderation/admin/rules/${ruleType}/${ruleId}`, {
        method: 'DELETE'
      });
      return await res.json();
    }
    const col = ruleType === 'word' ? 'badWords' : 'harassmentPatterns';
    await this.firestore.collection(col).doc(ruleId).delete();
    return { status: 'deleted', rule_id: ruleId };
  }

  /**
   * Admin: Toggle rule active status.
   */
  async toggleRuleActive(ruleType, ruleId, currentActive) {
    if (this.useBackendApi) {
      const res = await fetch(`/api/v1/moderation/admin/rules/${ruleType}/${ruleId}/toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active: !currentActive })
      });
      return await res.json();
    }
    const col = ruleType === 'word' ? 'badWords' : 'harassmentPatterns';
    await this.firestore.collection(col).doc(ruleId).update({ active: !currentActive });
    return { id: ruleId, active: !currentActive };
  }
}

export const firebaseRuleService = new FirebaseRuleService();

if (typeof window !== 'undefined') {
  window.FirebaseRuleService = firebaseRuleService;
}
