import { spawn } from "node:child_process";
import { setTimeout } from "node:timers/promises";
import { fileURLToPath } from "node:url";

const cwd = fileURLToPath(new URL(".", import.meta.url));
const child = spawn(process.execPath, [
  "node_modules/@stoplight/prism-cli/dist/index.js", "mock", "openapi.json",
  "--host", "127.0.0.1", "--port", "4019",
], { cwd, stdio: ["ignore", "pipe", "pipe"], windowsHide: true });
let output = "";
child.stdout.on("data", chunk => { output = (output + chunk).slice(-8000); });
child.stderr.on("data", chunk => { output = (output + chunk).slice(-8000); });
let failure;
child.on("error", error => { failure = error; });
try {
  const deadline = Date.now() + 30000;
  let ready = false;
  while (Date.now() < deadline) {
    if (failure) throw failure;
    if (child.exitCode !== null) throw new Error(`Prism exited: ${output}`);
    try {
      const response = await fetch("http://127.0.0.1:4019/healthz", {
        signal: AbortSignal.timeout(1000),
      });
      if (response.status !== 200) throw new Error(`Mock returned ${response.status}`);
      await response.json();
      ready = true;
      break;
    } catch {
      await setTimeout(200);
    }
  }
  if (!ready) throw new Error(`Prism did not become ready: ${output}`);
  console.log("Prism loaded the pinned OpenAPI contract and served JSON.");
} finally {
  child.kill();
  await Promise.race([
    new Promise(resolve => child.once("exit", resolve)),
    setTimeout(3000).then(() => child.kill("SIGKILL")),
  ]);
}
