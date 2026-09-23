// Test suite for the services layer. Each test gets a fresh zero-latency mock.
import { createMockService, createHttpService, STAGES, ACTIVITY_TYPES } from "./crm-service.js";

const fresh = () => createMockService({ latency: 0 });

function eq(actual, expected, what) {
  if (actual !== expected) throw new Error(`${what}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
}
function ok(cond, what) {
  if (!cond) throw new Error(what);
}
async function throws(fn, what) {
  try { await fn(); } catch (e) { return e; }
  throw new Error(`${what}: expected a rejection, none thrown`);
}

export const tests = [
  { group: "Pipeline", name: "has one pipeline with Won and Lost as stages", fn: async () => {
    const { stages } = await fresh().getPipeline();
    eq(stages.join(" > "), STAGES.join(" > "), "stage order");
    ok(stages.includes("Won") && stages.includes("Lost"), "Won and Lost are stages");
  } },

  { group: "Contacts", name: "lists contacts alphabetically", fn: async () => {
    const rows = await fresh().listContacts();
    ok(rows.length >= 8, "seed has at least 8 contacts");
    const names = rows.map((r) => r.name);
    eq(names.join("|"), names.slice().sort((a, b) => a.localeCompare(b)).join("|"), "sorted by name");
  } },

  { group: "Contacts", name: "searches by name, email and company", fn: async () => {
    const s = fresh();
    eq((await s.listContacts({ search: "marisol" }))[0].name, "Marisol Ferrer", "by name");
    eq((await s.listContacts({ search: "northfieldmill.co.uk" }))[0].company, "Northfield Mill", "by email");
    eq((await s.listContacts({ search: "sumi green" }))[0].name, "Aiko Tanaka", "by company");
    eq((await s.listContacts({ search: "zzzz" })).length, 0, "no match");
  } },

  { group: "Contacts", name: "filters by tags (all selected tags must match)", fn: async () => {
    const s = fresh();
    const design = await s.listContacts({ tags: ["Design"] });
    ok(design.length === 2, `two Design contacts, got ${design.length}`);
    ok(design.every((c) => c.tags.includes("Design")), "every row carries the tag");
    const both = await s.listContacts({ tags: ["Design", "Retainer"] });
    eq(both.length, 1, "intersection of two tags");
  } },

  { group: "Contacts", name: "search and tag filter combine", fn: async () => {
    const rows = await fresh().listContacts({ search: "e", tags: ["Retainer"] });
    ok(rows.every((c) => c.tags.includes("Retainer")), "tag holds");
    ok(rows.every((c) => [c.name, c.email, c.company].join(" ").toLowerCase().includes("e")), "search holds");
  } },

  { group: "Contacts", name: "creates a contact and exposes its tag", fn: async () => {
    const s = fresh();
    const c = await s.createContact({ name: "Iris Vandal", company: "Vandal Press", tags: " Print , Inbound " });
    ok(c.id, "id assigned");
    eq(c.tags.join(","), "Print,Inbound", "tags trimmed from a string");
    eq((await s.getContact(c.id)).name, "Iris Vandal", "readable back");
    ok((await s.listTags()).includes("Print"), "new tag in the tag list");
  } },

  { group: "Contacts", name: "requires a name and a company", fn: async () => {
    const s = fresh();
    await throws(() => s.createContact({ company: "X" }), "missing name");
    await throws(() => s.createContact({ name: "  " , company: "X" }), "blank name");
    await throws(() => s.createContact({ name: "Y" }), "missing company");
  } },

  { group: "Contacts", name: "edits a contact without touching other fields", fn: async () => {
    const s = fresh();
    const before = await s.getContact("c2");
    const after = await s.updateContact("c2", { jobTitle: "Operations Director" });
    eq(after.jobTitle, "Operations Director", "patched field");
    eq(after.email, before.email, "untouched field");
    await throws(() => s.updateContact("nope", { jobTitle: "x" }), "unknown contact");
  } },

  { group: "Deals", name: "every deal belongs to a contact", fn: async () => {
    const s = fresh();
    const deals = await s.listDeals();
    const contacts = await s.listContacts();
    const ids = new Set(contacts.map((c) => c.id));
    ok(deals.every((d) => ids.has(d.contactId)), "all deals resolve to a contact");
    ok(deals.every((d) => d.contactName), "list view carries the contact name");
  } },

  { group: "Deals", name: "rejects a deal with no contact or a bad one", fn: async () => {
    const s = fresh();
    await throws(() => s.createDeal({ title: "Orphan" }), "no contact");
    await throws(() => s.createDeal({ title: "Ghost", contactId: "c999" }), "unknown contact");
    await throws(() => s.createDeal({ contactId: "c1" }), "no title");
  } },

  { group: "Deals", name: "creates a deal from a contact, defaulting to the first stage", fn: async () => {
    const s = fresh();
    const d = await s.createDeal({ contactId: "c3", title: "Report vol. 2", value: "7500" });
    eq(d.stage, STAGES[0], "default stage");
    eq(d.value, 7500, "value coerced to a number");
    const forContact = await s.listDeals({ contactId: "c3" });
    ok(forContact.some((x) => x.id === d.id), "appears on the contact");
  } },

  { group: "Deals", name: "moves between stages manually, including Won and Lost", fn: async () => {
    const s = fresh();
    let d = await s.moveDeal("d1", "Negotiation");
    eq(d.stage, "Negotiation", "moved forward");
    d = await s.moveDeal("d1", "Won");
    eq(d.stage, "Won", "won is just a stage");
    d = await s.moveDeal("d1", "Lead");
    eq(d.stage, "Lead", "can move back out of Won");
    await throws(() => s.moveDeal("d1", "Archived"), "unknown stage");
  } },

  { group: "Deals", name: "a stage change triggers nothing else", fn: async () => {
    const s = fresh();
    const before = await s.getDeal("d3");
    const actsBefore = await s.listActivities("c2");
    const after = await s.moveDeal("d3", "Won");
    eq(after.title, before.title, "title unchanged");
    eq(after.value, before.value, "value unchanged");
    eq(after.expectedClose, before.expectedClose, "close date unchanged");
    eq((await s.listActivities("c2")).length, actsBefore.length, "no activity logged");
  } },

  { group: "Deals", name: "groups by stage for the pipeline view", fn: async () => {
    const s = fresh();
    const { stages } = await s.getPipeline();
    const all = await s.listDeals();
    let total = 0;
    for (const st of stages) {
      const rows = await s.listDeals({ stage: st });
      ok(rows.every((d) => d.stage === st), `${st} column is pure`);
      total += rows.length;
    }
    eq(total, all.length, "every deal sits in exactly one column");
  } },

  { group: "Activities", name: "supports Call, Email, Meeting and Note", fn: async () => {
    const s = fresh();
    eq(ACTIVITY_TYPES.join(","), "Call,Email,Meeting,Note", "type list");
    for (const t of ACTIVITY_TYPES) {
      const a = await s.createActivity({ contactId: "c5", type: t, note: `${t} logged` });
      eq(a.type, t, `created ${t}`);
    }
    eq((await s.listActivities("c5")).length, 4, "all four on the contact");
  } },

  { group: "Activities", name: "belongs to a contact and shows newest first", fn: async () => {
    const s = fresh();
    await throws(() => s.createActivity({ type: "Call", note: "x" }), "no contact");
    await throws(() => s.createActivity({ contactId: "c1", type: "Fax", note: "x" }), "bad type");
    await throws(() => s.createActivity({ contactId: "c1", type: "Call", note: " " }), "blank note");
    const rows = await s.listActivities("c1");
    ok(rows.length >= 2, "seeded history");
    ok(rows[0].at >= rows[1].at, "newest first");
    ok(rows.every((a) => a.contactId === "c1"), "scoped to the contact");
  } },

  { group: "Activities", name: "a new activity lands at the top of the history", fn: async () => {
    const s = fresh();
    const a = await s.createActivity({ contactId: "c1", type: "Note", note: "Sent the invoice." });
    eq((await s.listActivities("c1"))[0].id, a.id, "top of the list");
  } },

  { group: "Isolation", name: "reads return copies, not live records", fn: async () => {
    const s = fresh();
    const c = await s.getContact("c1");
    c.name = "Mutated";
    c.tags.push("Hacked");
    eq((await s.getContact("c1")).name, "Marisol Ferrer", "name intact");
    ok(!(await s.getContact("c1")).tags.includes("Hacked"), "tags intact");
  } },

  { group: "HTTP", name: "logs in again once when a token has expired", fn: async () => {
    const calls = [];
    let logins = 0;
    const json = (status, body) => ({ status, ok: status < 400, json: async () => body });
    const fakeFetch = async (url, init) => {
      calls.push(`${init.method} ${url.replace("http://api.test", "")}`);
      if (url.endsWith("/auth/login")) return json(200, { access_token: `t${++logins}` });
      if (init.headers.Authorization === "Bearer t1") return json(401, { detail: "Invalid or expired token" });
      return json(201, { id: "c1", name: "Retried" });
    };
    const s = createHttpService({ baseUrl: "http://api.test", fetch: fakeFetch });
    eq((await s.createContact({ name: "Retried", company: "R Co" })).name, "Retried", "request succeeds after re-login");
    eq(calls.join(", "), "POST /auth/login, POST /contacts, POST /auth/login, POST /contacts", "one re-login, one retry");
  } },

  { group: "Isolation", name: "two service instances do not share state", fn: async () => {
    const a = fresh();
    const b = fresh();
    await a.createContact({ name: "Only In A", company: "A Co" });
    eq((await b.listContacts({ search: "Only In A" })).length, 0, "b unaffected");
  } },
];

export async function runTests() {
  const out = [];
  for (const t of tests) {
    const started = performance.now();
    try {
      await t.fn();
      out.push({ group: t.group, name: t.name, pass: true, ms: performance.now() - started });
    } catch (e) {
      out.push({ group: t.group, name: t.name, pass: false, error: e.message, ms: performance.now() - started });
    }
  }
  return out;
}
