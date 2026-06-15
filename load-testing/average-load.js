import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const errorRate = new Rate('errors');
const authDuration = new Trend('auth_duration');
const healthDuration = new Trend('health_duration');

export const options = {
  stages: [
    { duration: '1m', target: 25 },
    { duration: '3m', target: 50 },
    { duration: '1m', target: 25 },
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    errors: ['rate<0.05'],
    http_req_duration: ['p(95)<3000', 'p(99)<5000'],
    auth_duration: ['p(95)<2000'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  const payload = JSON.stringify({
    email: `loadtest_${__VU}@example.com`,
    password: 'TestPassword123!',
  });

  const registerRes = http.post(
    `${BASE_URL}/auth/login`,
    payload,
    { headers: { 'Content-Type': 'application/json' } }
  );

  check(registerRes, {
    'auth endpoint responds': (r) => r.status === 200 || r.status === 401,
  });
  authDuration.add(registerRes.timings.duration);
  errorRate.add(registerRes.status >= 500);

  const healthRes = http.get(`${BASE_URL}/health`);
  check(healthRes, {
    'health endpoint is 200': (r) => r.status === 200,
  });
  healthDuration.add(healthRes.timings.duration);

  sleep(__ENV.THINK_TIME ? parseFloat(__ENV.THINK_TIME) : 2);
}
