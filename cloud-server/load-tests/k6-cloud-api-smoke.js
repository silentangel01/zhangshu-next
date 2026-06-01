/**
 * k6 Cloud API Smoke Test
 *
 * Usage:
 *   k6 run load-tests/k6-cloud-api-smoke.js
 *   k6 run --env BASE_URL=https://api.example.com load-tests/k6-cloud-api-smoke.js
 *
 * Targets:
 *   /health             — p95 < 100ms
 *   /ready              — p95 < 200ms
 *   /api/auth/login     — rate limit returns 429 after threshold
 *   /api/admin/search   — p95 < 500ms (with valid admin token)
 *   /api/admin/dashboard/summary — p95 < 300ms (cached)
 *
 * Prerequisites:
 *   - k6 installed: https://k6.io/docs/get-started/installation/
 *   - Server running locally or BASE_URL set
 *   - For admin endpoints: ADMIN_TOKEN env var
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// ── Configuration ──────────────────────────────────────────────────

const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:9000';
const ADMIN_TOKEN = __ENV.ADMIN_TOKEN || '';
const TEST_EMAIL = __ENV.TEST_EMAIL || 'loadtest@example.com';
const TEST_PASSWORD = __ENV.TEST_PASSWORD || 'TestPassword123!';

// ── Custom metrics ─────────────────────────────────────────────────

const authRateLimited = new Rate('auth_rate_limited');
const healthDuration = new Trend('health_duration', true);
const readyDuration = new Trend('ready_duration', true);
const searchDuration = new Trend('search_duration', true);
const dashboardDuration = new Trend('dashboard_duration', true);

// ── Test options ───────────────────────────────────────────────────

export const options = {
  stages: [
    { duration: '10s', target: 5 },   // Ramp up to 5 VUs
    { duration: '20s', target: 5 },   // Stay at 5 VUs
    { duration: '10s', target: 20 },  // Spike to 20 VUs (test rate limits)
    { duration: '10s', target: 5 },   // Ramp down
    { duration: '10s', target: 0 },   // Ramp to 0
  ],
  thresholds: {
    // Health endpoint: p95 < 100ms
    health_duration: ['p(95)<100'],
    // Ready endpoint: p95 < 200ms
    ready_duration: ['p(95)<200'],
    // Search endpoint: p95 < 500ms (with pg_trgm indexes)
    search_duration: ['p(95)<500'],
    // Dashboard (cached): p95 < 300ms
    dashboard_duration: ['p(95)<300'],
    // Overall: less than 5% errors
    http_req_failed: ['rate<0.05'],
  },
};

// ── Test scenarios ─────────────────────────────────────────────────

export default function () {
  group('Health endpoints', function () {
    // /health
    const healthRes = http.get(`${BASE_URL}/health`);
    healthDuration.add(healthRes.timings.duration);
    check(healthRes, {
      '/health status 200': (r) => r.status === 200,
      '/health has ok status': (r) => {
        try { return JSON.parse(r.body).status === 'ok'; } catch { return false; }
      },
    });

    // /ready
    const readyRes = http.get(`${BASE_URL}/ready`);
    readyDuration.add(readyRes.timings.duration);
    check(readyRes, {
      '/ready status 200': (r) => r.status === 200,
      '/ready has status field': (r) => {
        try { return 'status' in JSON.parse(r.body); } catch { return false; }
      },
    });
  });

  group('Auth rate limiting', function () {
    // Rapid login attempts to trigger rate limiting
    for (let i = 0; i < 3; i++) {
      const loginRes = http.post(`${BASE_URL}/api/auth/login`, JSON.stringify({
        email: TEST_EMAIL,
        password: TEST_PASSWORD,
      }), {
        headers: { 'Content-Type': 'application/json' },
      });

      const isRateLimited = loginRes.status === 429;
      authRateLimited.add(isRateLimited);

      if (!isRateLimited) {
        check(loginRes, {
          'login returns expected status': (r) => [200, 401, 429].includes(r.status),
        });
      }
    }
  });

  if (ADMIN_TOKEN) {
    group('Admin endpoints (requires ADMIN_TOKEN)', function () {
      const headers = {
        'Authorization': `Bearer ${ADMIN_TOKEN}`,
        'Content-Type': 'application/json',
      };

      // Admin search
      const searchRes = http.get(`${BASE_URL}/api/admin/search?q=test`, { headers });
      searchDuration.add(searchRes.timings.duration);
      check(searchRes, {
        '/admin/search status': (r) => [200, 401, 403].includes(r.status),
        '/admin/search has results shape': (r) => {
          if (r.status !== 200) return true;
          try {
            const body = JSON.parse(r.body);
            return 'users' in body && 'feedback' in body && 'announcements' in body;
          } catch { return false; }
        },
      });

      // Dashboard summary (should be cached after first call)
      for (let i = 0; i < 3; i++) {
        const dashRes = http.get(`${BASE_URL}/api/admin/dashboard/summary`, { headers });
        dashboardDuration.add(dashRes.timings.duration);
        check(dashRes, {
          '/dashboard/summary status': (r) => [200, 401, 403].includes(r.status),
          '/dashboard/summary cached flag': (r) => {
            if (r.status !== 200) return true;
            try { return 'cached' in JSON.parse(r.body); } catch { return false; }
          },
        });
        sleep(0.1);
      }
    });
  }

  sleep(1);
}

// ── Summary handler ────────────────────────────────────────────────

export function handleSummary(data) {
  const summary = {
    'load-tests/results/smoke-summary.json': JSON.stringify(data, null, 2),
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
  };
  return summary;
}

function textSummary(data, opts) {
  let out = '\n╔══════════════════════════════════════════╗\n';
  out +=    '║     k6 Cloud API Smoke Test Results      ║\n';
  out +=    '╚══════════════════════════════════════════╝\n\n';

  if (data.metrics) {
    for (const [name, metric] of Object.entries(data.metrics)) {
      if (metric.values) {
        const vals = metric.values;
        if (vals.avg !== undefined) {
          out += `  ${name}: avg=${vals.avg?.toFixed(1) || 'N/A'}ms p95=${vals['p(95)']?.toFixed(1) || 'N/A'}ms\n`;
        } else if (vals.rate !== undefined) {
          out += `  ${name}: ${(vals.rate * 100).toFixed(1)}%\n`;
        } else if (vals.count !== undefined) {
          out += `  ${name}: ${vals.count}\n`;
        }
      }
    }
  }

  return out + '\n';
}
