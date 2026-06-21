// =====================================================================
// VESTRA — Load Test (k6)
// =====================================================================
// Simulates 50 concurrent users ramping up over 6 minutes.
//
// Thresholds:
//   - p95 response time < 500ms
//   - Error rate < 1%
//
// Run:
//   k6 run vestra-load-test.js
//   k6 run -e BASE_URL=https://staging.vestra.co.ke -e TEST_TOKEN=... vestra-load-test.js
// =====================================================================

import http from "k6/http";
import { check, sleep, group } from "k6";
import { Rate, Trend } from "k6/metrics";

// ── Environment ──────────────────────────────────────────────────────
const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const TEST_TOKEN = __ENV.TEST_TOKEN || "test-load-token";

// ── Custom metrics ───────────────────────────────────────────────────
const errorRate = new Rate("errors");
const healthDuration = new Trend("health_duration");
const authDuration = new Trend("auth_duration");
const propertiesDuration = new Trend("properties_duration");

// ── Configuration ────────────────────────────────────────────────────
export const options = {
  stages: [
    { duration: "1m", target: 10 },   // Ramp up to 10 users
    { duration: "2m", target: 50 },   // Ramp up to 50 users
    { duration: "3m", target: 50 },   // Stay at 50 users (plateau)
    { duration: "1m", target: 0 },    // Ramp down to 0
  ],
  thresholds: {
    http_req_duration: ["p(95)<500"],
    http_req_failed: ["rate<0.01"],
    errors: ["rate<0.01"],
    health_duration: ["p(95)<300"],
    auth_duration: ["p(95)<800"],
    properties_duration: ["p(95)<1000"],
  },
  // 10% of requests can be discarded from statistics (smoothing)
  "summaryTrendStats": ["avg", "min", "med", "max", "p(90)", "p(95)", "p(99)"],
};

// ── Setup: authenticate once to get a valid token ──────────────────
export function setup() {
  if (!__ENV.TEST_TOKEN) {
    console.warn("TEST_TOKEN not provided — using hardcoded fallback. " +
      "Set TEST_TOKEN env var for realistic auth.");
    return { token: "setup-fallback-token" };
  }
  return { token: __ENV.TEST_TOKEN };
}

// ── Main test iteration ──────────────────────────────────────────────
export default function (data) {
  const token = data.token;
  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };

  // ── 1. Health check (lightweight) ─────────────────────────────────
  group("health endpoint", function () {
    const res = http.get(`${BASE_URL}/health`);
    const ok = check(res, {
      "health returns 200": (r) => r.status === 200,
    });
    errorRate.add(!ok);
    healthDuration.add(res.timings.duration);
  });

  sleep(1);

  // ── 2. Authentication (login simulation) ──────────────────────────
  group("authentication", function () {
    const vu = __VU;
    const iter = __ITER;
    const payload = JSON.stringify({
      email: `loadtest_${vu}_${iter}@vestra.loadtest`,
      password: "LoadTestPass123!",
    });

    const res = http.post(`${BASE_URL}/api/v1/auth/login`, payload, {
      headers: { "Content-Type": "application/json" },
      tags: { name: "auth_login" },
    });

    const ok = check(res, {
      "auth returns 200 or 422": (r) => r.status === 200 || r.status === 422,
    });

    // 422 is acceptable (fake user won't exist) — that's a valid response
    if (res.status === 200) {
      check(res, {
        "auth response has access_token": (r) => r.json("access_token") !== undefined,
      });
    }

    errorRate.add(!ok);
    authDuration.add(res.timings.duration);
  });

  sleep(1);

  // ── 3. Properties list ────────────────────────────────────────────
  group("properties listing", function () {
    const res = http.get(
      `${BASE_URL}/api/v1/properties?skip=0&limit=10`,
      { headers, tags: { name: "properties_list" } }
    );

    const ok = check(res, {
      "properties returns 200": (r) => r.status === 200,
      "properties returns array": (r) => {
        try {
          return Array.isArray(JSON.parse(r.body));
        } catch {
          return false;
        }
      },
    });

    errorRate.add(!ok);
    propertiesDuration.add(res.timings.duration);
  });

  sleep(1);

  // ── 4. Property detail (randomized) ──────────────────────────────
  group("property detail", function () {
    const propertyId = ((__VU * 100 + __ITER) % 20) + 1;
    const res = http.get(
      `${BASE_URL}/api/v1/properties/${propertyId}`,
      { headers, tags: { name: "property_detail" } }
    );

    check(res, {
      "property detail returns 200 or 404": (r) =>
        r.status === 200 || r.status === 404,
    });

    errorRate.add(res.status >= 500);
  });

  sleep(2);

  // ── 5. Search endpoint ───────────────────────────────────────────
  group("property search", function () {
    const searchTerms = ["house", "land", "apartment", "office", "villa"];
    const q = searchTerms[__VU % searchTerms.length];
    const res = http.get(
      `${BASE_URL}/api/v1/properties/search?q=${q}&skip=0&limit=5`,
      { headers, tags: { name: "property_search" } }
    );

    check(res, {
      "search returns 200": (r) => r.status === 200,
    });

    errorRate.add(res.status >= 500);
  });

  sleep(2);
}

// ── Teardown ─────────────────────────────────────────────────────────
export function teardown(data) {
  console.log(`Load test complete. Base URL: ${BASE_URL}`);
}
