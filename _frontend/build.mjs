// Assembles the static files the app needs into dist/ for production.
// In dev the frontend and API run on different ports; in the built output
// the backend serves both, so the API base URL becomes same-origin "/api".
import { cpSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";

const DS_DIR = "_ds/organic-103e147d-99da-4ba2-98c9-6b3adb18baf2";
const OUT = "dist";

rmSync(OUT, { recursive: true, force: true });
mkdirSync(`${OUT}/${DS_DIR}`, { recursive: true });

cpSync("Simple CRM.dc.html", `${OUT}/index.html`);
cpSync("support.js", `${OUT}/support.js`);
cpSync("crm-tests.js", `${OUT}/crm-tests.js`);
cpSync(`${DS_DIR}/styles.css`, `${OUT}/${DS_DIR}/styles.css`);
cpSync(`${DS_DIR}/_ds_bundle.js`, `${OUT}/${DS_DIR}/_ds_bundle.js`);

const devBaseUrl = 'const DEFAULT_BASE_URL = "http://localhost:8091/api";';
const service = readFileSync("crm-service.js", "utf8");
if (!service.includes(devBaseUrl)) {
  throw new Error("crm-service.js: DEFAULT_BASE_URL not found; update build.mjs");
}
writeFileSync(
  `${OUT}/crm-service.js`,
  service.replace(devBaseUrl, 'const DEFAULT_BASE_URL = "/api";'),
);

console.log(`Built frontend into ${OUT}/`);
