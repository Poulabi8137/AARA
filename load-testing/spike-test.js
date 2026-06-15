import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const errorRate = new Rate('errors');
const latency = new Trend('request_latency');

export const options = {
  stages: [
    { duration: '30s', target: 10 },
    { duration: '10s', target: 500 },
    { duration: '30s', target: 500 },
    { duration: '10s', target: 10 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    errors: ['rate<0.15'],
    http_req_duration: ['p(95)<10000'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  const endpoints = [
    `${BASE_URL}/health`,
    `${BASE_URL}/docs`,
    `${BASE_URL}/openapi.json`,
  ];
  const url = endpoints[Math.floor(Math.random() * endpoints.length)];

  const res = http.get(url);
  check(res, {
    'status is 2xx': (r) => r.status >= 200 && r.status < 300,
  });
  latency.add(res.timings.duration);
  errorRate.add(res.status >= 400);

  sleep(0.3);
}
