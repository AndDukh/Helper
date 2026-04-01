"use client";

import { useEffect, useState } from "react";

const apiBase = "/api";

export default function HomePage() {
  const [title, setTitle] = useState("Weekly sync");
  const [meetingId, setMeetingId] = useState("");
  const [audioFile, setAudioFile] = useState(null);
  const [output, setOutput] = useState({ hint: "Run action to see response." });
  const [loading, setLoading] = useState(false);
  const [telegramHint, setTelegramHint] = useState("");

  useEffect(() => {
    const tg = typeof window !== "undefined" ? window.Telegram?.WebApp : null;
    if (tg) {
      tg.ready();
      tg.expand();
      setTelegramHint("Running inside Telegram WebApp.");
    } else {
      setTelegramHint("Open via Telegram bot button to enable WebApp context.");
    }
  }, []);

  async function verifyTelegram() {
    const tg = typeof window !== "undefined" ? window.Telegram?.WebApp : null;
    if (!tg?.initData) {
      setOutput({ error: "No initData: open this page from the Telegram Mini App button." });
      return;
    }
    setLoading(true);
    try {
      const response = await fetch(`${apiBase}/telegram/verify-init`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ init_data: tg.initData }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Verify failed");
      setOutput(data);
    } catch (error) {
      setOutput({ error: error.message });
    } finally {
      setLoading(false);
    }
  }

  async function postJson(path, payload) {
    const response = await fetch(`${apiBase}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Request failed");
    return data;
  }

  async function startMeeting() {
    setLoading(true);
    try {
      const data = await postJson("/meetings/start", { title });
      setMeetingId(data.id);
      setOutput(data);
    } catch (error) {
      setOutput({ error: error.message });
    } finally {
      setLoading(false);
    }
  }

  async function stopMeeting() {
    if (!meetingId) return setOutput({ error: "Meeting ID is required" });
    setLoading(true);
    try {
      const data = await postJson("/meetings/stop", { meeting_id: meetingId });
      setOutput(data);
    } catch (error) {
      setOutput({ error: error.message });
    } finally {
      setLoading(false);
    }
  }

  async function transcribeMeeting() {
    if (!meetingId) return setOutput({ error: "Meeting ID is required" });
    if (!audioFile) return setOutput({ error: "Choose an audio file first" });

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("audio", audioFile);
      const response = await fetch(`${apiBase}/meetings/${meetingId}/transcribe`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Transcribe failed");
      setOutput(data);
    } catch (error) {
      setOutput({ error: error.message });
    } finally {
      setLoading(false);
    }
  }

  async function runDemoFlow() {
    if (!meetingId) return setOutput({ error: "Meeting ID is required" });
    setLoading(true);
    try {
      const response = await fetch(`${apiBase}/meetings/${meetingId}/start-demo-flow`, {
        method: "POST",
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Demo flow failed");
      setOutput(data);
    } catch (error) {
      setOutput({ error: error.message });
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <h1>Helper Mini App Prototype</h1>
      <p>Start/stop a meeting, transcribe audio, and run demo protocol flow.</p>
      <p style={{ color: "#444" }}>{telegramHint}</p>
      <div style={{ marginBottom: 16 }}>
        <button type="button" onClick={verifyTelegram} disabled={loading}>
          Verify Telegram session
        </button>
      </div>

      <div style={{ display: "grid", gap: 10, maxWidth: 640 }}>
        <label>
          Meeting title
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            style={{ display: "block", width: "100%", marginTop: 4 }}
          />
        </label>

        <label>
          Meeting ID
          <input
            value={meetingId}
            onChange={(e) => setMeetingId(e.target.value)}
            placeholder="filled automatically after Start"
            style={{ display: "block", width: "100%", marginTop: 4 }}
          />
        </label>

        <label>
          Audio file (.mp3/.wav/.webm)
          <input
            type="file"
            onChange={(e) => setAudioFile(e.target.files?.[0] || null)}
            style={{ display: "block", width: "100%", marginTop: 4 }}
          />
        </label>

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button onClick={startMeeting} disabled={loading}>Start</button>
          <button onClick={stopMeeting} disabled={loading}>Stop</button>
          <button onClick={transcribeMeeting} disabled={loading}>Transcribe</button>
          <button onClick={runDemoFlow} disabled={loading}>Run Demo Flow</button>
        </div>
      </div>

      <h3>API output</h3>
      <pre>{JSON.stringify(output, null, 2)}</pre>
    </main>
  );
}
