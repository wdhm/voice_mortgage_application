const TARGET_SAMPLE_RATE = 24_000;

type SendFrame = (frame: Record<string, unknown>) => void;

export class BrowserVoiceAudio {
  private inputContext: AudioContext | null = null;
  private playbackContext: AudioContext | null = null;
  private stream: MediaStream | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private processor: ScriptProcessorNode | null = null;
  private mutedOutput: GainNode | null = null;
  private playbackSources = new Set<AudioBufferSourceNode>();
  private nextPlaybackTime = 0;

  async startCapture(send: SendFrame): Promise<void> {
    if (this.stream) return;
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error("Microphone access is not supported by this browser.");
    }

    this.playbackContext ??= new AudioContext();
    await this.playbackContext.resume();

    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });

    const context = new AudioContext();
    const source = context.createMediaStreamSource(stream);
    const processor = context.createScriptProcessor(4096, 1, 1);
    const mutedOutput = context.createGain();
    mutedOutput.gain.value = 0;

    processor.onaudioprocess = (event) => {
      const input = event.inputBuffer.getChannelData(0);
      const samples = resample(input, context.sampleRate, TARGET_SAMPLE_RATE);
      send({ type: "audio", pcm: encodePcm16(samples) });
    };

    source.connect(processor);
    processor.connect(mutedOutput);
    mutedOutput.connect(context.destination);
    await context.resume();

    this.stream = stream;
    this.inputContext = context;
    this.source = source;
    this.processor = processor;
    this.mutedOutput = mutedOutput;
  }

  async stopCapture(): Promise<void> {
    this.processor?.disconnect();
    this.source?.disconnect();
    this.mutedOutput?.disconnect();
    this.stream?.getTracks().forEach((track) => track.stop());

    this.processor = null;
    this.source = null;
    this.mutedOutput = null;
    this.stream = null;

    const context = this.inputContext;
    this.inputContext = null;
    if (context && context.state !== "closed") await context.close();
  }

  play(pcmBase64: string): void {
    const context = this.playbackContext;
    if (!context || context.state === "closed") return;

    const bytes = decodeBase64(pcmBase64);
    const sampleCount = Math.floor(bytes.byteLength / 2);
    const audioBuffer = context.createBuffer(1, sampleCount, TARGET_SAMPLE_RATE);
    const channel = audioBuffer.getChannelData(0);
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    for (let i = 0; i < sampleCount; i++) {
      channel[i] = view.getInt16(i * 2, true) / 0x8000;
    }

    const source = context.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(context.destination);
    source.onended = () => this.playbackSources.delete(source);

    const startAt = Math.max(context.currentTime + 0.02, this.nextPlaybackTime);
    source.start(startAt);
    this.nextPlaybackTime = startAt + audioBuffer.duration;
    this.playbackSources.add(source);
  }

  interrupt(): void {
    this.playbackSources.forEach((source) => {
      try {
        source.stop();
      } catch (error) {
        if (!(error instanceof DOMException && error.name === "InvalidStateError")) throw error;
      }
    });
    this.playbackSources.clear();
    this.nextPlaybackTime = this.playbackContext?.currentTime ?? 0;
  }

  async close(): Promise<void> {
    await this.stopCapture();
    this.interrupt();
    const context = this.playbackContext;
    this.playbackContext = null;
    if (context && context.state !== "closed") await context.close();
  }
}

function resample(input: Float32Array, sourceRate: number, targetRate: number): Float32Array {
  if (sourceRate === targetRate) return input;
  const outputLength = Math.max(1, Math.floor((input.length * targetRate) / sourceRate));
  const output = new Float32Array(outputLength);
  const ratio = sourceRate / targetRate;

  for (let i = 0; i < outputLength; i++) {
    const position = i * ratio;
    const left = Math.floor(position);
    const right = Math.min(left + 1, input.length - 1);
    const mix = position - left;
    output[i] = input[left] * (1 - mix) + input[right] * mix;
  }
  return output;
}

function encodePcm16(samples: Float32Array): string {
  const buffer = new ArrayBuffer(samples.length * 2);
  const view = new DataView(buffer);
  for (let i = 0; i < samples.length; i++) {
    const sample = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(i * 2, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
  }

  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  return btoa(binary);
}

function decodeBase64(value: string): Uint8Array {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}
