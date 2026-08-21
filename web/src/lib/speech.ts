// Speaks assistant transcript lines aloud. Primary path is server-side Azure
// neural TTS (POST /api/tts -> MP3); if that is unavailable (provider off, network,
// auth) it falls back to the browser's Web Speech API so the demo never goes silent.
// Lines are queued and played strictly in order.

let enabled = true;
let speaking = false;
const queue: string[] = [];
let current: HTMLAudioElement | null = null;
let currentUrl: string | null = null;

export function isSpeechEnabled(): boolean {
  return enabled;
}

export function setSpeechEnabled(on: boolean): void {
  enabled = on;
  if (!on) cancelSpeech();
}

export function cancelSpeech(): void {
  queue.length = 0;
  speaking = false;
  if (current) {
    current.pause();
    current.src = "";
    current = null;
  }
  if (currentUrl) {
    URL.revokeObjectURL(currentUrl);
    currentUrl = null;
  }
  if (typeof window !== "undefined" && "speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
}

export function speak(text: string): void {
  const t = text.trim();
  if (!enabled || !t) return;
  queue.push(t);
  if (!speaking) void drain();
}

async function drain(): Promise<void> {
  speaking = true;
  while (enabled && queue.length) {
    const text = queue.shift() as string;
    try {
      await speakViaServer(text);
    } catch {
      await speakViaBrowser(text);
    }
  }
  speaking = false;
}

async function speakViaServer(text: string): Promise<void> {
  const res = await fetch("/api/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error(`tts ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  currentUrl = url;
  await new Promise<void>((resolve, reject) => {
    const audio = new Audio(url);
    current = audio;
    const done = () => {
      if (currentUrl === url) {
        URL.revokeObjectURL(url);
        currentUrl = null;
      }
      current = null;
    };
    audio.onended = () => {
      done();
      resolve();
    };
    audio.onerror = () => {
      done();
      reject(new Error("audio playback failed"));
    };
    audio.play().catch((err) => {
      done();
      reject(err);
    });
  });
}

function speakViaBrowser(text: string): Promise<void> {
  return new Promise((resolve) => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      resolve();
      return;
    }
    const utter = new SpeechSynthesisUtterance(text);
    utter.onend = () => resolve();
    utter.onerror = () => resolve();
    window.speechSynthesis.speak(utter);
  });
}
