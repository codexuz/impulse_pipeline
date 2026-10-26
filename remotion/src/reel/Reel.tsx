import { Audio, Video } from "@remotion/media";
import React, { useMemo } from "react";
import {
  AbsoluteFill,
  CalculateMetadataFunction,
  Composition,
  Easing,
  Img,
  interpolate,
  Sequence,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { asset, Chip, Emoji } from "../components/primitives";
import { headingFont } from "../fonts";
import { brandGradient, brandTextGradient, colors, safeZone } from "../theme";
import { Captions } from "./Captions";
import { ReelCard } from "./Cards";
import { type ReelProps, reelSchema } from "./schema";

const calculateMetadata: CalculateMetadataFunction<ReelProps> = ({ props }) => ({
  fps: props.fps,
  durationInFrames: Math.max(1, Math.ceil(props.durationInSeconds * props.fps)),
});

export const ReelComposition = () => (
  <Composition
    id="Reel"
    component={Reel}
    schema={reelSchema}
    width={1080}
    height={1920}
    fps={60}
    durationInFrames={300}
    calculateMetadata={calculateMetadata}
    defaultProps={{
      fps: 60,
      durationInSeconds: 5,
      source: "",
      logo: "",
      voiceVolume: 1,
      hook: { text: "Band 8.0 idioms", emoji: "", start: 0, end: 2.5 },
      captionPages: [
        {
          startMs: 300,
          endMs: 1800,
          words: [
            { text: "very", startMs: 300, endMs: 600, style: "mistake" },
            { text: "happy", startMs: 600, endMs: 1000, style: "mistake" },
            { text: "emas", startMs: 1000, endMs: 1800, style: null },
          ],
        },
        {
          startMs: 1800,
          endMs: 3600,
          words: [
            { text: "over", startMs: 1800, endMs: 2200, style: "correct" },
            { text: "the", startMs: 2200, endMs: 2400, style: "correct" },
            { text: "moon", startMs: 2400, endMs: 3600, style: "correct" },
          ],
        },
      ],
      zooms: [{ start: 0, end: 2.5, scale: 1.12 }],
      visuals: [],
      emojis: [],
      cards: [
        { type: "compare", weak: "very happy", strong: "over the moon", weakLabel: "BAND 5.5", strongLabel: "BAND 8.0", start: 2.5, end: 4.8 },
      ],
      cta: { text: "Izohda 'IELTS' deb yozing", icon: "MessageCircle", emoji: "", start: 4 },
      bgm: null,
      sfx: [],
      voiceovers: [],
    }}
  />
);

const sec = (s: number, fps: number) => Math.round(s * fps);

export const Reel: React.FC<ReelProps> = (props) => {
  const { fps } = useVideoConfig();
  const frame = useCurrentFrame();
  const t = frame / fps;

  // Auto-zoom: har bir oraliqda 0.2s silliq punch-in
  const zoom = props.zooms.reduce(
    (acc, z) =>
      acc +
      (t >= z.start && t < z.end
        ? (z.scale - 1) * interpolate(t, [z.start, z.start + 0.2], [0, 1], { extrapolateRight: "clamp", easing: Easing.bezier(0.16, 1, 0.3, 1) })
        : 0),
    1,
  );

  // Ustoz gapirayotgan oraliqlar — BGM ducking uchun
  const speech = useMemo(
    () => props.captionPages.flatMap((p) => p.words.map((w) => [w.startMs / 1000, w.endMs / 1000] as const)),
    [props.captionPages],
  );

  return (
    <AbsoluteFill style={{ backgroundColor: colors.navy }}>
      <AbsoluteFill style={{ scale: zoom }}>
        {props.source ? (
          <Video src={asset(props.source)} volume={props.voiceVolume} objectFit="cover" style={{ width: "100%", height: "100%" }} />
        ) : null}
      </AbsoluteFill>

      {props.visuals.map((v) => {
        const duration = Math.max(1, sec(v.end - v.start, fps));
        return (
          <Sequence key={v.id} name={`Visual ${v.id}`} from={sec(v.start, fps)} durationInFrames={duration}>
            <Visual visual={v} durationInFrames={duration} />
          </Sequence>
        );
      })}

      {props.emojis.map((e, i) => {
        const duration = Math.max(1, sec(e.end - e.start, fps));
        return (
          <Sequence key={i} name={`Emoji ${i + 1}`} from={sec(e.start, fps)} durationInFrames={duration}>
            <FloatingEmoji src={e.src} size={e.size} position={e.position} durationInFrames={duration} />
          </Sequence>
        );
      })}

      {props.cards.map((c, i) => {
        const duration = Math.max(1, sec(c.end - c.start, fps));
        return (
          <Sequence key={i} name={`Card ${c.type}`} from={sec(c.start, fps)} durationInFrames={duration}>
            <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", paddingBottom: 260 }}>
              <ReelCard card={c} durationInFrames={duration} />
            </AbsoluteFill>
          </Sequence>
        );
      })}

      {props.hook ? (
        <Sequence name="Hook" from={sec(props.hook.start, fps)} durationInFrames={Math.max(1, sec(props.hook.end - props.hook.start, fps))}>
          <Hook text={props.hook.text} emoji={props.hook.emoji} durationInFrames={Math.max(1, sec(props.hook.end - props.hook.start, fps))} />
        </Sequence>
      ) : null}

      <Captions pages={props.captionPages} />

      {props.cta ? (
        <Sequence name="CTA" from={sec(props.cta.start, fps)}>
          <Cta text={props.cta.text} icon={props.cta.icon} emoji={props.cta.emoji} />
        </Sequence>
      ) : null}

      <ProgressBar />
      {props.logo ? <Watermark src={props.logo} /> : null}

      {props.bgm ? (
        <Audio
          src={asset(props.bgm.src)}
          loop
          loopVolumeCurveBehavior="extend"
          volume={(f) => {
            const now = f / fps;
            const end = props.durationInSeconds;
            const fade = interpolate(now, [0, 0.8, end - 1.5, end], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
            if (!props.bgm!.ducking) return props.bgm!.volume * fade;
            // ±0.25s oynada nutq ulushi -> silliq ducking (keskin sakrashsiz)
            const window = 0.25;
            let covered = 0;
            for (const [a, b] of speech) {
              covered += Math.max(0, Math.min(b, now + window) - Math.max(a, now - window));
            }
            const amount = Math.min(1, covered / (2 * window));
            return fade * (props.bgm!.volume + (props.bgm!.duckVolume - props.bgm!.volume) * amount);
          }}
        />
      ) : null}
      {props.sfx.map((s, i) => (
        <Sequence key={`sfx${i}`} name={`SFX ${i + 1}`} from={sec(s.at, fps)} layout="none">
          <Audio src={asset(s.src)} volume={s.volume} />
        </Sequence>
      ))}
      {props.voiceovers.map((s, i) => (
        <Sequence key={`vo${i}`} name={`TTS ${i + 1}`} from={sec(s.at, fps)} layout="none">
          <Audio src={asset(s.src)} volume={s.volume} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

// Sequence ichida useVideoConfig().durationInFrames butun videoniki bo'ladi — shuning uchun davomiylik prop orqali
const Visual: React.FC<{ visual: ReelProps["visuals"][number]; durationInFrames: number }> = ({ visual, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const fade = interpolate(frame, [0, 0.15 * fps, durationInFrames - 0.15 * fps, durationInFrames], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  if (visual.kind === "clip") {
    return (
      <AbsoluteFill style={{ opacity: fade }}>
        <Video src={asset(visual.src)} muted objectFit="cover" style={{ width: "100%", height: "100%" }} />
      </AbsoluteFill>
    );
  }
  if (visual.kind === "broll") {
    // Ken Burns: 1.0x -> 1.12x
    return (
      <AbsoluteFill style={{ opacity: fade, overflow: "hidden" }}>
        <Img
          src={asset(visual.src)}
          style={{ width: "100%", height: "100%", objectFit: "cover", scale: interpolate(frame, [0, durationInFrames], [1, 1.12]) }}
        />
      </AbsoluteFill>
    );
  }
  const pop = spring({ frame, fps, config: { damping: 11, stiffness: 160 } });
  const top = { top: safeZone.top + 40, center: 560, bottom: 1000 }[visual.position];
  return (
    <AbsoluteFill style={{ alignItems: "center" }}>
      <Img
        src={asset(visual.src)}
        style={{
          position: "absolute",
          top,
          width: 620,
          height: 620,
          objectFit: "contain",
          opacity: fade,
          scale: interpolate(pop, [0, 1], [0.4, 1]),
          rotate: `${interpolate(pop, [0, 1], [-8, 0])}deg`,
          filter: "drop-shadow(0 24px 40px rgba(0,0,0,0.5))",
        }}
      />
    </AbsoluteFill>
  );
};

const FloatingEmoji: React.FC<{
  src: string;
  size: number;
  position: "top" | "center" | "left" | "right";
  durationInFrames: number;
}> = ({ src, size, position, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  const pop = spring({ frame, fps, config: { damping: 10, stiffness: 170 } });
  const out = interpolate(frame, [durationInFrames - 0.2 * fps, durationInFrames], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const place = {
    top: { left: (width - size) / 2, top: safeZone.top + 60 },
    center: { left: (width - size) / 2, top: 700 },
    left: { left: safeZone.left, top: 620 },
    right: { left: width - safeZone.right - size, top: 620 },
  }[position];
  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          ...place,
          opacity: out,
          scale: interpolate(pop, [0, 1], [0.2, 1]),
          translate: `0px ${Math.sin(frame / 14) * 10}px`,
        }}
      >
        <Emoji src={src} size={size} />
      </div>
    </AbsoluteFill>
  );
};

const Hook: React.FC<{ text: string; emoji: string; durationInFrames: number }> = ({ text, emoji, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 13 } });
  const out = interpolate(frame, [durationInFrames - 0.2 * fps, durationInFrames], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ alignItems: "center", paddingTop: safeZone.top, paddingLeft: 80, paddingRight: 80 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 20,
          opacity: out,
          translate: `0px ${interpolate(enter, [0, 1], [-80, 0])}px`,
          background: "rgba(10,22,49,0.82)",
          border: `3px solid ${colors.accent}`,
          borderRadius: 36,
          padding: "22px 36px",
          boxShadow: "0 20px 60px rgba(0,0,0,0.45)",
        }}
      >
        <Emoji src={emoji} size={110} style={{ scale: interpolate(enter, [0, 1], [0.3, 1]) }} />
        <div
          style={{
            fontFamily: headingFont,
            fontWeight: 900,
            fontSize: 72,
            lineHeight: 1.05,
            textAlign: "center",
            textTransform: "uppercase",
            backgroundImage: brandTextGradient,
            backgroundClip: "text",
            WebkitBackgroundClip: "text",
            color: "transparent",
          }}
        >
          {text}
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Cta: React.FC<{ text: string; icon: string; emoji: string }> = ({ text, icon, emoji }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 12 } });
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: safeZone.bottom + 300 }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10, scale: interpolate(enter, [0, 1], [0.6, 1]), opacity: enter }}>
        <Emoji src={emoji} size={120} style={{ translate: `0px ${Math.sin(frame / 8) * 8}px` }} />
        <Chip icon={icon} tone="brand" size={46}>
          {text}
        </Chip>
      </div>
    </AbsoluteFill>
  );
};

// Instagram "Reels" yozuvidan pastda, hook'dan yuqorida — butun video davomida
const Watermark: React.FC<{ src: string }> = ({ src }) => (
  <AbsoluteFill style={{ alignItems: "center" }}>
    <Img src={asset(src)} style={{ position: "absolute", top: 150, height: 58, objectFit: "contain", opacity: 0.9 }} />
  </AbsoluteFill>
);

const ProgressBar: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", top: 0, left: 0, height: 8, width: `${(frame / durationInFrames) * 100}%`, background: brandGradient }} />
    </AbsoluteFill>
  );
};
