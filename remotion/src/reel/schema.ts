import { z } from "zod";

// scripts/render_pipeline.py edit_plan.json dan shu shaklda props yozadi.
// Vaqtlar soniyada (start/end/at), subtitr vaqtlari millisekundda.
const timed = { start: z.number(), end: z.number() };

export const reelSchema = z.object({
  fps: z.number(),
  durationInSeconds: z.number(),
  source: z.string(),
  logo: z.string(),
  voiceVolume: z.number(),
  hook: z.object({ text: z.string(), emoji: z.string(), ...timed }).nullable(),
  captionPages: z.array(
    z.object({
      startMs: z.number(),
      endMs: z.number(),
      words: z.array(
        z.object({ text: z.string(), startMs: z.number(), endMs: z.number(), style: z.string().nullable() }),
      ),
    }),
  ),
  zooms: z.array(z.object({ scale: z.number(), ...timed })),
  visuals: z.array(
    z.object({
      id: z.string(),
      kind: z.enum(["broll", "clip", "sticker"]),
      src: z.string(),
      position: z.enum(["top", "center", "bottom"]),
      ...timed,
    }),
  ),
  emojis: z.array(
    z.object({ src: z.string(), position: z.enum(["top", "center", "left", "right"]), size: z.number(), ...timed }),
  ),
  cards: z.array(
    z.discriminatedUnion("type", [
      z.object({ type: z.literal("compare"), weak: z.string(), strong: z.string(), weakLabel: z.string(), strongLabel: z.string(), ...timed }),
      z.object({ type: z.literal("band_meter"), from: z.number(), to: z.number(), label: z.string(), ...timed }),
      z.object({ type: z.literal("callout"), icon: z.string(), text: z.string(), tone: z.enum(["brand", "gold", "glass", "red", "green"]), ...timed }),
    ]),
  ),
  cta: z.object({ text: z.string(), icon: z.string(), emoji: z.string(), start: z.number() }).nullable(),
  bgm: z.object({ src: z.string(), volume: z.number(), duckVolume: z.number(), ducking: z.boolean() }).nullable(),
  sfx: z.array(z.object({ src: z.string(), at: z.number(), volume: z.number() })),
  voiceovers: z.array(z.object({ src: z.string(), at: z.number(), volume: z.number() })),
});

export type ReelProps = z.infer<typeof reelSchema>;
export type CaptionPage = ReelProps["captionPages"][number];
