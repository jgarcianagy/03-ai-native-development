// Runs crm-tests.js (the suite behind the in-app "Tests" tab) under Node,
// so CI can check the services layer without a browser.
import { runTests } from "./crm-tests.js";

const results = await runTests();
for (const r of results) {
  const line = `${r.pass ? "ok  " : "FAIL"} ${r.group} › ${r.name}`;
  console.log(r.pass ? line : `${line}\n     ${r.error}`);
}
const failed = results.filter((r) => !r.pass).length;
console.log(`\n${results.length - failed} of ${results.length} passing`);
process.exit(failed ? 1 : 0);
