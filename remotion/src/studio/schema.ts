import { z } from "zod";

// scripts/studio_render.py writes these props from workspace/03_edit_plans/<id>.studio.json.
// Times are in seconds.
const timed = { start: z.number(), end: z.number() };

export const studioSchema = z.object({
  fps: z.number(),
  durationInSeconds: z.number(),
  // Person cut out by scripts/matte_video.py (WebM VP9 with alpha + original audio)
  matte: z.string(),
  matteDuration: z.number(),
  logo: z.string(),
  voiceVolume: z.number(),
  subject: z.object({ scale: z.number(), offsetY: z.number() }),
  captionPages: z.array(
    z.object({
      start: z.number(),
      end: z.number(),
      words: z.array(z.object({ text: z.string(), start: z.number(), end: z.number(), highlight: z.boolean() })),
    }),
  ),
  zooms: z.array(z.object({ scale: z.number(), ...timed })),
  emojis: z.array(z.object({ src: z.string(), x: z.number(), y: z.number(), size: z.number(), rotate: z.number(), ...timed })),
  badges: z.array(z.object({ icon: z.string(), text: z.string(), ...timed })),
  callouts: z.array(
    z.object({ title: z.string(), subtitle: z.string(), emoji: z.string(), side: z.enum(["left", "right"]), y: z.number(), ...timed }),
  ),
  headlines: z.array(z.object({ text: z.string(), accent: z.string(), backdrop: z.string(), emoji: z.string(), ...timed })),
  endCard: z
    .object({ start: z.number(), title: z.string(), contacts: z.array(z.object({ icon: z.string(), text: z.string() })) })
    .nullable(),
  bgm: z.object({ src: z.string(), volume: z.number(), duckVolume: z.number() }).nullable(),
  sfx: z.array(z.object({ src: z.string(), at: z.number(), volume: z.number() })),
});

export type StudioProps = z.infer<typeof studioSchema>;
