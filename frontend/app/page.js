"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const apiBase = "/api";

function formatTime(totalSeconds) {
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function formatDate(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
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
  const [recordings, setRecordings] = useState([]);
  const [protocolLibrary, setProtocolLibrary] = useState([]);
  const [protocolLoading, setProtocolLoading] = useState(false);
  const [integrationStatus, setIntegrationStatus] = useState("Интеграции еще не подключены.");
  const [providerStatus, setProviderStatus] = useState("Внешние AI-провайдеры не подключены.");
  const [kimiTask, setKimiTask] = useState("Собрать ресерч и презентацию по итогам встречи");
  const [executionResult, setExecutionResult] = useState(null);
  const [cloudService, setCloudService] = useState("google_drive");

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
      if (p?.link_color) document.documentElement.style.setProperty("--accent", p.link_color);
    } else {
      setTelegramHint("Локальный режим. Для Telegram нужен HTTPS-туннель (см. README).");
    }
  }, []);

  useEffect(() => {
    return () => {
      if (tickRef.current) clearInterval(tickRef.current);
      streamRef.current?.getTracks().forEach((t) => t.stop());
      recordings.forEach((item) => URL.revokeObjectURL(item.url));
    };
  }, [recordings]);

  const loadProtocolLibrary = useCallback(async () => {
    setProtocolLoading(true);
    try {
      const meetingsRes = await fetch(`${apiBase}/meetings`);
      const meetingsData = await meetingsRes.json();
      if (!meetingsRes.ok || !Array.isArray(meetingsData)) throw new Error("Не удалось получить список встреч.");
      const subset = meetingsData.slice(0, 12);
      const protocolResults = await Promise.all(
        subset.map(async (meeting) => {
          try {
            const protocolRes = await fetch(`${apiBase}/meetings/${meeting.id}/protocol`);
            if (!protocolRes.ok) return null;
            const protocolData = await protocolRes.json();
            return {
              meetingId: meeting.id,
              title: meeting.title,
              startedAt: meeting.started_at,
              summary: protocolData.summary,
              decisions: protocolData.decisions || [],
              actionItems: protocolData.action_items || [],
            };
          } catch {
            return null;
          }
        })
      );
      setProtocolLibrary(protocolResults.filter(Boolean));
    } catch (error) {
      setOutput({ error: error.message });
    } finally {
      setProtocolLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProtocolLibrary();
  }, [loadProtocolLibrary]);

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
        const ext = type.includes("webm") ? "webm" : type.includes("mp4") ? "m4a" : "audio";
        const url = URL.createObjectURL(blob);
        setRecordings((prev) => {
          const item = {
            id: crypto.randomUUID(),
            name: `Запись ${new Date().toLocaleTimeString("ru-RU")} (${ext})`,
            url,
            createdAt: new Date().toISOString(),
            sizeKb: Math.round(blob.size / 1024),
          };
          const next = [item, ...prev].slice(0, 3);
          if (prev.length >= 3) {
            prev.slice(2).forEach((old) => URL.revokeObjectURL(old.url));
          }
          return next;
        });
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
      await loadProtocolLibrary();
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
      await loadProtocolLibrary();
    } catch (error) {
      setOutput({ error: error.message });
    } finally {
      setLoading(false);
    }
  }

  async function checkSttHealth() {
    setLoading(true);
    setOutput(null);
    try {
      const response = await fetch(`${apiBase}/health/stt`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Проверка не удалась");
      setOutput(data);
    } catch (error) {
      setOutput({ error: error.message });
    } finally {
      setLoading(false);
    }
  }

  async function connectIntegration(service) {
    setLoading(true);
    setExecutionResult(null);
    try {
      const data = await postJson("/assistant/integrations/connect", { service });
      setIntegrationStatus(`${data.service}: ${data.note}`);
    } catch (error) {
      setOutput({ error: error.message });
    } finally {
      setLoading(false);
    }
  }

  async function connectAIProvider(provider) {
    setLoading(true);
    setExecutionResult(null);
    try {
      const data = await postJson("/assistant/providers/connect", { provider });
      setProviderStatus(`${data.provider}: ${data.note}`);
    } catch (error) {
      setOutput({ error: error.message });
    } finally {
      setLoading(false);
    }
  }

  async function transcribeAndAutoProtocol() {
    if (!meetingId) {
      setOutput({ error: "Сначала создайте встречу (Старт)." });
      return;
    }
    const file = buildAudioFileForUpload();
    if (!file) {
      setOutput({ error: "Нужно записать или загрузить аудио." });
      return;
    }
    setLoading(true);
    setExecutionResult(null);
    try {
      const formData = new FormData();
      formData.append("audio", file);
      const response = await fetch(`${apiBase}/meetings/${meetingId}/auto-protocol`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Автопротокол не выполнен");
      setOutput(data);
      await loadProtocolLibrary();
    } catch (error) {
      setOutput({ error: error.message });
    } finally {
      setLoading(false);
    }
  }

  async function executeProtocolTaskInKimi() {
    if (!meetingId) {
      setOutput({ error: "Укажите ID встречи для выполнения пункта протокола." });
      return;
    }
    setLoading(true);
    setOutput(null);
    try {
      const data = await postJson("/assistant/protocol/execute-task", {
        meeting_id: meetingId,
        task: kimiTask,
        provider: "kimi",
      });
      setExecutionResult(data);
    } catch (error) {
      setOutput({ error: error.message });
    } finally {
      setLoading(false);
    }
  }

  async function saveResultToCloud() {
    if (!executionResult?.artifact) {
      setOutput({ error: "Сначала поручите задачу AI и получите результат." });
      return;
    }
    setLoading(true);
    try {
      const bytes = new TextEncoder().encode(executionResult.artifact);
      let binary = "";
      bytes.forEach((b) => {
        binary += String.fromCharCode(b);
      });
      const contentBase64 = btoa(binary);
      const data = await postJson("/assistant/integrations/upload", {
        service: cloudService,
        filename: `protocol-result-${meetingId || "draft"}.txt`,
        mime_type: "text/plain",
        content_base64: contentBase64,
      });
      setIntegrationStatus(`${data.note}${data.location ? ` (${data.location})` : ""}`);
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
        <h2 className="card__title">Интеграции: календари и файловые сервисы</h2>
        <p className="card__desc">Подключение внешних систем для материалов и планирования.</p>
        <div className="btn-row">
          <button type="button" className="btn btn--ghost" onClick={() => connectIntegration("google_calendar")} disabled={loading}>
            Google Calendar
          </button>
          <button type="button" className="btn btn--ghost" onClick={() => connectIntegration("outlook_calendar")} disabled={loading}>
            Outlook Calendar
          </button>
          <button type="button" className="btn btn--ghost" onClick={() => connectIntegration("google_drive")} disabled={loading}>
            Google Drive
          </button>
          <button type="button" className="btn btn--ghost" onClick={() => connectIntegration("dropbox")} disabled={loading}>
            Dropbox
          </button>
        </div>
        <p className="card__desc" style={{ marginTop: 10 }}>{integrationStatus}</p>
      </section>

      <section className="card">
        <h2 className="card__title">Внешние нейросети (Kimi и другие)</h2>
        <p className="card__desc">AI-агенты для ресерча, поиска информации, презентаций и записок.</p>
        <div className="btn-row">
          <button type="button" className="btn btn--ghost" onClick={() => connectAIProvider("kimi")} disabled={loading}>
            Подключить Kimi
          </button>
          <button type="button" className="btn btn--ghost" onClick={() => connectAIProvider("openai")} disabled={loading}>
            Подключить OpenAI
          </button>
          <button type="button" className="btn btn--ghost" onClick={() => connectAIProvider("claude")} disabled={loading}>
            Подключить Claude
          </button>
        </div>
        <p className="card__desc" style={{ marginTop: 10 }}>{providerStatus}</p>
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
          Запись через микрофон браузера. После «Стоп» — «Расшифровать»: на сервере используется локальный openai/whisper (модель small) или OpenAI API — см. README / STT_PROVIDER.
        </p>
        <div className="btn-row" style={{ marginBottom: 12 }}>
          <button type="button" className="btn btn--ghost" onClick={checkSttHealth} disabled={loading}>
            Проверить Whisper (связь с API)
          </button>
        </div>
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
          <button
            type="button"
            className="btn btn--ghost"
            onClick={transcribeAndAutoProtocol}
            disabled={loading || !meetingId || (!recordedBlob && !audioFile)}
          >
            Транскрибация + автопротокол
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
        <h2 className="card__title">Последние 3 аудиозаписи</h2>
        <p className="card__desc">Сохраняются в текущей сессии Mini App.</p>
        {recordings.length === 0 ? (
          <p className="card__desc">Пока нет записей. Нажмите "Записать".</p>
        ) : (
          recordings.map((item) => (
            <div key={item.id} className="library-item">
              <div className="library-item__meta">
                <strong>{item.name}</strong>
                <span>{formatDate(item.createdAt)} · {item.sizeKb} КБ</span>
              </div>
              <audio controls src={item.url} className="audio-player">
                Ваш браузер не поддерживает аудио.
              </audio>
            </div>
          ))
        )}
      </section>

      <section className="card">
        <h2 className="card__title">Протоколы и саммари</h2>
        <p className="card__desc">Текстовые протоколы по встречам из базы.</p>
        <div className="btn-row" style={{ marginBottom: 10 }}>
          <button type="button" className="btn btn--ghost" onClick={loadProtocolLibrary} disabled={loading || protocolLoading}>
            {protocolLoading ? "Обновляем..." : "Обновить список"}
          </button>
        </div>
        {protocolLibrary.length === 0 ? (
          <p className="card__desc">Пока нет протоколов. Создайте встречу и выполните "Демо-протокол" или "Расшифровать".</p>
        ) : (
          protocolLibrary.map((entry) => (
            <div key={entry.meetingId} className="library-item">
              <div className="library-item__meta">
                <strong>{entry.title}</strong>
                <span>{formatDate(entry.startedAt)}</span>
              </div>
              <p className="library-summary">{entry.summary}</p>
            </div>
          ))
        )}
        {output && outputIsError ? <p className="card__desc" style={{ color: "var(--danger)" }}>{output.error}</p> : null}
      </section>

      <section className="card">
        <h2 className="card__title">Поручение задачи AI</h2>
        <p className="card__desc">Отправка задачи из автопротокола во внешнюю модель с готовым результатом.</p>
        <div className="field">
          <label htmlFor="kimi-task">Задача для выполнения</label>
          <input
            id="kimi-task"
            className="input"
            value={kimiTask}
            onChange={(e) => setKimiTask(e.target.value)}
            placeholder="Например: подготовить презентацию и сопроводительную записку"
          />
        </div>
        <div className="btn-row">
          <button type="button" className="btn btn--primary" onClick={executeProtocolTaskInKimi} disabled={loading || !meetingId}>
            Поручить AI
          </button>
        </div>
        {executionResult ? (
          <div className="library-item" style={{ marginTop: 10 }}>
            <div className="library-item__meta">
              <strong>{executionResult.provider}</strong>
              <span>{executionResult.status}</span>
            </div>
            <p className="library-summary">{executionResult.summary}</p>
            <p className="library-summary" style={{ marginTop: 6 }}>{executionResult.artifact}</p>
            <div className="btn-row" style={{ marginTop: 10 }}>
              <button
                type="button"
                className={`btn ${cloudService === "google_drive" ? "btn--primary" : "btn--ghost"}`}
                onClick={() => setCloudService("google_drive")}
                disabled={loading}
              >
                Google Drive
              </button>
              <button
                type="button"
                className={`btn ${cloudService === "dropbox" ? "btn--primary" : "btn--ghost"}`}
                onClick={() => setCloudService("dropbox")}
                disabled={loading}
              >
                Dropbox
              </button>
              <button type="button" className="btn btn--ghost" onClick={saveResultToCloud} disabled={loading}>
                Сохранить в облако
              </button>
            </div>
          </div>
        ) : null}
      </section>
    </div>
  );
}
