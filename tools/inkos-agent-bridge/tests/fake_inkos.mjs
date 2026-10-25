#!/usr/bin/env node
// Stand-in for the `inkos` CLI: issues OpenAI-style calls the way InkOS does,
// using only the INKOS_LLM_* environment the bridge wrapper provides.
const mode = process.argv[2] ?? "stream";
if (mode === "--version") { console.log("0.0.0-fake"); process.exit(0); }
const base = process.env.INKOS_LLM_BASE_URL;
const proxyLeak = ["HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"].filter(k => process.env[k]);
console.log(JSON.stringify({ base, model: process.env.INKOS_LLM_MODEL, key: process.env.INKOS_LLM_API_KEY, proxyLeak }));

const tools = [{ type: "function", function: { name: "submit_plan", description: "Submit the chapter plan",
  parameters: { type: "object", properties: { goal: { type: "string" } }, required: ["goal"] } } }];

async function call(stream, withTools) {
  const res = await fetch(`${base}/chat/completions`, {
    method: "POST", headers: { "content-type": "application/json", authorization: `Bearer ${process.env.INKOS_LLM_API_KEY}` },
    body: JSON.stringify({ model: process.env.INKOS_LLM_MODEL, stream, max_tokens: 4000,
      ...(stream ? { stream_options: { include_usage: true } } : {}),
      ...(withTools ? { tools, tool_choice: "required" } : {}),
      messages: [{ role: "system", content: "You are the InkOS writer agent. 한국어로 집필한다." },
                 { role: "user", content: "제1화를 써라." }] }),
  });
  if (!res.ok) { console.log(JSON.stringify({ status: res.status, body: await res.text() })); return; }
  if (!stream) { const json = await res.json();
    if (json.error) { console.log(JSON.stringify({ status: 200, body: JSON.stringify(json) })); return; }
    console.log(JSON.stringify({ status: 200, message: json.choices[0].message, finish: json.choices[0].finish_reason })); return; }
  const text = await res.text();
  let content = "", toolCalls = [], finish = null, done = false, comments = 0, usage = false, error = null;
  for (const block of text.split("\n\n")) {
    if (block.startsWith(":")) { comments++; continue; }
    if (!block.startsWith("data: ")) continue;
    const data = block.slice(6);
    if (data === "[DONE]") { done = true; continue; }
    const json = JSON.parse(data);
    if (json.error) { error = json.error; continue; }
    if (json.usage) usage = true;
    const choice = json.choices?.[0];
    if (!choice) continue;
    if (choice.delta?.content) content += choice.delta.content;
    for (const tc of choice.delta?.tool_calls ?? []) toolCalls.push(tc);
    if (choice.finish_reason) finish = choice.finish_reason;
  }
  console.log(JSON.stringify({ status: 200, content, toolCalls, finish, done, comments, usage, error }));
}

if (mode === "stream") await call(true, false);
else if (mode === "buffered") await call(false, false);
else if (mode === "tools") await call(true, true);
else if (mode === "abort") {
  const ctl = new AbortController();
  setTimeout(() => ctl.abort(), 2500);
  try { await fetch(`${base}/chat/completions`, { method: "POST", signal: ctl.signal,
    body: JSON.stringify({ stream: true, messages: [{ role: "user", content: "x" }] }) }).then(r => r.text()); }
  catch { console.log("aborted"); }
}
