# AI Orchestrator Skeletons (Node / Nest / FastAPI)

This document contains minimal skeletons for provider routing:
- local `ollama`
- external `kimi`
- single orchestration endpoint

## FastAPI (already integrated in this repository)

Use endpoint:
- `POST /ai/orchestrate`

Environment variables:
- `OLLAMA_BASE_URL` (default `http://localhost:11434`)
- `OLLAMA_CHAT_MODEL` (default `llama3.3:latest`)
- `OLLAMA_TODO_MODEL` (default `phi3:mini`)
- `KIMI_API_KEY`
- `KIMI_API_BASE_URL` (default `https://api.moonshot.ai/v1`)
- `KIMI_MODEL` (default `moonshot-v1-8k`)

## Node (Express) skeleton

```js
import express from "express";
import fetch from "node-fetch";

const app = express();
app.use(express.json());

const OLLAMA_BASE_URL = process.env.OLLAMA_BASE_URL || "http://localhost:11434";
const OLLAMA_MODEL = process.env.OLLAMA_MODEL || "qwen2.5:7b-instruct";
const KIMI_API_KEY = process.env.KIMI_API_KEY || "";
const KIMI_API_BASE_URL = process.env.KIMI_API_BASE_URL || "https://api.moonshot.ai/v1";
const KIMI_MODEL = process.env.KIMI_MODEL || "moonshot-v1-8k";

function decideProvider({ task_type, priority, prompt, force_provider }) {
  if (force_provider === "ollama" || force_provider === "kimi") return force_provider;
  const lowered = (prompt || "").toLowerCase();
  if ((task_type === "analysis" || task_type === "report") && priority === "high") return "kimi";
  if (["research", "benchmark", "long context", "strategy"].some((k) => lowered.includes(k))) return "kimi";
  return "ollama";
}

async function callOllama(payload) {
  const res = await fetch(`${OLLAMA_BASE_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: OLLAMA_MODEL,
      stream: false,
      messages: payload.messages,
      options: { temperature: 0.2 },
    }),
  });
  if (!res.ok) throw new Error(`Ollama failed: ${res.status}`);
  return res.json();
}

async function callKimi(payload) {
  const res = await fetch(`${KIMI_API_BASE_URL}/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${KIMI_API_KEY}`,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Kimi failed: ${res.status}`);
  return res.json();
}

app.post("/ai/orchestrate", async (req, res) => {
  const { task_type = "analysis", prompt, context = {}, priority = "normal", force_provider = null } = req.body;
  const provider = decideProvider({ task_type, priority, prompt, force_provider });

  try {
    if (provider === "kimi") {
      const data = await callKimi({
        model: KIMI_MODEL,
        temperature: 0.2,
        messages: [
          { role: "system", content: "Return JSON: summary, steps, risks, report_markdown." },
          { role: "user", content: JSON.stringify({ task_type, prompt, context }) },
        ],
      });
      return res.json({ provider_used: "kimi", result: data });
    }

    const data = await callOllama({
      messages: [
        { role: "system", content: "Return JSON: summary, steps, risks, report_markdown." },
        { role: "user", content: JSON.stringify({ task_type, prompt, context }) },
      ],
    });
    return res.json({ provider_used: "ollama", result: data });
  } catch (error) {
    return res.status(502).json({ error: String(error) });
  }
});

app.listen(8000);
```

## Nest skeleton

```ts
// ai.module.ts
import { Module } from "@nestjs/common";
import { HttpModule } from "@nestjs/axios";
import { AiController } from "./ai.controller";
import { AiService } from "./ai.service";

@Module({
  imports: [HttpModule],
  controllers: [AiController],
  providers: [AiService],
})
export class AiModule {}
```

```ts
// ai.controller.ts
import { Body, Controller, Post } from "@nestjs/common";
import { AiService } from "./ai.service";

@Controller("ai")
export class AiController {
  constructor(private readonly aiService: AiService) {}

  @Post("orchestrate")
  orchestrate(@Body() body: any) {
    return this.aiService.orchestrate(body);
  }
}
```

```ts
// ai.service.ts
import { Injectable } from "@nestjs/common";
import { HttpService } from "@nestjs/axios";
import { firstValueFrom } from "rxjs";

@Injectable()
export class AiService {
  constructor(private readonly http: HttpService) {}

  private decideProvider(payload: any): "ollama" | "kimi" {
    if (payload.force_provider === "ollama" || payload.force_provider === "kimi") return payload.force_provider;
    const prompt = String(payload.prompt || "").toLowerCase();
    if ((payload.task_type === "analysis" || payload.task_type === "report") && payload.priority === "high") return "kimi";
    if (["research", "benchmark", "long context", "strategy"].some((k) => prompt.includes(k))) return "kimi";
    return "ollama";
  }

  async orchestrate(payload: any) {
    const provider = this.decideProvider(payload);
    if (provider === "kimi") {
      const response = await firstValueFrom(
        this.http.post(
          `${process.env.KIMI_API_BASE_URL || "https://api.moonshot.ai/v1"}/chat/completions`,
          {
            model: process.env.KIMI_MODEL || "moonshot-v1-8k",
            temperature: 0.2,
            messages: [
              { role: "system", content: "Return JSON: summary, steps, risks, report_markdown." },
              { role: "user", content: JSON.stringify(payload) },
            ],
          },
          {
            headers: { Authorization: `Bearer ${process.env.KIMI_API_KEY}` },
          },
        ),
      );
      return { provider_used: "kimi", result: response.data };
    }

    const response = await firstValueFrom(
      this.http.post(`${process.env.OLLAMA_BASE_URL || "http://localhost:11434"}/api/chat`, {
        model: process.env.OLLAMA_MODEL || "qwen2.5:7b-instruct",
        stream: false,
        messages: [
          { role: "system", content: "Return JSON: summary, steps, risks, report_markdown." },
          { role: "user", content: JSON.stringify(payload) },
        ],
      }),
    );
    return { provider_used: "ollama", result: response.data };
  }
}
```
