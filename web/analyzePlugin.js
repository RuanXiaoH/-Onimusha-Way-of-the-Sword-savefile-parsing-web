import { spawn } from "node:child_process";
import { readFileSync } from "node:fs";
import { mkdtemp, writeFile, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const MAX_BYTES = 12 * 1024 * 1024;
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SCRIPT = path.join(ROOT, "scripts", "analyze_bin.py");

function readBody(req, limit) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let total = 0;
    req.on("data", (chunk) => {
      total += chunk.length;
      if (total > limit) {
        reject(Object.assign(new Error("文件太大，请提交 data001Slot.bin"), { code: 413 }));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on("end", () => resolve(Buffer.concat(chunks)));
    req.on("error", reject);
  });
}

function runPython(binPath) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.env.PYTHON || "python", [SCRIPT, "--bin", binPath], {
      cwd: ROOT,
      env: { ...process.env, PYTHONIOENCODING: "utf-8" },
      windowsHide: true,
    });
    let out = "";
    let err = "";
    child.stdout.on("data", (d) => {
      out += d.toString("utf8");
    });
    child.stderr.on("data", (d) => {
      err += d.toString("utf8");
    });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) {
        resolve(out);
        return;
      }
      const message = (err || out || `解析失败，退出码 ${code}`).trim();
      reject(new Error(message.split(/\r?\n/).filter(Boolean).pop() || message));
    });
  });
}

function sendJson(res, status, body) {
  const text = JSON.stringify(body);
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.end(text);
}

function parseSaveJson(out) {
  const start = out.indexOf("{");
  const end = out.lastIndexOf("}");
  if (start < 0 || end <= start) {
    throw new Error("解析结果不是 JSON");
  }
  const save = JSON.parse(out.slice(start, end + 1));
  if (save && typeof save === "object") {
    delete save._source;
  }
  if (!save?.slots?.length) {
    throw new Error("没有占用中的存档栏位");
  }
  return save;
}

function scrubError(message) {
  let text = String(message || "解析失败");
  try {
    const sidPath = path.join(ROOT, "scripts", "steamid.txt");
    const sid = readFileSync(sidPath, "utf8").trim().split(/\r?\n/)[0]?.trim();
    if (sid) text = text.split(sid).join("");
  } catch {
    // SteamID 只用于脱敏，读不到就原样返回
  }
  return text.replace(/\s+/g, " ").trim() || "解析失败";
}

async function handleAnalyze(req, res) {
  if (req.method === "OPTIONS") {
    res.statusCode = 204;
    res.end();
    return;
  }
  if (req.method !== "POST") {
    sendJson(res, 405, { error: "请用 POST 提交存档" });
    return;
  }
  let tmpDir;
  try {
    const raw = await readBody(req, MAX_BYTES);
    if (!raw.length) {
      sendJson(res, 400, { error: "没有读到文件" });
      return;
    }
    const filename = decodeURIComponent(req.headers["x-filename"] || "data001Slot.bin");
    tmpDir = await mkdtemp(path.join(os.tmpdir(), "oni-upload-"));
    const binPath = path.join(tmpDir, filename.replace(/[^\w.\u4e00-\u9fff-]+/g, "_") || "data001Slot.bin");
    await writeFile(binPath, raw);
    const out = await runPython(binPath);
    const save = parseSaveJson(out);
    sendJson(res, 200, {
      save,
      filename,
      uploadedAt: new Date().toISOString(),
    });
  } catch (err) {
    const code = err.code === 413 ? 413 : 500;
    sendJson(res, code, { error: scrubError(err.message) });
  } finally {
    if (tmpDir) {
      await rm(tmpDir, { recursive: true, force: true }).catch(() => {});
    }
  }
}

export function analyzeSavePlugin() {
  const middleware = (req, res, next) => {
    const url = req.url?.split("?")[0];
    if (url !== "/api/analyze") {
      next();
      return;
    }
    handleAnalyze(req, res);
  };
  return {
    name: "analyze-save",
    configureServer(server) {
      server.middlewares.use(middleware);
    },
    configurePreviewServer(server) {
      server.middlewares.use(middleware);
    },
  };
}
