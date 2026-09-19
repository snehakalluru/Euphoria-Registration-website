const BACKEND_URL = (process.env.BACKEND_URL || process.env.REACT_APP_BACKEND_URL || "").replace(/\/+$/, "");

const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "content-length",
  "host",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", (chunk) => chunks.push(chunk));
    req.on("end", () => resolve(Buffer.concat(chunks)));
    req.on("error", reject);
  });
}

function copyResponseHeaders(source, res) {
  source.headers.forEach((value, key) => {
    if (!HOP_BY_HOP_HEADERS.has(key.toLowerCase())) {
      res.setHeader(key, value);
    }
  });
}

export default async function handler(req, res) {
  if (req.method === "OPTIONS") {
    res.setHeader("Access-Control-Allow-Origin", req.headers.origin || "*");
    res.setHeader("Access-Control-Allow-Methods", "GET,POST,PUT,PATCH,DELETE,OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", req.headers["access-control-request-headers"] || "Content-Type, Authorization");
    return res.status(204).end();
  }

  if (!BACKEND_URL) {
    return res.status(500).json({
      detail: {
        code: "BACKEND_URL_NOT_CONFIGURED",
        message: "Set BACKEND_URL to your FastAPI backend URL in Vercel and redeploy.",
      },
    });
  }

  const path = Array.isArray(req.query.path) ? req.query.path.join("/") : req.query.path || "";
  const queryIndex = req.url.indexOf("?");
  const query = queryIndex >= 0 ? req.url.slice(queryIndex) : "";
  const target = `${BACKEND_URL}/api/${path}${query}`;
  const body = ["GET", "HEAD"].includes(req.method) ? undefined : await readBody(req);
  const headers = {};

  for (const [key, value] of Object.entries(req.headers)) {
    if (!HOP_BY_HOP_HEADERS.has(key.toLowerCase()) && value !== undefined) {
      headers[key] = Array.isArray(value) ? value.join(", ") : value;
    }
  }

  try {
    const response = await fetch(target, {
      method: req.method,
      headers,
      body,
      redirect: "manual",
    });
    const buffer = Buffer.from(await response.arrayBuffer());
    copyResponseHeaders(response, res);
    res.status(response.status).send(buffer);
  } catch {
    res.status(502).json({
      detail: {
        code: "BACKEND_UNREACHABLE",
        message: "The backend could not be reached from the Vercel proxy.",
      },
    });
  }
}
