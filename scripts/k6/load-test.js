import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { uuidv4 } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

// Base configuration via env vars
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_KEY = __ENV.API_KEY || 'set-me';
const QUESTION_SET_ID = __ENV.QUESTION_SET_ID || null;
const INTERVIEW_MODE = __ENV.INTERVIEW_MODE || 'dynamic_gap'; // dynamic_gap | predefined_questions
const SKIP_INTERVIEW = __ENV.SKIP_INTERVIEW === '1';

// Interview data set (override with INTERVIEW_CASES env as JSON string)
const INTERVIEW_CASES = getInterviewCases();

// Main scenario tuning
const VUS = Number(__ENV.VUS || 1);
const ITERATIONS = Number(__ENV.ITERATIONS || 1);

// Order controller: comma separated list of step names
// Default: health -> interview -> predefined -> health
const SCENARIO_ORDER = (__ENV.SCENARIO_ORDER || 'health,interview,health')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean);

const HEADERS = {
  'Content-Type': 'application/json',
  'X-API-Key': API_KEY,
};

export const options = {
  thresholds: {
    http_req_failed: ['rate<0.1'], // 10% error rate
    http_req_duration: ['p(95)<60000'], // 95% of requests below 60s
  },
  scenarios: {
    main: {
      executor: 'per-vu-iterations',
      vus: VUS,
      iterations: ITERATIONS,
      exec: 'mainScenario',
    },
  },
};

export function mainScenario() {
  runOrderedSteps();
  // Add delay between requests to prevent DB connection pool exhaustion
  // Adjust sleep based on interview latency
  const delayMs = Number(__ENV.DELAY_MS || 2000);
  sleep(delayMs / 1000);
}

function runOrderedSteps() {
  for (const step of SCENARIO_ORDER) {
    if (step === 'health') {
      runHealth();
    } else if (step === 'interview') {
      runInterview();
    } else if (step === 'predefined') {
      runPredefinedReads();
    }
  }
}

function runHealth() {
  group('health-checks', () => {
    const ping = http.get(`${BASE_URL}/ping`);
    console.log(`PING: status=${ping.status}, body=${ping.body}, url=${BASE_URL}/ping`);
    check(ping, {
      'ping 200': (r) => r.status === 200,
      'ping has pong': (r) => r.json('message') === 'pong',
    });

    const health = http.get(`${BASE_URL}/health`);
    console.log(`HEALTH: status=${health.status}, body=${health.body}, url=${BASE_URL}/health`);
    check(health, {
      'health 200': (r) => r.status === 200,
      'health has status': (r) => r.json('status') === 'healthy',
    });
  });
}

function runPredefinedReads() {
  group('predefined-reads', () => {
    const roles = http.get(`${BASE_URL}/predefined/roles?limit=20`, { headers: HEADERS });
    check(roles, {
      'roles 200': (r) => r.status === 200,
    });

    const sets = http.get(`${BASE_URL}/predefined/question-sets?limit=20`, { headers: HEADERS });
    check(sets, {
      'question sets 200': (r) => r.status === 200,
    });

    if (QUESTION_SET_ID) {
      const qs = http.get(`${BASE_URL}/predefined/question-sets/${QUESTION_SET_ID}/full-details`, { headers: HEADERS });
      check(qs, {
        'question set details ok': (r) => r.status === 200,
      });
    }
  });
}

function runInterview() {
  if (SKIP_INTERVIEW) {
    return;
  }

  const caseData = pickInterviewCase();
  if (!caseData) {
    return;
  }

  group('interview-flow', () => {
    const candidateId = `loadtest-${uuidv4()}`;
    const startPayload = {
      candidate_id: candidateId,
      resume_text: caseData.resume_text,
      mode: caseData.mode || INTERVIEW_MODE,
    };

    const qsId = caseData.question_set_id || QUESTION_SET_ID;
    if (startPayload.mode === 'predefined_questions' && qsId) {
      startPayload.question_set_id = qsId;
    }

    const startRes = http.post(`${BASE_URL}/interview/start`, JSON.stringify(startPayload), { headers: HEADERS });
    if (startRes.status !== 201) {
      console.error(`Interview START FAILED: status=${startRes.status}, body=${startRes.body}, candidate=${candidateId}`);
    }
    const startOk = check(startRes, {
      'start 201': (r) => r.status === 201,
      'start has thread_id': (r) => !!r.json('thread_id'),
    });

    if (!startOk) {
      return;
    }

    const threadId = startRes.json('thread_id');
    for (const answer of caseData.answers || []) {
      const continuePayload = {
        thread_id: threadId,
        answer,
      };

      const contRes = http.post(`${BASE_URL}/interview/continue`, JSON.stringify(continuePayload), { headers: HEADERS });
      const ok = check(contRes, {
        'continue 200': (r) => r.status === 200,
      });

      // Stop early if API signals completion or returns non-200
      if (!ok || contRes.json('completed')) {
        break;
      }
    }
  });
}

function getInterviewCases() {
  if (__ENV.INTERVIEW_CASES) {
    try {
      const parsed = JSON.parse(__ENV.INTERVIEW_CASES);
      if (Array.isArray(parsed) && parsed.length > 0) {
        return parsed;
      }
    } catch (e) {
      console.error('Failed to parse INTERVIEW_CASES JSON, falling back to default set.', e);
    }
  }

  return [
    {
      resume_text: 'Sarah\nProfile Summary: Frontend Developer with 4 years of experience in building responsive web applications using React and Vue.js. Skilled in creating intuitive user interfaces and optimizing performance for large-scale platforms.\nKey Skills: JavaScript (ES6+), React, Vue.js, HTML5, CSS3, Responsive Design, UI/UX Collaboration\nProfessional Experience: Frontend Engineer – E-Commerce Platform (2020–Present): Developed dynamic product pages and checkout flows; improved site speed and user engagement; collaborated with designers to enhance usability. Web Developer – Digital Agency (2017–2020): Built client websites with modern frameworks; ensured cross-browser compatibility; implemented SEO best practices.\nEducation: Bachelor’s Degree in Information Technology, Global University',
      mode: 'dynamic_gap',
      answers: [
        'Worked 5 years building REST APIs with FastAPI; led a team of 3; handled 15k rps peak.',
        'Used Docker and Kubernetes for deployment; owned CI/CD with GitHub Actions.',
        'Optimized Postgres queries with proper indexing and analyzed plans.',
        'Implemented monitoring with Prometheus and Grafana; set up alerts for key metrics.',
        'Familiar with AWS services like EC2, S3, RDS, and Lambda for scalable deployments.',
      ],
    },
  ];
}

function pickInterviewCase() {
  if (!INTERVIEW_CASES.length) {
    return null;
  }
  const idx = (__ITER || 0) % INTERVIEW_CASES.length;
  return INTERVIEW_CASES[idx];
}
