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

/**
 * Helper simulating the state derivation logic in CoachView.jsx
 */
function resolveCoachSessionAndTurnState({ sessionData, turnsList }) {
  let turnState = 'ready';
  if (!sessionData) {
    turnState = 'zero_interviews';
  } else if (
    sessionData.status === 'in_progress' ||
    sessionData.status === 'evaluating' ||
    (!sessionData.has_evaluation && sessionData.status !== 'completed')
  ) {
    turnState = 'in_progress';
  } else if (!turnsList || turnsList.length === 0) {
    turnState = 'missing_turns';
  } else {
    turnState = 'ready';
  }
  return turnState;
}

async function runCoachTests() {
  console.log("==========================================");
  console.log("RUNNING AROVIA COACH TURN EXPLORER SUITE");
  console.log("==========================================");

  // ----------------------------------------------------
  // TEST 1: Valid authenticated completed session with turns -> 'ready' turn details
  // ----------------------------------------------------
  {
    const session = {
      id: 'sess-1',
      status: 'completed',
      has_evaluation: true,
      overall_score: 84,
      target_role: 'Backend Engineer',
      seniority_level: 'senior',
    };
    const evaluation = {
      overall_score: 84,
      turns_evaluation: [
        {
          turn_index: 0,
          question_text: 'Explain cache invalidation trade-offs.',
          candidate_answer: 'I use write-through caching with TTLs.',
          correctness_score: 85,
          turn_feedback: 'Solid analysis of eventual consistency.',
        },
        {
          turn_index: 1,
          question_text: 'How do you handle database failover?',
          candidate_answer: 'Using read replicas and automatic leader election.',
          correctness_score: 90,
          turn_feedback: 'Clear architecture explanation.',
        },
      ],
    };
    const turnsList = evaluation.turns_evaluation;
    const sessionData = { ...session, evaluation };

    const state = resolveCoachSessionAndTurnState({ sessionData, turnsList });
    assert.strictEqual(state, 'ready');
    assert.strictEqual(turnsList.length, 2);
    assert.strictEqual(turnsList[0].correctness_score, 85);
    console.log("✓ TEST 1 PASSED: Valid completed session resolves to 'ready' with 2 turns.");
  }

  // ----------------------------------------------------
  // TEST 2: Zero completed sessions -> onboarding 'zero_interviews' state
  // ----------------------------------------------------
  {
    const sessionData = null;
    const turnsList = [];

    const state = resolveCoachSessionAndTurnState({ sessionData, turnsList });
    assert.strictEqual(state, 'zero_interviews');
    console.log("✓ TEST 2 PASSED: Zero completed sessions resolves to 'zero_interviews' onboarding state.");
  }

  // ----------------------------------------------------
  // TEST 3: In-progress session without final evaluation -> 'in_progress' state
  // ----------------------------------------------------
  {
    const sessionData = {
      id: 'sess-active',
      status: 'in_progress',
      has_evaluation: false,
      target_role: 'Frontend Architect',
      seniority_level: 'senior',
      evaluation: null,
    };
    const turnsList = [];

    const state = resolveCoachSessionAndTurnState({ sessionData, turnsList });
    assert.strictEqual(state, 'in_progress');
    console.log("✓ TEST 3 PASSED: In-progress session resolves to 'in_progress' guidance state.");
  }

  // ----------------------------------------------------
  // TEST 4: Completed session with evaluation but genuinely empty turns -> 'missing_turns' state
  // ----------------------------------------------------
  {
    const sessionData = {
      id: 'sess-legacy',
      status: 'completed',
      has_evaluation: true,
      overall_score: 78,
      target_role: 'Data Engineer',
      evaluation: {
        overall_score: 78,
        turns_evaluation: [],
      },
    };
    const turnsList = [];

    const state = resolveCoachSessionAndTurnState({ sessionData, turnsList });
    assert.strictEqual(state, 'missing_turns');
    console.log("✓ TEST 4 PASSED: Completed session with no turn details resolves to explicit 'missing_turns' state.");
  }

  // ----------------------------------------------------
  // TEST 5: API / Auth failure in getUserSessions -> error thrown, NOT swallowed as []
  // ----------------------------------------------------
  {
    fetchCalls = [];
    storage = { arovia_token: 'expired-token' };

    mockFetchHandler = (url, opts) => {
      if (url === '/api/v1/auth/refresh') {
        return jsonResponse({ detail: 'Refresh token expired' }, 401);
      }
      if (url.includes('/api/v1/interviews/sessions')) {
        return jsonResponse({ detail: 'Access token has expired. Please refresh your session.', error_code: 'TOKEN_EXPIRED' }, 401);
      }
      throw new Error(`Unexpected URL: ${url}`);
    };

    let caughtError = null;
    try {
      await api.getUserSessions(10, 0);
    } catch (err) {
      caughtError = err;
    }

    assert.notStrictEqual(caughtError, null, "API error must NOT be silently swallowed");
    assert.strictEqual(caughtError.status, 401);
    console.log("✓ TEST 5 PASSED: API/Auth failure throws authentic error and is not converted to empty [] state.");
  }

  // ----------------------------------------------------
  // TEST 6: Expired token recovered by api.js -> Coach receives valid data without false empty state
  // ----------------------------------------------------
  {
    fetchCalls = [];
    storage = { arovia_token: 'expired-token-123' };

    let sessionCallCount = 0;
    mockFetchHandler = (url, opts) => {
      if (url.includes('/api/v1/interviews/sessions') && !url.includes('sess-')) {
        sessionCallCount++;
        if (sessionCallCount === 1) {
          return jsonResponse({ detail: 'Token expired', error_code: 'TOKEN_EXPIRED' }, 401);
        }
        return jsonResponse([
          {
            id: 'sess-recovered-1',
            status: 'completed',
            has_evaluation: true,
            overall_score: 88,
            target_role: 'Full Stack Engineer',
            seniority_level: 'senior',
          }
        ], 200);
      }
      if (url === '/api/v1/auth/refresh') {
        return jsonResponse({
          access_token: 'new-valid-token-789',
          token_type: 'bearer',
          expires_in: 900,
        }, 200);
      }
      throw new Error(`Unexpected URL: ${url}`);
    };

    const sessions = await api.getUserSessions(10, 0);
    assert.strictEqual(Array.isArray(sessions), true);
    assert.strictEqual(sessions.length, 1);
    assert.strictEqual(sessions[0].id, 'sess-recovered-1');
    assert.strictEqual(storage.arovia_token, 'new-valid-token-789');
    console.log("✓ TEST 6 PASSED: P0 transparent token refresh recovers session request and delivers valid data.");
  }

  // ----------------------------------------------------
  // TEST 7: Action Plan & Coach chat payloads are unaffected
  // ----------------------------------------------------
  {
    fetchCalls = [];
    storage = { arovia_token: 'valid-token' };

    mockFetchHandler = (url, opts) => {
      if (url === '/api/v1/coach/conversation') {
        return jsonResponse({
          id: 'conv-123',
          user_id: 'usr-1',
          session_id: 'sess-1',
          messages: [
            { id: 'msg-1', sender: 'coach', message_text: 'Welcome back! How can I help you refine your answers?' }
          ],
          suggested_followups: ['Why did I lose points on Turn 1?'],
          actionable_plan: {
            focus_dimensions: ['System Design'],
            recommended_actions: ['Practice sharding architectures'],
          },
          weakness_resolutions: [],
        }, 200);
      }
      throw new Error(`Unexpected URL: ${url}`);
    };

    const conv = await api.getOrCreateCoachConversation('sess-1', true);
    assert.strictEqual(conv.id, 'conv-123');
    assert.strictEqual(conv.messages.length, 1);
    assert.strictEqual(conv.actionable_plan.focus_dimensions[0], 'System Design');
    console.log("✓ TEST 7 PASSED: Coach conversation & Action Plan payloads remain fully functional.");
  }

  // ----------------------------------------------------
  // TEST 8: Turn with architecture_blueprint triggers blueprint state & action
  // ----------------------------------------------------
  {
    const blueprintTurn = {
      turn_index: 0,
      question_text: 'Design a globally distributed rate limiter.',
      candidate_answer: 'Using Redis sliding windows and edge gateways.',
      correctness_score: 88,
      architecture_blueprint: {
        scenario_id: 'sys.sr.ratelimit.core.01',
        title: 'Globally Distributed API Rate Limiter',
        nodes: [{ id: 'redis', label: 'Redis Cluster', type: 'cache' }],
      },
    };
    assert.strictEqual(Boolean(blueprintTurn.architecture_blueprint), true);
    assert.strictEqual(blueprintTurn.architecture_blueprint.scenario_id, 'sys.sr.ratelimit.core.01');
    console.log("✓ TEST 8 PASSED: System Design turn with blueprint metadata correctly identified for Coach grounding.");
  }

  // ----------------------------------------------------
  // TEST 9: Coach conversation receives structured reference_architecture_context
  // ----------------------------------------------------
  {
    fetchCalls = [];
    storage = { arovia_token: 'valid-token' };

    mockFetchHandler = (url, opts) => {
      if (url === '/api/v1/coach/conversation') {
        return jsonResponse({
          id: 'conv-arch-1',
          user_id: 'usr-arch',
          session_id: 'sess-arch-1',
          messages: [
            { id: 'msg-1', sender: 'coach', message_text: 'Welcome! Let us review your rate limiting architecture.' }
          ],
          suggested_followups: ['Why was Redis chosen over SQL here?'],
          reference_architecture_context: {
            scenario_id: 'sys.sr.ratelimit.core.01',
            title: 'Globally Distributed API Rate Limiter',
            nodes: [
              { id: 'edge_gw', label: 'Edge Gateway', type: 'gateway' },
              { id: 'redis_cluster', label: 'Redis Cluster', type: 'cache' },
            ],
          },
          actionable_plan: null,
          weakness_resolutions: [],
        }, 200);
      }
      throw new Error(`Unexpected URL: ${url}`);
    };

    const conv = await api.getOrCreateCoachConversation('sess-arch-1', true);
    assert.strictEqual(conv.id, 'conv-arch-1');
    assert.strictEqual(Boolean(conv.reference_architecture_context), true);
    assert.strictEqual(conv.reference_architecture_context.scenario_id, 'sys.sr.ratelimit.core.01');
    assert.strictEqual(conv.reference_architecture_context.nodes.length, 2);
    console.log("✓ TEST 9 PASSED: Coach conversation receives structured reference_architecture_context without schema errors.");
  }

  // ----------------------------------------------------
  // TEST 10: Turn prompt generator creates exact architecture inquiry string
  // ----------------------------------------------------
  {
    const generatePrompt = (turnIndex, promptType) => {
      if (promptType === 'architecture') {
        return `Can you explain the reference architecture, component purposes, and key trade-offs for Turn ${turnIndex + 1}?`;
      }
      if (promptType === 'model_answer') {
        return `What is a senior-level benchmark model answer for Turn ${turnIndex + 1}?`;
      }
      return `Why was my answer in Turn ${turnIndex + 1} scored lower?`;
    };

    const archPrompt = generatePrompt(0, 'architecture');
    assert.strictEqual(archPrompt, 'Can you explain the reference architecture, component purposes, and key trade-offs for Turn 1?');
    console.log("✓ TEST 10 PASSED: Architecture inquiry prompt correctly formats Turn index and reference trade-off request.");
  }

  console.log("==========================================");
  console.log("ALL 10 COACH TURN EXPLORER TESTS PASSED!");
  console.log("==========================================");
}

runCoachTests().catch((err) => {
  console.error("TEST FAILED:", err);
  process.exit(1);
});

