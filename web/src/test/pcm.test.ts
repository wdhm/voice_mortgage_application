import { describe, expect, it } from "vitest";
import { pcm16ToFloat32, toPcm16 } from "../voice/pcm";

describe("Voice Live PCM conversion", () => {
  it("downsamples browser audio to 24 kHz PCM16", () => {
    const source = new Float32Array(4_800).fill(0.5);
    const pcm = new Int16Array(toPcm16(source, 48_000));

    expect(pcm).toHaveLength(2_400);
    expect(pcm[0]).toBeCloseTo(16_384, -1);
  });

  it("decodes signed PCM16 for browser playback", () => {
    const encoded = new Int16Array([-32_768, 0, 32_767]);
    const decoded = pcm16ToFloat32(encoded.buffer);

    expect(Array.from(decoded)).toEqual([-1, 0, 1]);
  });
});