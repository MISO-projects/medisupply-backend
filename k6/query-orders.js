import http from 'k6/http';
import { check, sleep } from 'k6';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.2/index.js';

const BASE_URL = "http://localhost:3014";
const EMAIL = "alejo@mail.com"
const PASSWORD = "Password123!";
const ORDERS_URL = `${BASE_URL}/ordenes/`;
const LOGIN_URL = `${BASE_URL}/autenticacion/login`;

export const options = {
  scenarios: {
    constant_load: {
      executor: 'constant-arrival-rate',
      rate: 7,
      timeUnit: '1s',
      duration: '1m',
      preAllocatedVUs: 20,
      maxVUs: 100,
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<1000', 'p(99)<2000', 'avg<500'], // 95% under 1s, 99% under 2s, average under 500ms
  },
};

// Función setup que k6 ejecutará antes de las pruebas
export function setup() {
  // Step 1: Login to get authentication token
  const loginPayload = {
    email: EMAIL,
    password: PASSWORD,
  };

  const headers = {
    "Content-Type": "application/json",
  };

  console.log("Attempting to login...");
  const loginResponse = http.post(LOGIN_URL, JSON.stringify(loginPayload), { headers });
  
  if (loginResponse.status !== 200 && loginResponse.status !== 201) {
    console.log(`Login failed with status: ${loginResponse.status}`);
    console.log(`Login response body: ${loginResponse.body}`);
    throw new Error(`Login failed: ${loginResponse.status}`);
  }

  let token;
  try {
    const loginData = JSON.parse(loginResponse.body);
    token = loginData.token || loginData.access_token || loginData.accessToken;
    
    if (!token) {
      console.log(`Token not found in response: ${loginResponse.body}`);
      throw new Error("Token not found in login response");
    }
    
    console.log("Login successful, token obtained");
  } catch (e) {
    console.log(`Failed to parse login response: ${loginResponse.body}`);
    throw e;
  }

  // Step 2: Get all order IDs
  const response = http.get(`${ORDERS_URL}ids`);
  try {
    const data = JSON.parse(response.body);
    if (data.data && Array.isArray(data.data)) {
      console.log(`Retrieved ${data.data.length} order IDs`);
      return { orderIds: data.data, token: token };
    }
  } catch (e) {
    console.error('Error parsing order IDs:', e);
  }
  return { orderIds: [], token: token };
}

export default function (data) {
  const { orderIds, token } = data;
  
  if (orderIds.length === 0) {
    console.error('No order IDs available for testing');
    return;
  }

  const randomId = orderIds[Math.floor(Math.random() * orderIds.length)];
  
  const headers = {
    "Authorization": `Bearer ${token}`,
  };
  
  const response = http.get(`${ORDERS_URL}${randomId}`, { headers });

  check(response, {
    'status is 200': (r) => r.status === 200,
    'has order data': (r) => {
      try {
        const data = JSON.parse(r.body);
        return data !== null && data.data !== undefined;
      } catch (e) {
        return false;
      }
    },
  });

  sleep(0.1);
}

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
  };
}