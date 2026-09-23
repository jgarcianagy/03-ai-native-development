// Services layer. Every backend call in the app goes through an object shaped
// like this. `createMockService` is the in-memory implementation used by the
// test suite; `createHttpService` talks to the real FastAPI backend
// (backend/app) and returns the same method names and shapes.

export const STAGES = ["Lead", "Qualified", "Proposal", "Negotiation", "Won", "Lost"];
export const CLOSED_STAGES = ["Won", "Lost"];
export const ACTIVITY_TYPES = ["Call", "Email", "Meeting", "Note"];

const clone = (v) => (v == null ? v : JSON.parse(JSON.stringify(v)));

const CONTACT_FIELDS = [
  "name", "email", "phone", "company", "jobTitle", "address", "website", "tags",
];
const DEAL_FIELDS = ["title", "value", "stage", "contactId", "expectedClose"];

function seedData() {
  return {
    contacts: [
      { id: "c1", name: "Marisol Ferrer", email: "marisol@terracottastudio.com", phone: "+34 611 204 883", company: "Terracotta Studio", jobTitle: "Creative Director", address: "Carrer de Bailèn 92, Barcelona", website: "terracottastudio.com", tags: ["Design", "Retainer"] },
      { id: "c2", name: "Dominic Ashby", email: "d.ashby@northfieldmill.co.uk", phone: "+44 7700 145 902", company: "Northfield Mill", jobTitle: "Head of Operations", address: "Mill Lane 4, Leeds", website: "northfieldmill.co.uk", tags: ["Manufacturing"] },
      { id: "c3", name: "Aiko Tanaka", email: "aiko@sumigreen.jp", phone: "+81 90 4412 8871", company: "Sumi Green", jobTitle: "Founder", address: "2-14 Yanaka, Taito, Tokyo", website: "sumigreen.jp", tags: ["Sustainability", "Inbound"] },
      { id: "c4", name: "Peter Wienand", email: "p.wienand@hofgutbrand.de", phone: "+49 151 2244 8130", company: "Hofgut Brand", jobTitle: "Managing Partner", address: "Weinstraße 18, Mainz", website: "hofgutbrand.de", tags: ["Food & Drink", "Retainer"] },
      { id: "c5", name: "Noor Haddad", email: "noor@atlasclay.com", phone: "+971 50 771 3306", company: "Atlas Clay", jobTitle: "Brand Lead", address: "Al Quoz 3, Dubai", website: "atlasclay.com", tags: ["Design"] },
      { id: "c6", name: "Ruth Okonjo", email: "ruth@lagoscircle.ng", phone: "+234 803 118 4420", company: "Lagos Circle", jobTitle: "Programme Manager", address: "12 Kofo Abayomi, Victoria Island", website: "lagoscircle.ng", tags: ["Non-profit", "Inbound"] },
      { id: "c7", name: "Sam Barlowe", email: "sam@driftwoodgoods.com", phone: "+1 503 448 2210", company: "Driftwood Goods", jobTitle: "Owner", address: "418 SE Clay St, Portland", website: "driftwoodgoods.com", tags: ["Retail"] },
      { id: "c8", name: "Elena Kovač", email: "elena@primorje.hr", phone: "+385 91 552 7714", company: "Primorje Hotels", jobTitle: "Commercial Director", address: "Obala 11, Rijeka", website: "primorje.hr", tags: ["Hospitality", "Retail"] },
    ],
    deals: [
      { id: "d1", contactId: "c1", title: "Brand system refresh", value: 42000, stage: "Proposal", expectedClose: "2026-10-30" },
      { id: "d2", contactId: "c1", title: "Packaging retainer 2027", value: 18000, stage: "Lead", expectedClose: "2026-12-15" },
      { id: "d3", contactId: "c2", title: "Plant floor signage", value: 26500, stage: "Qualified", expectedClose: "2026-11-20" },
      { id: "d4", contactId: "c3", title: "Sustainability report design", value: 15000, stage: "Negotiation", expectedClose: "2026-09-30" },
      { id: "d5", contactId: "c4", title: "Estate label redesign", value: 31000, stage: "Won", expectedClose: "2026-08-28" },
      { id: "d6", contactId: "c5", title: "Campaign art direction", value: 22000, stage: "Lead", expectedClose: "2026-11-06" },
      { id: "d7", contactId: "c6", title: "Annual impact microsite", value: 12500, stage: "Qualified", expectedClose: "2026-10-12" },
      { id: "d8", contactId: "c7", title: "Store fit-out graphics", value: 9800, stage: "Lost", expectedClose: "2026-07-19" },
      { id: "d9", contactId: "c8", title: "Group rebrand phase 1", value: 58000, stage: "Negotiation", expectedClose: "2026-10-02" },
    ],
    activities: [
      { id: "a1", contactId: "c1", type: "Meeting", note: "Walked through the moodboards. She wants the terracotta direction taken further.", at: "2026-09-08T10:30:00Z" },
      { id: "a2", contactId: "c1", type: "Email", note: "Sent revised scope and the phase-two estimate.", at: "2026-09-09T14:05:00Z" },
      { id: "a3", contactId: "c2", type: "Call", note: "Budget sign-off sits with the board; next meeting is the 24th.", at: "2026-09-04T09:15:00Z" },
      { id: "a4", contactId: "c3", type: "Note", note: "Prefers async updates. Keep decks short.", at: "2026-08-29T08:00:00Z" },
      { id: "a5", contactId: "c4", type: "Call", note: "Agreed terms verbally. Contract to follow.", at: "2026-08-26T16:40:00Z" },
      { id: "a6", contactId: "c8", type: "Meeting", note: "Site visit in Rijeka. Four properties in scope, not two.", at: "2026-09-10T11:00:00Z" },
      { id: "a7", contactId: "c6", type: "Email", note: "Shared two reference microsites for tone.", at: "2026-09-02T13:20:00Z" },
    ],
  };
}

