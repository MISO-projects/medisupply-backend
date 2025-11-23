import http from "k6/http";
import { check, sleep } from "k6";
import { uuidv4 } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.2/index.js'; 

// Environment variables with defaults
const BFF_WEB_URL = __ENV.BFF_WEB_URL || "http://localhost:3013";
const BFF_MOVIL_URL = __ENV.BFF_MOVIL_URL || "http://localhost:3014";
const EMAIL = __ENV.EMAIL || "alejo@mail.com";
const PASSWORD = __ENV.PASSWORD || "Password123!";

// Derived URLs
const ORDERS_URL = `${BFF_MOVIL_URL}/ordenes/`;
const LOGIN_URL = `${BFF_MOVIL_URL}/autenticacion/login`;
const CLIENTES_URL = `${BFF_MOVIL_URL}/clientes/`;
const VENDEDORES_URL = `${BFF_WEB_URL}/ventas/vendedores`;
const INVENTARIO_URL = `${BFF_MOVIL_URL}/inventario/`;

// Configuración de la prueba
export const options = {
  scenarios: {
    constant_load: {
      executor: "constant-arrival-rate",
      rate: 7, // ~400 órdenes por minuto (7 por segundo)
      timeUnit: "1s",
      duration: "1m",
      preAllocatedVUs: 20,
      maxVUs: 100,
    },
  },
  thresholds: {
    http_req_duration: ["p(95)<2000", "p(99)<3000", "avg<1000"], // 95% under 2s, 99% under 3s, average under 1s
    http_req_failed: ["rate<0.01"], // Less than 1% of requests should fail
  },
};

// Setup function - runs once per VU before the default function
export function setup() {
  // Log configuration
  console.log("=== K6 Load Test Configuration ===");
  console.log(`BFF Web URL: ${BFF_WEB_URL}`);
  console.log(`BFF Móvil URL: ${BFF_MOVIL_URL}`);
  console.log(`Email: ${EMAIL}`);
  console.log("==================================");

  const headers = {
    "Content-Type": "application/json",
  };

  // Step 1: Login to get authentication token
  console.log("Attempting to login...");
  const loginPayload = {
    email: EMAIL,
    password: PASSWORD,
  };
  
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

  const authHeaders = {
    "Authorization": `Bearer ${token}`,
    "Content-Type": "application/json",
  };

  // Step 2: Fetch all clients
  console.log("Fetching clients...");
  const clientsResponse = http.get(CLIENTES_URL, { headers: authHeaders });
  let clients = [];
  
  if (clientsResponse.status === 200) {
    try {
      const clientsData = JSON.parse(clientsResponse.body);
      clients = clientsData.clientes || clientsData;
      console.log(`Fetched ${clients.length} clients`);
    } catch (e) {
      console.error(`Failed to parse clients: ${e}`);
    }
  } else {
    console.error(`Failed to fetch clients: ${clientsResponse.status}`);
  }

  // Step 3: Fetch all sellers
  console.log("Fetching sellers...");
  const sellersResponse = http.get(`${VENDEDORES_URL}?page=1&page_size=100`, { headers: authHeaders });
  let sellers = [];
  
  if (sellersResponse.status === 200) {
    try {
      const sellersData = JSON.parse(sellersResponse.body);
      sellers = sellersData.data || [];
      console.log(`Fetched ${sellers.length} sellers`);
    } catch (e) {
      console.error(`Failed to parse sellers: ${e}`);
    }
  } else {
    console.error(`Failed to fetch sellers: ${sellersResponse.status}`);
    console.log(`selleers endpoint: ${VENDEDORES_URL}`);
  }

  // Step 4: Fetch inventory/products
  console.log("Fetching products from inventory...");
  const inventoryResponse = http.get(`${INVENTARIO_URL}?page=1&page_size=100`, { headers: authHeaders });
  let products = [];
  
  if (inventoryResponse.status === 200) {
    try {
      const inventoryData = JSON.parse(inventoryResponse.body);
      // Extract unique product IDs from inventory items
      const items = inventoryData.items || [];
      const productMap = new Map();
      
      items.forEach(item => {
        if (item.producto_id && item.estado === 'DISPONIBLE' && item.cantidad > 0) {
          productMap.set(item.producto_id, {
            id: item.producto_id,
            nombre: item.producto_nombre || 'Unknown',
            sku: item.producto_sku || 'Unknown'
          });
        }
      });
      
      products = Array.from(productMap.values());
      console.log(`Fetched ${products.length} available products`);
    } catch (e) {
      console.error(`Failed to parse inventory: ${e}`);
    }
  } else {
    console.error(`Failed to fetch inventory: ${inventoryResponse.status}`);
  }

  // Validate we have data
  if (clients.length === 0 || sellers.length === 0 || products.length === 0) {
    console.error(`Missing data - Clients: ${clients.length}, Sellers: ${sellers.length}, Products: ${products.length}`);
    throw new Error("Failed to fetch required data for test");
  }

  return { 
    token: token,
    clients: clients,
    sellers: sellers,
    products: products
  };
}


export default function (data) {
  // Get data from setup
  const { token, clients, sellers, products } = data;

  // Select random client, seller, and product
  const randomClient = clients[Math.floor(Math.random() * clients.length)];
  const randomSeller = sellers[Math.floor(Math.random() * sellers.length)];
  const randomProduct = products[Math.floor(Math.random() * products.length)];

  // Generate random quantity and price
  const cantidad = Math.floor(Math.random() * 10) + 1; // 1-10 units
  const precioUnitario = Math.floor(Math.random() * 1000) + 100; // 100-1100

  const payload = {
    id_cliente: randomClient.id,
    id_vendedor: randomSeller.id,
    observaciones: `Load test order - ${new Date().toISOString()}`,
    detalles: [
      {
        id_producto: randomProduct.id,
        cantidad: cantidad,
        precio_unitario: precioUnitario,
      },
    ],
  };

  const headers = {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${token}`,
  };

  const response = http.post(ORDERS_URL, JSON.stringify(payload), { headers });

  // Log response details for debugging errors
  if (response.status === 422) {
    console.log(`422 Error - Status: ${response.status}`);
    console.log(`Response Body: ${response.body}`);
    console.log(`Request Payload: ${JSON.stringify(payload, null, 2)}`);
  } else if (response.status >= 400) {
    console.log(`Error ${response.status}: ${response.body}`);
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
  });

  sleep(0.1);
}

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
  };
}
