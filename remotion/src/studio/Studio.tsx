import { Audio } from "@remotion/media";
import React, { useMemo } from "react";
import {
  AbsoluteFill,
  CalculateMetadataFunction,
  Composition,
  Easing,
  Freeze,
  Img,
  interpolate,
  OffthreadVideo,
  random,
  Sequence,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { asset, Icon } from "../components/primitives";
import { bodyFont, headingFont } from "../fonts";
import { brandGradient, brandTextGradient, colors, rgba } from "../theme";
import { type StudioProps, studioSchema } from "./schema";

// "Studio" — the speaker cut out of their background (scripts/matte_video.py) and placed in an animated
// Impulse studio: light beams, halo, bokeh, rim light + soft shadow on the person, karaoke captions,
// badges, callout cards, kinetic headlines, end card, SFX and ducked music.

const calculateMetadata: CalculateMetadataFunction<StudioProps> = ({ props }) => ({
  fps: props.fps,
  durationInFrames: Math.max(1, Math.ceil(props.durationInSeconds * props.fps)),
});

export const StudioComposition = () => (
  <Composition
    id="Studio"
    component={Studio}
    schema={studioSchema}
    width={1080}
    height={1920}
    fps={60}
    durationInFrames={300}
    calculateMetadata={calculateMetadata}
    defaultProps={{
      fps: 60,
      durationInSeconds: 5,
      matte: "",
      matteDuration: 5,
      logo: "",
      voiceVolume: 1,
      subject: { scale: 1, offsetY: 0 },
      captionPages: [],
      zooms: [],
      emojis: [],
      badges: [],
      callouts: [],
      headlines: [],
      endCard: null,
      bgm: null,
      sfx: [],
    }}
  />
);

const sec = (s: number, fps: number) => Math.round(s * fps);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const easeOut = Easing.bezier(0.16, 1, 0.3, 1);

export const Studio: React.FC<StudioProps> = (props) => {
  const { fps } = useVideoConfig();
  const frame = useCurrentFrame();
  const t = frame / fps;

  // Camera: smooth punch-ins that stack, background moves less (parallax)
  const zoom = props.zooms.reduce((acc, z) => {
    const inOut = interpolate(t, [z.start, z.start + 0.35, z.end - 0.3, z.end], [0, 1, 1, 0], { ...clamp, easing: easeOut });
    return acc + (z.scale - 1) * inOut;
  }, 1);

  const speech = useMemo(
    () => props.captionPages.flatMap((p) => p.words.map((w) => [w.start, w.end] as const)),
    [props.captionPages],
  );
  const matteFrames = Math.floor(props.matteDuration * fps) - 1;
  const endStart = props.endCard?.start ?? Infinity;

  return (
    <AbsoluteFill style={{ backgroundColor: colors.navy, overflow: "hidden" }}>
      <AbsoluteFill style={{ scale: 1 + (zoom - 1) * 0.35 }}>
        <StudioBackground />
      </AbsoluteFill>

      {props.headlines.map((h, i) => (
        <Sequence key={`bd${i}`} name={`Backdrop ${h.backdrop}`} from={sec(h.start, fps)} durationInFrames={sec(h.end - h.start, fps)}>
          <BackdropWord text={h.backdrop} durationInFrames={sec(h.end - h.start, fps)} />
        </Sequence>
      ))}

      {/* The person: graded cut-out with rim light and a soft shadow on the backdrop */}
      <AbsoluteFill style={{ scale: zoom, transformOrigin: "50% 42%" }}>
        <Subject {...props} matteFrames={matteFrames} />
      </AbsoluteFill>

      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 45%, transparent 55%, ${rgba("#020617", 0.55)} 100%)` }} />

      {props.emojis.map((e, i) => {
        const d = Math.max(1, sec(e.end - e.start, fps));
        return (
          <Sequence key={`e${i}`} name={`Emoji ${i + 1}`} from={sec(e.start, fps)} durationInFrames={d}>
            <PopEmoji emoji={e} durationInFrames={d} />
          </Sequence>
        );
      })}
      {props.badges.map((b, i) => {
        const d = Math.max(1, sec(b.end - b.start, fps));
        return (
          <Sequence key={`b${i}`} name={`Badge ${b.text}`} from={sec(b.start, fps)} durationInFrames={d}>
            <Badge badge={b} durationInFrames={d} />
          </Sequence>
        );
      })}
      {props.callouts.map((c, i) => {
        const d = Math.max(1, sec(c.end - c.start, fps));
        return (
          <Sequence key={`c${i}`} name={`Callout ${c.title}`} from={sec(c.start, fps)} durationInFrames={d}>
            <Callout callout={c} durationInFrames={d} />
          </Sequence>
        );
      })}
      {props.headlines.map((h, i) => {
        const d = Math.max(1, sec(h.end - h.start, fps));
        return (
          <Sequence key={`h${i}`} name={`Headline ${h.text}`} from={sec(h.start, fps)} durationInFrames={d}>
            <Headline headline={h} durationInFrames={d} />
          </Sequence>
        );
      })}

      {props.captionPages.map((p, i) => {
        const from = sec(p.start, fps);
        const d = Math.max(1, sec(Math.min(p.end, endStart) - p.start, fps));
        return (
          <Sequence key={`cap${i}`} name={`Caption ${i + 1}`} from={from} durationInFrames={d} layout="none">
            <CaptionPage page={p} durationInFrames={d} />
          </Sequence>
        );
      })}

      {props.endCard ? (
        <Sequence name="End card" from={sec(props.endCard.start, fps)}>
          <EndCard card={props.endCard} logo={props.logo} />
        </Sequence>
      ) : null}

      {props.logo ? <Watermark src={props.logo} hideAt={endStart} hidden={props.headlines.map((h) => [h.start, h.end] as const)} /> : null}
      <LightSweep />

      {props.bgm ? (
        <Audio
          src={asset(props.bgm.src)}
          loop
          loopVolumeCurveBehavior="extend"
          volume={(f) => {
            const now = f / fps;
            const end = props.durationInSeconds;
            const fade = interpolate(now, [0, 0.5, end - 1.2, end], [0, 1, 1, 0], clamp);
            const window = 0.25;
            let covered = 0;
            for (const [a, b] of speech) covered += Math.max(0, Math.min(b, now + window) - Math.max(a, now - window));
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
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// Studio set
// ---------------------------------------------------------------------------

const StudioBackground: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const t = frame / fps;
  const on = interpolate(t, [0, 0.7], [0, 1], { ...clamp, easing: easeOut });
  const breathe = 0.85 + 0.15 * Math.sin(t * 1.4);

  const bokeh = useMemo(
    () =>
      new Array(16).fill(0).map((_, i) => ({
        x: random(`bx${i}`) * width,
        y: random(`by${i}`) * height,
        r: 18 + random(`br${i}`) * 70,
        speed: 8 + random(`bs${i}`) * 22,
        alpha: 0.08 + random(`ba${i}`) * 0.18,
        blur: 4 + random(`bb${i}`) * 14,
      })),
    [width, height],
  );

  return (
    <AbsoluteFill style={{ opacity: on }}>
      {/* Back wall: deep navy with a lit centre */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 85% 55% at 50% 40%, ${colors.surface} 0%, ${colors.navy} 55%, #040A1A 100%)`,
        }}
      />
      {/* Key spotlight behind the speaker */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 48% 30% at 50% 44%, ${rgba(colors.glow, 0.32 * breathe)} 0%, ${rgba(colors.accent, 0.12)} 45%, transparent 75%)`,
        }}
      />
      {/* Light beams from the rig */}
      {[-24, 0, 22].map((angle, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: width / 2 - 170,
            top: -260,
            width: 340,
            height: 1500,
            transformOrigin: "50% 0%",
            rotate: `${angle + Math.sin(t * 0.6 + i * 1.7) * 3}deg`,
            background: `linear-gradient(180deg, ${rgba(colors.glow, 0.2)} 0%, ${rgba(colors.glow, 0.05)} 55%, transparent 100%)`,
            filter: "blur(24px)",
            mixBlendMode: "screen",
          }}
        />
      ))}
      {/* Halo ring behind the head */}
      <div
        style={{
          position: "absolute",
          left: width / 2 - 400,
          top: 360,
          width: 800,
          height: 800,
          borderRadius: "50%",
          border: `3px solid ${rgba(colors.glow, 0.28)}`,
          boxShadow: `0 0 60px ${rgba(colors.accent, 0.25)}, inset 0 0 60px ${rgba(colors.accent, 0.18)}`,
          scale: interpolate(t, [0, 1.2], [0.85, 1], { ...clamp, easing: easeOut }),
        }}
      />
      <div
        style={{
          position: "absolute",
          left: width / 2 - 460,
          top: 300,
          width: 920,
          height: 920,
          borderRadius: "50%",
          background: `conic-gradient(from ${t * 40}deg, transparent 0deg, ${rgba(colors.glow, 0.55)} 40deg, transparent 90deg, transparent 180deg, ${rgba(colors.accent, 0.4)} 220deg, transparent 270deg)`,
          WebkitMask: "radial-gradient(circle, transparent 448px, black 450px, black 456px, transparent 458px)",
          mask: "radial-gradient(circle, transparent 448px, black 450px, black 456px, transparent 458px)",
        }}
      />
      {/* Bokeh drifting up */}
      {bokeh.map((b, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: b.x - b.r,
            top: ((b.y - t * b.speed) % height + height) % height - b.r,
            width: b.r * 2,
            height: b.r * 2,
            borderRadius: "50%",
            background: `radial-gradient(circle, ${rgba(colors.glow, b.alpha)} 0%, transparent 70%)`,
            filter: `blur(${b.blur}px)`,
          }}
        />
      ))}
      {/* Floor glow */}
      <AbsoluteFill style={{ background: `linear-gradient(0deg, ${rgba(colors.brandDark, 0.35)} 0%, transparent 28%)` }} />
    </AbsoluteFill>
  );
};

const Subject: React.FC<StudioProps & { matteFrames: number }> = ({ matte, voiceVolume, subject, matteFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const reveal = interpolate(t, [0.05, 0.6], [0, 1], { ...clamp, easing: easeOut });
  if (!matte) return null;
  const style: React.CSSProperties = {
    position: "absolute",
    width: "100%",
    height: "100%",
    objectFit: "cover",
    // Rim light (brand blue) + soft contact shadow on the backdrop: the person sits in the set, not on top of it
    filter: `drop-shadow(0 0 18px ${rgba(colors.glow, 0.45)}) drop-shadow(28px 36px 46px rgba(0,0,0,0.55))`,
  };
  return (
    <AbsoluteFill
      style={{
        opacity: reveal,
        scale: subject.scale * interpolate(reveal, [0, 1], [1.06, 1]),
        translate: `0 ${subject.offsetY}px`,
        filter: `blur(${interpolate(reveal, [0, 1], [18, 0])}px)`,
      }}
    >
      <Sequence durationInFrames={matteFrames} layout="none">
        <OffthreadVideo src={asset(matte)} transparent volume={voiceVolume} style={style} />
      </Sequence>
      {/* After the clip ends the last frame holds under the end card */}
      <Sequence from={matteFrames} layout="none">
        <Freeze frame={matteFrames - 1}>
          <OffthreadVideo src={asset(matte)} transparent muted style={style} />
        </Freeze>
      </Sequence>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// Graphics
// ---------------------------------------------------------------------------

const useInOut = (durationInFrames: number, inSec = 0.45, outSec = 0.25) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 14, stiffness: 140 }, durationInFrames: Math.round(inSec * fps) });
  const exit = interpolate(frame, [durationInFrames - outSec * fps, durationInFrames], [1, 0], { ...clamp, easing: Easing.in(Easing.cubic) });
  return { enter, exit, frame, fps };
};

const CaptionPage: React.FC<{ page: StudioProps["captionPages"][number]; durationInFrames: number }> = ({ page, durationInFrames }) => {
  const { enter, exit, frame, fps } = useInOut(durationInFrames, 0.3, 0.15);
  const now = page.start + frame / fps;
  return (
    <AbsoluteFill style={{ top: 1390, height: 240, justifyContent: "center", alignItems: "center", padding: "0 70px" }}>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          gap: "6px 10px",
          opacity: exit,
          translate: `0 ${interpolate(enter, [0, 1], [40, 0])}px`,
          scale: interpolate(enter, [0, 1], [0.9, 1]),
        }}
      >
        {page.words.map((w, i) => {
          const active = now >= w.start && now < w.end + 0.05;
          const lit = interpolate(now, [w.start - 0.06, w.start + 0.06], [0, 1], clamp);
          return (
            <span
              key={i}
              style={{
                fontFamily: headingFont,
                fontWeight: 900,
                fontSize: 74,
                lineHeight: 1.15,
                padding: "2px 18px 6px",
                borderRadius: 18,
                color: w.highlight && !active ? colors.english : colors.text,
                background: active ? brandGradient : "transparent",
                boxShadow: active ? `0 10px 30px ${rgba(colors.accent, 0.45)}` : "none",
                opacity: interpolate(lit, [0, 1], [0.55, 1]),
                scale: active ? 1.06 : 1,
                textShadow: active ? "none" : "0 4px 18px rgba(0,0,0,0.75), 0 0 2px rgba(0,0,0,0.9)",
              }}
            >
              {w.text}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const PopEmoji: React.FC<{ emoji: StudioProps["emojis"][number]; durationInFrames: number }> = ({ emoji, durationInFrames }) => {
  const { enter, exit, frame, fps } = useInOut(durationInFrames, 0.5, 0.2);
  return (
    <Img
      src={asset(emoji.src)}
      style={{
        position: "absolute",
        left: emoji.x - emoji.size / 2,
        top: emoji.y - emoji.size / 2 + Math.sin((frame / fps) * 3) * 10,
        width: emoji.size,
        height: emoji.size,
        objectFit: "contain",
        opacity: exit,
        scale: interpolate(enter, [0, 1], [0.2, 1]) * interpolate(exit, [0, 1], [0.6, 1]),
        rotate: `${emoji.rotate + interpolate(enter, [0, 1], [-25, 0])}deg`,
        filter: "drop-shadow(0 20px 30px rgba(0,0,0,0.5))",
      }}
    />
  );
};

const Badge: React.FC<{ badge: StudioProps["badges"][number]; durationInFrames: number }> = ({ badge, durationInFrames }) => {
  const { enter, exit } = useInOut(durationInFrames);
  return (
    <AbsoluteFill style={{ alignItems: "center", top: 300 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 18,
          padding: "20px 36px 20px 24px",
          borderRadius: 999,
          background: rgba("#0B1530", 0.72),
          border: `2px solid ${rgba(colors.glow, 0.6)}`,
          boxShadow: `0 18px 50px rgba(0,0,0,0.45), 0 0 30px ${rgba(colors.accent, 0.3)}`,
          backdropFilter: "blur(16px)",
          opacity: exit,
          translate: `0 ${interpolate(enter, [0, 1], [-60, 0])}px`,
          scale: interpolate(enter, [0, 1], [0.8, 1]),
        }}
      >
        <div style={{ width: 64, height: 64, borderRadius: "50%", background: brandGradient, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Icon name={badge.icon} size={36} color="#fff" />
        </div>
        <span style={{ fontFamily: headingFont, fontWeight: 800, fontSize: 40, letterSpacing: 3, color: colors.text, textTransform: "uppercase" }}>
          {badge.text}
        </span>
      </div>
    </AbsoluteFill>
  );
};

const Callout: React.FC<{ callout: StudioProps["callouts"][number]; durationInFrames: number }> = ({ callout, durationInFrames }) => {
  const { enter, exit } = useInOut(durationInFrames, 0.55, 0.3);
  const fromSide = callout.side === "right" ? 1 : -1;
  return (
    <div
      style={{
        position: "absolute",
        top: callout.y,
        [callout.side]: 56,
        padding: "34px 44px 34px 40px",
        borderRadius: 34,
        background: `linear-gradient(135deg, ${rgba("#13254A", 0.88)}, ${rgba("#0A1631", 0.82)})`,
        border: `2px solid ${rgba(colors.glow, 0.55)}`,
        boxShadow: `0 30px 70px rgba(0,0,0,0.5), 0 0 40px ${rgba(colors.accent, 0.25)}`,
        backdropFilter: "blur(18px)",
        opacity: exit,
        translate: `${interpolate(enter, [0, 1], [fromSide * 520, 0])}px 0`,
        rotate: `${interpolate(enter, [0, 1], [fromSide * 6, 0])}deg`,
      }}
    >
      {callout.emoji ? (
        <Img
          src={asset(callout.emoji)}
          style={{
            position: "absolute",
            top: -95,
            [callout.side === "right" ? "left" : "right"]: -105,
            width: 150,
            height: 150,
            scale: interpolate(enter, [0.4, 1], [0, 1], clamp),
            filter: "drop-shadow(0 16px 24px rgba(0,0,0,0.5))",
          }}
        />
      ) : null}
      <div
        style={{
          fontFamily: headingFont,
          fontWeight: 900,
          fontSize: 76,
          lineHeight: 1,
          letterSpacing: 2,
          backgroundImage: brandTextGradient,
          backgroundClip: "text",
          WebkitBackgroundClip: "text",
          color: "transparent",
        }}
      >
        {callout.title}
      </div>
      <div style={{ fontFamily: bodyFont, fontWeight: 700, fontSize: 44, color: colors.text, marginTop: 10 }}>{callout.subtitle}</div>
      <div
        style={{
          marginTop: 18,
          height: 6,
          borderRadius: 3,
          width: `${interpolate(enter, [0.3, 1], [0, 100], clamp)}%`,
          background: brandGradient,
          boxShadow: `0 0 16px ${rgba(colors.glow, 0.8)}`,
        }}
      />
    </div>
  );
};

const BackdropWord: React.FC<{ text: string; durationInFrames: number }> = ({ text, durationInFrames }) => {
  const { enter, exit, frame, fps } = useInOut(durationInFrames, 0.6, 0.4);
  if (!text) return null;
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", top: -330 }}>
      <div
        style={{
          fontFamily: headingFont,
          fontWeight: 900,
          fontSize: 330,
          letterSpacing: -6,
          color: "transparent",
          WebkitTextStroke: `4px ${rgba(colors.glow, 0.55)}`,
          textShadow: `0 0 50px ${rgba(colors.accent, 0.35)}`,
          opacity: exit * enter,
          scale: interpolate(frame / fps, [0, durationInFrames / fps], [1.15, 1.0]),
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};

const Headline: React.FC<{ headline: StudioProps["headlines"][number]; durationInFrames: number }> = ({ headline, durationInFrames }) => {
  const { enter, exit, frame, fps } = useInOut(durationInFrames, 0.5, 0.3);
  const accentIn = spring({ frame: frame - 0.25 * fps, fps, config: { damping: 12, stiffness: 150 } });
  return (
    <AbsoluteFill style={{ alignItems: "center", top: 280 }}>
      <div style={{ textAlign: "center", opacity: exit }}>
        <div
          style={{
            fontFamily: headingFont,
            fontWeight: 800,
            fontSize: 56,
            letterSpacing: 6,
            color: colors.text,
            textTransform: "uppercase",
            translate: `0 ${interpolate(enter, [0, 1], [-40, 0])}px`,
            opacity: enter,
            textShadow: "0 6px 24px rgba(0,0,0,0.6)",
          }}
        >
          {headline.text}
        </div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 18 }}>
          <span
            style={{
              fontFamily: headingFont,
              fontWeight: 900,
              fontStyle: "italic",
              fontSize: 132,
              lineHeight: 1.05,
              backgroundImage: brandTextGradient,
              backgroundClip: "text",
              WebkitBackgroundClip: "text",
              color: "transparent",
              filter: `drop-shadow(0 10px 30px ${rgba(colors.accent, 0.45)})`,
              scale: interpolate(accentIn, [0, 1], [0.6, 1]),
              opacity: accentIn,
            }}
          >
            {headline.accent}
          </span>
          {headline.emoji ? (
            <Img
              src={asset(headline.emoji)}
              style={{
                width: 140,
                height: 140,
                scale: interpolate(accentIn, [0, 1], [0, 1]),
                rotate: `${interpolate(accentIn, [0, 1], [-30, 8])}deg`,
                filter: "drop-shadow(0 16px 24px rgba(0,0,0,0.5))",
              }}
            />
          ) : null}
        </div>
      </div>
    </AbsoluteFill>
  );
};

const EndCard: React.FC<{ card: NonNullable<StudioProps["endCard"]>; logo: string }> = ({ card, logo }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 15, stiffness: 120 } });
  return (
    <AbsoluteFill>
      <AbsoluteFill
        style={{
          background: `linear-gradient(180deg, transparent 35%, ${rgba("#040A1A", 0.75)} 62%, ${rgba("#040A1A", 0.92)} 100%)`,
          opacity: interpolate(frame, [0, 0.4 * fps], [0, 1], clamp),
        }}
      />
      <AbsoluteFill style={{ top: 1060, alignItems: "center" }}>
        <div
          style={{
            width: 900,
            padding: "46px 56px 50px",
            borderRadius: 40,
            background: `linear-gradient(160deg, ${rgba("#13254A", 0.9)}, ${rgba("#0A1631", 0.92)})`,
            border: `2px solid ${rgba(colors.glow, 0.5)}`,
            boxShadow: `0 40px 90px rgba(0,0,0,0.6), 0 0 50px ${rgba(colors.accent, 0.25)}`,
            backdropFilter: "blur(20px)",
            translate: `0 ${interpolate(enter, [0, 1], [380, 0])}px`,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 26,
          }}
        >
          {logo ? <Img src={asset(logo)} style={{ height: 96, objectFit: "contain" }} /> : null}
          <div style={{ fontFamily: headingFont, fontWeight: 800, fontSize: 46, color: colors.text, textAlign: "center" }}>{card.title}</div>
          <div style={{ width: "100%", height: 3, background: brandGradient, borderRadius: 2, boxShadow: `0 0 14px ${rgba(colors.glow, 0.8)}` }} />
          {card.contacts.map((c, i) => {
            const item = spring({ frame: frame - (0.35 + i * 0.12) * fps, fps, config: { damping: 14, stiffness: 160 } });
            return (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 22,
                  alignSelf: "stretch",
                  opacity: item,
                  translate: `${interpolate(item, [0, 1], [-60, 0])}px 0`,
                }}
              >
                <div style={{ width: 70, height: 70, borderRadius: 20, background: brandGradient, display: "flex", alignItems: "center", justifyContent: "center", flex: "none" }}>
                  <Icon name={c.icon} size={38} color="#fff" />
                </div>
                <span style={{ fontFamily: bodyFont, fontWeight: 700, fontSize: 48, color: colors.text }}>{c.text}</span>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// Fades out under headlines (same top area) and before the end card, which shows the logo itself
const Watermark: React.FC<{ src: string; hideAt: number; hidden: (readonly [number, number])[] }> = ({ src, hideAt, hidden }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const under = Math.max(0, ...hidden.map(([a, b]) => interpolate(t, [a - 0.2, a, b - 0.2, b], [0, 1, 1, 0], clamp)));
  return (
    <Img
      src={asset(src)}
      style={{
        position: "absolute",
        left: 64,
        top: 240,
        height: 70,
        objectFit: "contain",
        opacity: interpolate(t, [0.4, 0.9, hideAt - 0.2, hideAt], [0, 0.9, 0.9, 0], clamp) * (1 - under),
        filter: "drop-shadow(0 4px 12px rgba(0,0,0,0.5))",
      }}
    />
  );
};

// One soft diagonal light sweep at the start (reveal)
const LightSweep: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  const x = interpolate(frame, [0, 0.9 * fps], [-width, width * 1.4], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  return (
    <AbsoluteFill style={{ pointerEvents: "none", mixBlendMode: "screen" }}>
      <div
        style={{
          position: "absolute",
          top: -400,
          left: x,
          width: 380,
          height: 2800,
          rotate: "18deg",
          background: `linear-gradient(90deg, transparent, ${rgba(colors.glow, 0.28)}, transparent)`,
          filter: "blur(30px)",
        }}
      />
    </AbsoluteFill>
  );
};