function pick(source, fields) {
  const out = {};
  for (const f of fields) if (source[f] !== undefined) out[f] = source[f];
  return out;
}

function normaliseTags(tags) {
  if (tags == null) return [];
  const list = Array.isArray(tags) ? tags : String(tags).split(",");
  return list.map((t) => String(t).trim()).filter(Boolean);
}

export function createMockService(options = {}) {
  const latency = options.latency == null ? 140 : options.latency;
  const db = options.data ? clone(options.data) : seedData();
  let counter = 1000;
  const id = (p) => `${p}${++counter}`;
  const wait = () => (latency ? new Promise((r) => setTimeout(r, latency)) : Promise.resolve());
  const fail = (msg) => { throw new Error(msg); };

  const contactById = (cid) => db.contacts.find((c) => c.id === cid);

  async function listContacts(query = {}) {
    await wait();
    const term = String(query.search || "").trim().toLowerCase();
    const tags = normaliseTags(query.tags);
    let rows = db.contacts.filter((c) => {
      if (term) {
        const hay = [c.name, c.email, c.company].join(" ").toLowerCase();
        if (!hay.includes(term)) return false;
      }
      if (tags.length && !tags.every((t) => c.tags.includes(t))) return false;
      return true;
    });
    rows = rows.slice().sort((a, b) => a.name.localeCompare(b.name));
    return clone(rows);
  }

  async function getContact(cid) {
    await wait();
    const c = contactById(cid);
    if (!c) fail(`No contact with id ${cid}`);
    return clone(c);
  }

  async function createContact(input = {}) {
    await wait();
    if (!String(input.name || "").trim()) fail("Contact name is required");
    if (!String(input.company || "").trim()) fail("Contact company is required");
    const record = Object.assign(
      { id: id("c"), name: "", email: "", phone: "", company: "", jobTitle: "", address: "", website: "", tags: [] },
      pick(input, CONTACT_FIELDS)
    );
    record.tags = normaliseTags(record.tags);
    db.contacts.push(record);
    return clone(record);
  }

  async function updateContact(cid, patch = {}) {
    await wait();
    const c = contactById(cid);
    if (!c) fail(`No contact with id ${cid}`);
    const next = pick(patch, CONTACT_FIELDS);
    if ("name" in next && !String(next.name).trim()) fail("Contact name is required");
    if ("company" in next && !String(next.company).trim()) fail("Contact company is required");
    if ("tags" in next) next.tags = normaliseTags(next.tags);
    Object.assign(c, next);
    return clone(c);
  }

  async function listTags() {
    await wait();
    const seen = new Set();
    for (const c of db.contacts) for (const t of c.tags) seen.add(t);
    return Array.from(seen).sort();
  }

  async function listDeals(query = {}) {
    await wait();
    let rows = db.deals;
    if (query.contactId) rows = rows.filter((d) => d.contactId === query.contactId);
    if (query.stage) rows = rows.filter((d) => d.stage === query.stage);
    return clone(rows.map((d) => Object.assign({}, d, {
      contactName: (contactById(d.contactId) || {}).name || "",
      company: (contactById(d.contactId) || {}).company || "",
    })));
  }

  async function getDeal(did) {
    await wait();
    const d = db.deals.find((x) => x.id === did);
    if (!d) fail(`No deal with id ${did}`);
    return clone(d);
  }

  async function createDeal(input = {}) {
    await wait();
    if (!input.contactId) fail("A deal must belong to a contact");
    if (!contactById(input.contactId)) fail(`No contact with id ${input.contactId}`);
    if (!String(input.title || "").trim()) fail("Deal title is required");
    const stage = input.stage || STAGES[0];
    if (!STAGES.includes(stage)) fail(`Unknown stage ${stage}`);
    const record = Object.assign(
      { id: id("d"), title: "", value: 0, stage, contactId: null, expectedClose: "" },
      pick(input, DEAL_FIELDS),
      { stage }
    );
    record.value = Number(record.value) || 0;
    db.deals.push(record);
    return clone(record);
  }

  async function updateDeal(did, patch = {}) {
    await wait();
    const d = db.deals.find((x) => x.id === did);
    if (!d) fail(`No deal with id ${did}`);
    const next = pick(patch, DEAL_FIELDS);
    if ("title" in next && !String(next.title).trim()) fail("Deal title is required");
    if ("stage" in next && !STAGES.includes(next.stage)) fail(`Unknown stage ${next.stage}`);
    if ("contactId" in next) {
      if (!next.contactId) fail("A deal must belong to a contact");
      if (!contactById(next.contactId)) fail(`No contact with id ${next.contactId}`);
    }
    if ("value" in next) next.value = Number(next.value) || 0;
    Object.assign(d, next);
    return clone(d);
  }

  // Stage changes are manual and trigger nothing else.
  async function moveDeal(did, stage) {
    return updateDeal(did, { stage });
  }

  async function listActivities(cid) {
    await wait();
    if (!cid) fail("Activities are listed per contact");
    const rows = db.activities
      .filter((a) => a.contactId === cid)
      .slice()
      .sort((a, b) => (a.at < b.at ? 1 : -1));
    return clone(rows);
  }

  async function createActivity(input = {}) {
    await wait();
    if (!input.contactId) fail("An activity must belong to a contact");
    if (!contactById(input.contactId)) fail(`No contact with id ${input.contactId}`);
    if (!ACTIVITY_TYPES.includes(input.type)) fail(`Unknown activity type ${input.type}`);
    if (!String(input.note || "").trim()) fail("Activity note is required");
    const record = {
      id: id("a"),
      contactId: input.contactId,
      type: input.type,
      note: String(input.note).trim(),
      at: input.at || new Date().toISOString(),
    };
    db.activities.push(record);
    return clone(record);
  }

  async function getPipeline() {
    await wait();
    return { stages: STAGES.slice() };
  }

  return {
    kind: "mock",
    getPipeline,
    listContacts, getContact, createContact, updateContact, listTags,
    listDeals, getDeal, createDeal, updateDeal, moveDeal,
    listActivities, createActivity,
  };
}

