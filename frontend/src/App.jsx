import React, { useEffect, useMemo, useRef, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8080";

function SettingsPanel({ settings, onSettingsChange }) {
  const [draft, setDraft] = useState(settings);

  useEffect(() => {
    setDraft(settings);
  }, [settings]);

  return (
    <section>
      <h2>Settings</h2>
      <label>
        Target language
        <input
          value={draft.target_language}
          onChange={(event) => setDraft({ ...draft, target_language: event.target.value })}
        />
      </label>
      <label>
        Voice
        <input value={draft.voice} onChange={(event) => setDraft({ ...draft, voice: event.target.value })} />
      </label>
      <label>
        Output mode
        <select
          value={draft.output_mode}
          onChange={(event) => setDraft({ ...draft, output_mode: event.target.value })}
        >
          <option value="text">Text</option>
          <option value="audio">Audio</option>
        </select>
      </label>
      <button type="button" onClick={() => onSettingsChange(draft)}>
        Save settings
      </button>
    </section>
  );
}

function LivePanel({ settings }) {
  const [context, setContext] = useState("");
  const [transcript, setTranscript] = useState("");
  const [translation, setTranslation] = useState("");
  const socketRef = useRef(null);

  useEffect(() => {
    const ws = new WebSocket(`${API_BASE.replace("http", "ws")}/ws/live`);
    socketRef.current = ws;

    ws.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      if (payload.type === "translation_complete") {
        setTranslation(payload.translation);
      }
    };

    return () => ws.close();
  }, []);

  const sendTranscript = () => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN || !transcript.trim()) {
      return;
    }
    socketRef.current.send(
      JSON.stringify({
        transcript,
        target_language: settings.target_language,
        voice: settings.voice,
        output_mode: settings.output_mode,
        background_context: context,
      })
    );
  };

  const webSpeechSupported = useMemo(
    () => Boolean(window.SpeechRecognition || window.webkitSpeechRecognition),
    []
  );

  return (
    <section>
      <h2>Live translation</h2>
      <p>Microphone transcription relies on the browser Web Speech API: {webSpeechSupported ? "available" : "missing"}.</p>
      <label>
        Optional context
        <input value={context} onChange={(event) => setContext(event.target.value)} placeholder="technical interview" />
      </label>
      <label>
        Transcript
        <textarea value={transcript} onChange={(event) => setTranscript(event.target.value)} />
      </label>
      <button type="button" onClick={sendTranscript}>
        Stream translation
      </button>
      <p>{translation}</p>
    </section>
  );
}

function FilePanel({ settings }) {
  const [file, setFile] = useState(null);
  const [context, setContext] = useState("");
  const [result, setResult] = useState(null);

  const submit = async () => {
    if (!file) {
      return;
    }
    const body = new FormData();
    body.append("file", file);
    body.append("target_language", settings.target_language);
    body.append("voice", settings.voice);
    body.append("output_mode", settings.output_mode);
    body.append("background_context", context);

    const response = await fetch(`${API_BASE}/api/files/translate`, {
      method: "POST",
      body,
    });
    const payload = await response.json();
    setResult(payload);
  };

  return (
    <section>
      <h2>Upload translation</h2>
      <input type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
      <label>
        Optional context
        <input value={context} onChange={(event) => setContext(event.target.value)} placeholder="medical conference" />
      </label>
      <button type="button" onClick={submit}>
        Translate file
      </button>
      {result ? (
        <article>
          <p>{result.transcript}</p>
          <p>{result.translation}</p>
        </article>
      ) : null}
    </section>
  );
}

export default function App() {
  const [mode, setMode] = useState("live");
  const [settings, setSettings] = useState({ target_language: "Spanish", voice: "alloy", output_mode: "text" });

  useEffect(() => {
    fetch(`${API_BASE}/api/settings`)
      .then((response) => response.json())
      .then((payload) => setSettings(payload));
  }, []);

  const saveSettings = async (nextSettings) => {
    const response = await fetch(`${API_BASE}/api/settings`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(nextSettings),
    });
    const payload = await response.json();
    setSettings(payload);
  };

  return (
    <main>
      <h1>AI Context Translator</h1>
      <nav>
        <button type="button" onClick={() => setMode("live")}>Live</button>
        <button type="button" onClick={() => setMode("file")}>File</button>
        <button type="button" onClick={() => setMode("settings")}>Settings</button>
      </nav>
      {mode === "live" ? <LivePanel settings={settings} /> : null}
      {mode === "file" ? <FilePanel settings={settings} /> : null}
      {mode === "settings" ? <SettingsPanel settings={settings} onSettingsChange={saveSettings} /> : null}
    </main>
  );
}
