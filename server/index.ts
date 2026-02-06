import { spawn } from "child_process";
import path from "path";

const pythonProcess = spawn("python", [path.resolve("talk.py")], {
  stdio: "inherit",
  env: { ...process.env },
});

pythonProcess.on("error", (err) => {
  console.error("Failed to start Python server:", err);
  process.exit(1);
});

pythonProcess.on("exit", (code) => {
  console.log(`Python server exited with code ${code}`);
  process.exit(code ?? 1);
});

process.on("SIGTERM", () => pythonProcess.kill("SIGTERM"));
process.on("SIGINT", () => pythonProcess.kill("SIGINT"));