// The backend requires a bearer token on writes (POST/PATCH) but the frontend
// has no login screen, so the client logs in once with the seeded admin user
// and attaches the token itself — an implementation detail, not a UI flow.
const DEFAULT_BASE_URL = "http://localhost:8091/api";
const DEFAULT_CREDENTIALS = { username: "admin", password: "admin123" };

export function createHttpService(options = {}) {
  const baseUrl = (options.baseUrl || DEFAULT_BASE_URL).replace(/\/$/, "");
  const credentials = options.credentials || DEFAULT_CREDENTIALS;
  const fetchFn = options.fetch || ((...args) => fetch(...args));
  let tokenPromise = null;

  function getToken() {
    if (!tokenPromise) {
      tokenPromise = request("/auth/login", { method: "POST", body: credentials })
        .then((t) => t.access_token)
        .catch((err) => { tokenPromise = null; throw err; });
    }
    return tokenPromise;
  }

  async function request(path, { method = "GET", body, auth = false, retried = false } = {}) {
    const headers = {};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (auth) headers.Authorization = `Bearer ${await getToken()}`;
    const res = await fetchFn(`${baseUrl}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    // Tokens expire server-side; log in again once and repeat the request.
    if (res.status === 401 && auth && !retried) {
      tokenPromise = null;
      return request(path, { method, body, auth, retried: true });
    }
    const data = res.status === 204 ? null : await res.json().catch(() => null);
    if (!res.ok) throw new Error((data && data.error) || `Request failed with status ${res.status}`);
    return data;
  }

  function query(params) {
    const usp = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v == null || v === "" || (Array.isArray(v) && !v.length)) continue;
      usp.set(k, Array.isArray(v) ? v.join(",") : v);
    }
    const s = usp.toString();
    return s ? `?${s}` : "";
  }

  const enc = encodeURIComponent;

  async function getPipeline() {
    return request("/pipeline");
  }

  async function listContacts(query_ = {}) {
    return request(`/contacts${query({ search: query_.search, tags: query_.tags })}`);
  }

  async function getContact(cid) {
    return request(`/contacts/${enc(cid)}`);
  }

  async function createContact(input = {}) {
    return request("/contacts", { method: "POST", body: input, auth: true });
  }

  async function updateContact(cid, patch = {}) {
    return request(`/contacts/${enc(cid)}`, { method: "PATCH", body: patch, auth: true });
  }

  async function listTags() {
    return request("/tags");
  }

  async function listDeals(query_ = {}) {
    return request(`/deals${query({ contactId: query_.contactId, stage: query_.stage })}`);
  }

  async function getDeal(did) {
    return request(`/deals/${enc(did)}`);
  }

  async function createDeal(input = {}) {
    return request("/deals", { method: "POST", body: input, auth: true });
  }

  async function updateDeal(did, patch = {}) {
    return request(`/deals/${enc(did)}`, { method: "PATCH", body: patch, auth: true });
  }

  // Stage changes are manual and trigger nothing else.
  async function moveDeal(did, stage) {
    return updateDeal(did, { stage });
  }

  async function listActivities(cid) {
    return request(`/contacts/${enc(cid)}/activities`);
  }

  async function createActivity(input = {}) {
    return request("/activities", { method: "POST", body: input, auth: true });
  }

  return {
    kind: "http",
    getPipeline,
    listContacts, getContact, createContact, updateContact, listTags,
    listDeals, getDeal, createDeal, updateDeal, moveDeal,
    listActivities, createActivity,
  };
}
