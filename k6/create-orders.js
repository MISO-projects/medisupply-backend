import http from "k6/http";
import { check, sleep } from "k6";
import { uuidv4 } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.2/index.js'; 

const BASE_URL = "http://localhost:3014";
const ORDERS_URL = `${BASE_URL}/ordenes/`;
const LOGIN_URL = `${BASE_URL}/autenticacion/login`;
const CLIENT_ID ="039afa14-f75b-4f32-8f44-71c924443c6a"
const SELLER_ID = "412cb8a1-fb3e-4b22-ad98-9c99c826648f"
const PRODUCT_ID = "77977de4-228f-4774-97a2-f1b10f359a66";
const EMAIL = "Stacey_Ebert98@hotmail.com"
const PASSWORD = "Password123!"

// Global variable to store the token
let authToken = null;

// Configuración de la prueba
export const options = {
  scenarios: {
    constant_load: {
      executor: "constant-arrival-rate",
      rate: 7, // ~400 órdenes por minuto (7 por segundo)
      // rate: 1,
      timeUnit: "1s",
      duration: "1m",
      // duration: "2s",
      preAllocatedVUs: 20,
      maxVUs: 100,
    },
  },
  thresholds: {
    http_req_duration: ["p(95)<2000"], // 95% de las peticiones deben completarse en menos de 2s
  },
};

// Setup function - runs once per VU before the default function
export function setup() {
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

  return { token: token };
}


export default function (data) {
  // Get the token from setup
  const token = data.token;

  const payload = {
    id_cliente: CLIENT_ID,
    id_vendedor: SELLER_ID,
    observaciones: "Test order",
    detalles: [
      {
        id_producto: PRODUCT_ID,
        cantidad: 1,
        precio_unitario: 100,
      },
    ],
  };

  const headers = {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${token}`,
  };

  const response = http.post(ORDERS_URL, JSON.stringify(payload), { headers });

  // Log response details for debugging 422 errors
  if (response.status === 422) {
    console.log(`422 Error - Status: ${response.status}`);
    console.log(`Response Body: ${response.body}`);
    console.log(`Request Payload: ${JSON.stringify(payload, null, 2)}`);
  }

  check(response, {
    "status is 200 or 201": (r) => r.status === 200 || r.status === 201,
    "has order id": (r) => {
      if (r.status === 200 || r.status === 201) {
        try {
          return JSON.parse(r.body).id !== undefined;
        } catch (e) {
          console.log(`Failed to parse response body: ${r.body}`);
          return false;
        }
      }
      return false;
    },
    "response time < 2s": (r) => r.timings.duration < 2000,
  });

  sleep(0.1);
}

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
  };
}
