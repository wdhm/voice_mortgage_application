import { useEffect, useRef, useState } from "react";
import { voiceWebsocketUrl } from "../api";
import { pcm16ToFloat32, toPcm16, VOICE_SAMPLE_RATE } from "./pcm";

export type VoiceState = "idle" | "connecting" | "listening" | "thinking" | "speaking" | "error";

type VoiceEvent = {
  type: string;
  status?: VoiceState;
  message?: string;
  speaker?: "customer" | "assistant";
  text?: string;
  final?: boolean;
};

export function useVoiceLive(onFinalTranscript: () => void) {
  const [state, setState] = useState<VoiceState>("idle");
  const [error, setError] = useState("");
  const [partialTranscript, setPartialTranscript] = useState("");
  const socketRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const contextRef = useRef<AudioContext | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const silentGainRef = useRef<GainNode | null>(null);
  const playbackSourcesRef = useRef(new Set<AudioBufferSourceNode>());
  const nextPlaybackAtRef = useRef(0);
  const captureStartedRef = useRef(false);

  function clearPlayback() {
    for (const source of playbackSourcesRef.current) {
      try { source.stop(); } catch { /* Already stopped. */ }
    }
    playbackSourcesRef.current.clear();
    nextPlaybackAtRef.current = contextRef.current?.currentTime ?? 0;
  }

  function queuePlayback(data: ArrayBuffer) {
    const context = contextRef.current;
    if (!context || data.byteLength === 0) return;
    const samples = pcm16ToFloat32(data);
    const buffer = context.createBuffer(1, samples.length, VOICE_SAMPLE_RATE);
    buffer.getChannelData(0).set(samples);
    const source = context.createBufferSource();
    source.buffer = buffer;
    source.connect(context.destination);
    const startsAt = Math.max(context.currentTime + 0.015, nextPlaybackAtRef.current);
    nextPlaybackAtRef.current = startsAt + buffer.duration;
    playbackSourcesRef.current.add(source);
    source.onended = () => playbackSourcesRef.current.delete(source);
    source.start(startsAt);
  }

  function startCapture() {
    const context = contextRef.current;
    const stream = streamRef.current;
    const socket = socketRef.current;
    if (!context || !stream || !socket || captureStartedRef.current) return;
    const source = context.createMediaStreamSource(stream);
    const processor = context.createScriptProcessor(2048, 1, 1);
    const silentGain = context.createGain();
    silentGain.gain.value = 0;
    processor.onaudioprocess = (event) => {
      if (socket.readyState !== WebSocket.OPEN) return;
      socket.send(toPcm16(event.inputBuffer.getChannelData(0), context.sampleRate));
    };
    source.connect(processor);
    processor.connect(silentGain);
    silentGain.connect(context.destination);
    sourceRef.current = source;
    processorRef.current = processor;
    silentGainRef.current = silentGain;
    captureStartedRef.current = true;
  }

  function releaseResources(closeSocket: boolean) {
    clearPlayback();
    processorRef.current?.disconnect();
    sourceRef.current?.disconnect();
    silentGainRef.current?.disconnect();
    processorRef.current = null;
    sourceRef.current = null;
    silentGainRef.current = null;
    captureStartedRef.current = false;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    void contextRef.current?.close();
    contextRef.current = null;
    if (closeSocket && socketRef.current?.readyState === WebSocket.OPEN) socketRef.current.close(1000);
    socketRef.current = null;
  }

  function handleControlMessage(raw: string) {
    const event = JSON.parse(raw) as VoiceEvent;
    if (event.type === "voice.status" && event.status) {
      setState(event.status);
      if (event.status === "listening") startCapture();
    } else if (event.type === "voice.interrupted") {
      clearPlayback();
      setState("listening");
    } else if (event.type === "voice.transcript" && event.text) {
      if (event.final) {
        setPartialTranscript("");
        onFinalTranscript();
      } else {
        setPartialTranscript((current) => current + event.text);
      }
    } else if (event.type === "voice.error") {
      setError(event.message ?? "Voice Live failed");
      setState("error");
    }
  }

  async function start() {
    if (state !== "idle" && state !== "error") return;
    setError("");
    setPartialTranscript("");
    setState("connecting");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      const context = new AudioContext({ latencyHint: "interactive" });
      await context.resume();
      streamRef.current = stream;
      contextRef.current = context;
      nextPlaybackAtRef.current = context.currentTime;

      const socket = new WebSocket(voiceWebsocketUrl());
      socket.binaryType = "arraybuffer";
      socketRef.current = socket;
      socket.onmessage = (message) => {
        if (message.data instanceof ArrayBuffer) queuePlayback(message.data);
        else if (typeof message.data === "string") handleControlMessage(message.data);
      };
      socket.onerror = () => {
        setError("Could not connect to Voice Live");
        setState("error");
      };
      socket.onclose = () => {
        releaseResources(false);
        setState((current) => current === "error" ? "error" : "idle");
      };
    } catch (caught) {
      releaseResources(true);
      setError(caught instanceof Error ? caught.message : "Microphone access failed");
      setState("error");
    }
  }

  function stop() {
    releaseResources(true);
    setPartialTranscript("");
    setState("idle");
  }

  useEffect(() => () => releaseResources(true), []);

  return { state, error, partialTranscript, start, stop };
}