import assert from 'node:assert';
import { api } from '../src/services/api.js';

// Setup Mock Environment
let fetchCalls = [];
let mockFetchHandler = null;
let storage = {};

globalThis.localStorage = {
  getItem: (k) => storage[k] || null,
  setItem: (k, v) => { storage[k] = String(v); },
  removeItem: (k) => { delete storage[k]; },
  clear: () => { storage = {}; },
};

globalThis.window = {
  dispatchEvent: (event) => {
    window.lastEvent = event;
  },
  lastEvent: null,
};

globalThis.CustomEvent = class CustomEvent {
  constructor(name, opts = {}) {
    this.name = name;
    this.detail = opts.detail;
  }
};

globalThis.fetch = async (url, options = {}) => {
  fetchCalls.push({ url, options });
  if (mockFetchHandler) {
    return mockFetchHandler(url, options);
  }
  return {
    ok: true,
    status: 200,
    json: async () => ({}),
  };
};

function jsonResponse(data, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => data,
  };
}

async function runTests() {
  console.log("==========================================");
  console.log("RUNNING AROVIA API CLIENT AUTH SUITE");
  console.log("==========================================");

  // ----------------------------------------------------
  // TEST 1: Valid token -> request succeeds -> no refresh call
  // ----------------------------------------------------
  {
    fetchCalls = [];
    storage = { arovia_token: 'valid-token-123' };
    mockFetchHandler = (url, opts) => {
      assert.strictEqual(opts.headers.Authorization, 'Bearer valid-token-123');
      return jsonResponse({ sessions: ['sess_1'] }, 200);
    };

    const res = await api.getUserSessions();
    assert.deepStrictEqual(res, { sessions: ['sess_1'] });
    assert.strictEqual(fetchCalls.length, 1);
    assert.strictEqual(fetchCalls[0].url, '/api/v1/interviews/sessions?limit=50&offset=0');
    console.log("✓ TEST 1 PASSED: Valid token succeeds without calling refresh.");
  }

  // ----------------------------------------------------
  // TEST 2: TOKEN_EXPIRED 401 -> refresh called once -> new token stored -> original request retried once -> retry succeeds
  // ----------------------------------------------------
  {
    fetchCalls = [];
    storage = { arovia_token: 'expired-token-abc' };
    let requestCount = 0;

    mockFetchHandler = (url, opts) => {
      if (url === '/api/v1/interviews/sessions?limit=50&offset=0') {
        requestCount++;
        if (requestCount === 1) {
          // First attempt with expired token
          assert.strictEqual(opts.headers.Authorization, 'Bearer expired-token-abc');
          return jsonResponse({ detail: 'Access token has expired.', error_code: 'TOKEN_EXPIRED' }, 401);
        } else {
          // Retried attempt with new token
          assert.strictEqual(opts.headers.Authorization, 'Bearer fresh-token-xyz');
          return jsonResponse({ sessions: ['sess_recovered'] }, 200);
        }
      } else if (url === '/api/v1/auth/refresh') {
        assert.strictEqual(opts.credentials, 'include');
        return jsonResponse({ access_token: 'fresh-token-xyz', user: { id: 'u1' } }, 200);
      }
      throw new Error(`Unexpected URL: ${url}`);
    };

    const res = await api.getUserSessions();
    assert.deepStrictEqual(res, { sessions: ['sess_recovered'] });
    assert.strictEqual(storage.arovia_token, 'fresh-token-xyz');
    assert.strictEqual(fetchCalls.length, 3); // 1. Initial 401, 2. /auth/refresh, 3. Retry 200
    console.log("✓ TEST 2 PASSED: TOKEN_EXPIRED transparently refreshes and recovers original request.");
  }

  // ----------------------------------------------------
  // TEST 3: Four concurrent TOKEN_EXPIRED requests -> exactly one refresh request -> all four original requests retry
  // ----------------------------------------------------
  {
    fetchCalls = [];
    storage = { arovia_token: 'expired-batch-token' };
    let refreshCalls = 0;

    mockFetchHandler = async (url, opts) => {
      if (url === '/api/v1/auth/refresh') {
        refreshCalls++;
        // Simulate network latency for refresh
        await new Promise(r => setTimeout(r, 20));
        return jsonResponse({ access_token: 'batch-refreshed-token', user: { id: 'u_batch' } }, 200);
      }

      if (opts.headers.Authorization === 'Bearer expired-batch-token') {
        return jsonResponse({ detail: 'Access token has expired.', error_code: 'TOKEN_EXPIRED' }, 401);
      } else if (opts.headers.Authorization === 'Bearer batch-refreshed-token') {
        return jsonResponse({ url, recovered: true }, 200);
      }
      throw new Error(`Invalid token on ${url}: ${opts.headers.Authorization}`);
    };

    const [r1, r2, r3, r4] = await Promise.all([
      api.getUserSessions(),
      api.getProgress(),
      api.getMyResume(),
      api.getPresets(),
    ]);

    assert.strictEqual(r1.recovered, true);
    assert.strictEqual(r2.recovered, true);
    assert.strictEqual(r3.recovered, true);
    assert.strictEqual(r4.recovered, true);
    assert.strictEqual(refreshCalls, 1, "Expected exactly 1 refresh call for 4 concurrent requests (single-flight lock)");
    assert.strictEqual(storage.arovia_token, 'batch-refreshed-token');
    console.log("✓ TEST 3 PASSED: Four concurrent 401 requests trigger exactly one refresh (single-flight lock).");
  }

  // ----------------------------------------------------
  // TEST 4: Refresh fails -> no infinite loop -> stale access token cleared -> auth failure propagated
  // ----------------------------------------------------
  {
    fetchCalls = [];
    storage = { arovia_token: 'expired-token-unrecoverable' };

    mockFetchHandler = (url, opts) => {
      if (url === '/api/v1/interviews/sessions?limit=50&offset=0') {
        return jsonResponse({ detail: 'Access token has expired.', error_code: 'TOKEN_EXPIRED' }, 401);
      } else if (url === '/api/v1/auth/refresh') {
        return jsonResponse({ detail: 'Invalid refresh token.', error_code: 'INVALID_REFRESH_TOKEN' }, 401);
      }
      throw new Error(`Unexpected URL: ${url}`);
    };

    let threw = false;
    try {
      await api.getUserSessions();
    } catch (err) {
      threw = true;
      assert.strictEqual(err.status, 401);
      assert.strictEqual(err.code, 'TOKEN_EXPIRED');
    }

    assert.strictEqual(threw, true, "Expected request to throw after refresh failure");
    assert.strictEqual(storage.arovia_token, undefined, "Stale token must be cleared from localStorage");
    console.log("✓ TEST 4 PASSED: Refresh failure safely clears token without infinite loops and surfaces error.");
  }

  // ----------------------------------------------------
  // TEST 5: Non-TOKEN_EXPIRED 401 -> refresh NOT called
  // ----------------------------------------------------
  {
    fetchCalls = [];
    storage = { arovia_token: 'some-token' };
    let refreshCalled = false;

    mockFetchHandler = (url, opts) => {
      if (url === '/api/v1/interviews/sessions?limit=50&offset=0') {
        return jsonResponse({ detail: 'Invalid credentials or permissions.', error_code: 'UNAUTHORIZED' }, 401);
      } else if (url === '/api/v1/auth/refresh') {
        refreshCalled = true;
        return jsonResponse({ access_token: 'new-token' }, 200);
      }
      throw new Error(`Unexpected URL: ${url}`);
    };

    let threw = false;
    try {
      await api.getUserSessions();
    } catch (err) {
      threw = true;
      assert.strictEqual(err.code, 'UNAUTHORIZED');
    }

    assert.strictEqual(threw, true);
    assert.strictEqual(refreshCalled, false, "Non-TOKEN_EXPIRED 401 must NOT trigger refresh");
    console.log("✓ TEST 5 PASSED: Non-TOKEN_EXPIRED 401 does not trigger refresh.");
  }

  // ----------------------------------------------------
  // TEST 6: Retried request receives another 401 -> no second refresh loop
  // ----------------------------------------------------
  {
    fetchCalls = [];
    storage = { arovia_token: 'token-retry-loop-test' };
    let refreshCount = 0;

    mockFetchHandler = (url, opts) => {
      if (url === '/api/v1/interviews/sessions?limit=50&offset=0') {
        // Always return TOKEN_EXPIRED 401 even after refresh
        return jsonResponse({ detail: 'Access token has expired.', error_code: 'TOKEN_EXPIRED' }, 401);
      } else if (url === '/api/v1/auth/refresh') {
        refreshCount++;
        return jsonResponse({ access_token: 'issued-token-still-bad' }, 200);
      }
      throw new Error(`Unexpected URL: ${url}`);
    };

    let threw = false;
    try {
      await api.getUserSessions();
    } catch (err) {
      threw = true;
      assert.strictEqual(err.status, 401);
    }

    assert.strictEqual(threw, true);
    assert.strictEqual(refreshCount, 1, "Refresh must execute at most ONCE per original request");
    assert.strictEqual(fetchCalls.length, 3, "Expected: 1. original -> 2. refresh -> 3. retry -> failure thrown");
    console.log("✓ TEST 6 PASSED: Retried request receiving another 401 aborts cleanly without loop.");
  }

  // ----------------------------------------------------
  // TEST 7: Resume upload 503 error surfaces accurate message
  // ----------------------------------------------------
  {
    fetchCalls = [];
    storage = { arovia_token: 'valid-token' };

    mockFetchHandler = (url, opts) => {
      if (url === '/api/v1/resumes/upload') {
        return jsonResponse(
          {
            detail: 'AI resume analysis service is temporarily unavailable. Please retry shortly.',
            error_code: 'AI_SERVICE_UNAVAILABLE',
          },
          503
        );
      }
      throw new Error(`Unexpected URL: ${url}`);
    };

    let threw = false;
    try {
      await api.uploadResume(new Blob(['fake pdf'], { type: 'application/pdf' }));
    } catch (err) {
      threw = true;
      assert.strictEqual(err.status, 503);
      assert.strictEqual(err.message, 'AI resume analysis service is temporarily unavailable. Please retry shortly.');
      assert.strictEqual(err.code, 'AI_SERVICE_UNAVAILABLE');
      assert.strictEqual(err.message.includes('evaluation'), false);
    }

    assert.strictEqual(threw, true);
    console.log("✓ TEST 7 PASSED: Resume upload 503 error surfaces accurate resume analysis message.");
  }

  console.log("==========================================");
  console.log("ALL 7 AUTH & RESUME CLIENT TESTS PASSED!");
  console.log("==========================================");
}

runTests().catch((err) => {
  console.error("Test failure:", err);
  process.exit(1);
});
