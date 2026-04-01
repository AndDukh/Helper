"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const apiBase = "/api";

function formatTime(totalSeconds) {
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function pickMimeType() {
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4",
  ];
  if (typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported) {
    for (const t of candidates) {
      if (MediaRecorder.isTypeSupported(t)) return t;
    }
  }
  return "";
}

export default function HomePage() {
  const [title, setTitle] = useState("Еженедельная встреча");
  const [meetingId, setMeetingId] = useState("");
  const [audioFile, setAudioFile] = useState(null);
  const [output, setOutput] = useState(null);
  const [loading, setLoading] = useState(false);
  const [telegramHint, setTelegramHint] = useState("");

  const [recState, setRecState] = useState("idle");
  const [elapsed, setElapsed] = useState(0);
  const [recordedBlob, setRecordedBlob] = useState(null);
  const [recError, setRecError] = useState("");

  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const tickRef = useRef(null);
  const discardRecordingRef = useRef(false);

  useEffect(() => {
    const tg = typeof window !== "undefined" ? window.Telegram?.WebApp : null;
    if (tg) {
      tg.ready();
      tg.expand();
      setTelegramHint("Открыто в Telegram — доступен контекст Mini App.");
      const p = tg.themeParams;
      if (p?.bg_color) document.documentElement.style.setProperty("--bg", p.bg_color);
      if (p?.secondary_bg_color) {
        document.documentElement.style.setProperty("--bg-card", p.secondary_bg_color);
      }
      if (p?.text_color) document.documentElement.style.setProperty("--text", p.text_color);
      if (p?.hint_color) document.documentElement.style.setProperty("--text-muted", p.hint_color);
      if (p?.link_color) document.documentElement.style.setProperty("--accent", p.link_color);
    } else {
      setTelegramHint("Локальный режим. Для Telegram нужен HTTPS-туннель (см. README).");
    }
  }, []);

  useEffect(() => {
    return () => {
      if (tickRef.current) clearInterval(tickRef.current);
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  const stopTick = useCallback(() => {
    if (tickRef.current) {
      clearInterval(tickRef.current);
      tickRef.current = null;
    }
  }, []);

  const startRecording = async () => {
    setRecError("");
    setRecordedBlob(null);
    setAudioFile(null);
    chunksRef.current = [];
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      streamRef.current = stream;
      const mimeType = pickMimeType();
      const options = mimeType ? { mimeType } : undefined;
      const mr = new MediaRecorder(stream, options);
      mediaRecorderRef.current = mr;
      mr.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunksRef.current.push(e.data);
      };
      mr.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
        mediaRecorderRef.current = null;
        stopTick();
        if (discardRecordingRef.current) {
          discardRecordingRef.current = false;
          chunksRef.current = [];
          setRecordedBlob(null);
          setRecState("idle");
          setElapsed(0);
          return;
        }
        const type = mr.mimeType || mimeType || "audio/webm";
        const blob = new Blob(chunksRef.current, { type });
        setRecordedBlob(blob);
        setRecState("stopped");
      };
      mr.start(1000);
      setRecState("recording");
      setElapsed(0);
      stopTick();
      tickRef.current = setInterval(() => setElapsed((e) => e + 1), 1000);
    } catch (e) {
      setRecError(e?.message || "Не удалось получить доступ к микрофону.");
      setRecState("idle");
    }
  };

  const stopRecording = () => {
    const mr = mediaRecorderRef.current;
    if (mr && mr.state !== "inactive") {
      mr.stop();
    }
    stopTick();
  };

  const discardRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      discardRecordingRef.current = true;
      mediaRecorderRef.current.stop();
      setRecError("");
      return;
    }
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    mediaRecorderRef.current = null;
    chunksRef.current = [];
    setRecordedBlob(null);
    setRecState("idle");
    setElapsed(0);
    stopTick();
    setRecError("");
  };

  async function verifyTelegram() {
    const tg = typeof window !== "undefined" ? window.Telegram?.WebApp : null;
    if (!tg?.initData) {
      setOutput({ error: "Нет initData — откройте приложение кнопкой Mini App в боте." });
      return;
    }
    setLoading(true);
    setOutput(null);
    try {
      const response = await fetch(`${apiBase}/telegram/verify-init`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ init_data: tg.initData }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Ошибка проверки");
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
    if (!response.ok) throw new Error(data.detail || "Запрос не выполнен");
    return data;
  }

  async function startMeeting() {
    setLoading(true);
    setOutput(null);
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
    if (!meetingId) {
      setOutput({ error: "Сначала создайте встречу (Старт)." });
      return;
    }
    setLoading(true);
    setOutput(null);
    try {
      const data = await postJson("/meetings/stop", { meeting_id: meetingId });
      setOutput(data);
    } catch (error) {
      setOutput({ error: error.message });
    } finally {
      setLoading(false);
    }
  }

  function buildAudioFileForUpload() {
    if (recordedBlob) {
      const ext = recordedBlob.type.includes("webm") ? "webm" : recordedBlob.type.includes("mp4") ? "m4a" : "webm";
      return new File([recordedBlob], `recording.${ext}`, { type: recordedBlob.type || "audio/webm" });
    }
    return audioFile;
  }

  async function transcribeMeeting() {
    if (!meetingId) {
      setOutput({ error: "Сначала создайте встречу (Старт)." });
      return;
    }
    const file = buildAudioFileForUpload();
    if (!file) {
      setOutput({ error: "Запишите аудио диктофоном или выберите файл." });
      return;
    }
    setLoading(true);
    setOutput(null);
    try {
      const formData = new FormData();
      formData.append("audio", file);
      const response = await fetch(`${apiBase}/meetings/${meetingId}/transcribe`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Транскрибация не удалась");
      setOutput(data);
    } catch (error) {
      setOutput({ error: error.message });
    } finally {
      setLoading(false);
    }
  }

  async function runDemoFlow() {
    if (!meetingId) {
      setOutput({ error: "Сначала создайте встречу (Старт)." });
      return;
    }
    setLoading(true);
    setOutput(null);
    try {
      const response = await fetch(`${apiBase}/meetings/${meetingId}/start-demo-flow`, {
        method: "POST",
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Demo flow не выполнен");
      setOutput(data);
    } catch (error) {
      setOutput({ error: error.message });
    } finally {
      setLoading(false);
    }
  }

  const outputIsError = output && typeof output.error === "string";

  return (
    <div className="app-shell">
      <header className="app-header">
        <p className="app-header__eyebrow">Helper</p>
        <h1 className="app-header__title">Встречи и протокол</h1>
        <p className="app-header__subtitle">
          Диктофон, расшифровка и черновик протокола в одном месте.
        </p>
        <div className={`badge ${recState === "recording" ? "badge--live" : ""}`}>
          {recState === "recording" && <span className="badge__dot" aria-hidden />}
          {telegramHint}
        </div>
      </header>

      <section className="card">
        <h2 className="card__title">Telegram</h2>
        <p className="card__desc">Проверка подлинности сессии Mini App (после открытия из бота).</p>
        <div className="btn-row">
          <button type="button" className="btn btn--ghost" onClick={verifyTelegram} disabled={loading}>
            Проверить сессию
          </button>
        </div>
      </section>

      <section className="card">
        <h2 className="card__title">Встреча</h2>
        <p className="card__desc">Создайте встречу, затем запишите звук или загрузите файл.</p>
        <div className="field">
          <label htmlFor="title">Название</label>
          <input
            id="title"
            className="input"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Например: Синк с командой"
          />
        </div>
        <div className="field">
          <label htmlFor="mid">ID встречи</label>
          <input
            id="mid"
            className="input"
            value={meetingId}
            onChange={(e) => setMeetingId(e.target.value)}
            placeholder="Появится после «Начать встречу»"
          />
        </div>
        <div className="btn-row">
          <button type="button" className="btn btn--primary" onClick={startMeeting} disabled={loading}>
            Начать встречу
          </button>
          <button type="button" className="btn btn--ghost" onClick={stopMeeting} disabled={loading}>
            Завершить
          </button>
        </div>
      </section>

      <section className="card">
        <h2 className="card__title">Диктофон</h2>
        <p className="card__desc">
          Запись через микрофон браузера. После «Стоп» — «Расшифровать»: на сервере используется локальный Whisper (Docker whisper-api) или OpenAI — см. README / STT_PROVIDER.
        </p>
        {recError ? <p className="card__desc" style={{ color: "var(--danger)" }}>{recError}</p> : null}
        <div className="dictaphone-timer">{formatTime(elapsed)}</div>
        <p className="dictaphone-hint">
          {recState === "idle" && "Нажмите, чтобы начать запись"}
          {recState === "recording" && "Идёт запись…"}
          {recState === "stopped" && recordedBlob
            ? `Готово: ${(recordedBlob.size / 1024).toFixed(0)} КБ`
            : recState === "stopped"
              ? "Запись остановлена"
              : null}
        </p>
        <button
          type="button"
          className={`btn btn--record btn--primary ${recState === "recording" ? "is-recording" : ""}`}
          onClick={recState === "recording" ? stopRecording : startRecording}
          disabled={loading}
        >
          {recState === "recording" ? "Остановить запись" : recState === "stopped" ? "Новая запись" : "Записать"}
        </button>
        <div className="btn-row" style={{ marginTop: 12 }}>
          <button
            type="button"
            className="btn btn--danger"
            onClick={discardRecording}
            disabled={(recState === "idle" && !recordedBlob) || loading}
          >
            {recState === "recording" ? "Отменить" : "Сбросить"}
          </button>
          <button
            type="button"
            className="btn btn--primary"
            onClick={transcribeMeeting}
            disabled={loading || !meetingId || (!recordedBlob && !audioFile)}
          >
            Расшифровать
          </button>
        </div>
      </section>

      <section className="card">
        <h2 className="card__title">Файл</h2>
        <p className="card__desc">Альтернатива диктофону — загрузить готовое аудио.</p>
        <div className="field">
          <label htmlFor="file">Аудиофайл</label>
          <input
            id="file"
            className="file-input"
            type="file"
            accept="audio/*,.webm,.mp3,.wav,.m4a,.ogg"
            onChange={(e) => {
              setAudioFile(e.target.files?.[0] || null);
              if (e.target.files?.[0]) setRecordedBlob(null);
            }}
          />
        </div>
        <div className="btn-row">
          <button type="button" className="btn btn--ghost" onClick={runDemoFlow} disabled={loading || !meetingId}>
            Демо-протокол (без аудио)
          </button>
        </div>
      </section>

      <section className="card">
        <h2 className="card__title">Ответ API</h2>
        <p className="card__desc">JSON от последнего действия.</p>
        {output == null ? (
          <pre className="output">Выполните действие выше.</pre>
        ) : (
          <pre className={`output ${outputIsError ? "output--error" : ""}`}>
            {JSON.stringify(output, null, 2)}
          </pre>
        )}
      </section>
    </div>
  );
}
