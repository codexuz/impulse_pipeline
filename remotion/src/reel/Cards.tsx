import React from "react";
import { Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Card, Chip, Icon } from "../components/primitives";
import { bodyFont, headingFont } from "../fonts";
import { brandGradient, colors } from "../theme";
import type { ReelProps } from "./schema";

type CardItem = ReelProps["cards"][number];

/** Sequence ichida ishlaydi: frame 0 = karta chiqqan payt. */
export const ReelCard: React.FC<{ card: CardItem; durationInFrames: number }> = ({ card, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 14, stiffness: 140 } });
  const exit = interpolate(frame, [durationInFrames - 0.25 * fps, durationInFrames], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        opacity: Math.min(enter, exit),
        translate: `0px ${interpolate(enter, [0, 1], [60, 0])}px`,
        scale: interpolate(enter, [0, 1], [0.9, 1]),
      }}
    >
      {card.type === "compare" ? <Compare card={card} /> : null}
      {card.type === "band_meter" ? <BandMeter card={card} /> : null}
      {card.type === "callout" ? (
        <Chip icon={card.icon} tone={card.tone} size={44}>
          {card.text}
        </Chip>
      ) : null}
    </div>
  );
};

// "Don't say X, say Y": qizil X va yashil ✓ qatorlari (oldingi .mov overlay o'rniga)
const Compare: React.FC<{ card: Extract<CardItem, { type: "compare" }> }> = ({ card }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const strongIn = spring({ frame: frame - 0.5 * fps, fps, config: { damping: 12 } });
  const row = (label: string, text: string, good: boolean, progress: number) => (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 24,
        padding: "26px 30px",
        borderRadius: 26,
        background: good ? "rgba(0,230,118,0.14)" : "rgba(255,82,82,0.14)",
        border: `3px solid ${good ? colors.correct : colors.mistake}`,
        opacity: progress,
        scale: interpolate(progress, [0, 1], [0.92, 1]),
      }}
    >
      <Icon name={good ? "CircleCheck" : "CircleX"} size={64} color={good ? colors.correct : colors.mistake} />
      <div>
        <div style={{ fontFamily: bodyFont, fontWeight: 700, fontSize: 28, color: colors.muted, letterSpacing: 2 }}>
          {label}
        </div>
        <div
          style={{
            fontFamily: headingFont,
            fontWeight: 900,
            fontSize: 56,
            color: good ? colors.text : colors.muted,
            textDecoration: good ? "none" : "line-through",
            textDecorationColor: colors.mistake,
          }}
        >
          {text}
        </div>
      </div>
    </div>
  );
  return (
    <Card style={{ padding: 28, display: "flex", flexDirection: "column", gap: 20, width: 840 }}>
      {row(card.weakLabel, card.weak, false, 1)}
      {row(card.strongLabel, card.strong, true, strongIn)}
    </Card>
  );
};

// Band 6.0 -> 8.0 o'sish animatsiyasi
const BandMeter: React.FC<{ card: Extract<CardItem, { type: "band_meter" }> }> = ({ card }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = interpolate(frame, [0.2 * fps, 1.6 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const value = card.from + (card.to - card.from) * t;
  const pct = (v: number) => `${(v / 9) * 100}%`;
  return (
    <Card style={{ padding: "34px 40px", width: 840 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ fontFamily: bodyFont, fontWeight: 700, fontSize: 32, color: colors.muted }}>{card.label}</div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Icon name="TrendingUp" size={48} color={colors.correct} />
          <div style={{ fontFamily: headingFont, fontWeight: 900, fontSize: 80, color: colors.glow }}>
            {value.toFixed(1)}
          </div>
        </div>
      </div>
      <div style={{ position: "relative", height: 34, borderRadius: 999, background: "rgba(255,255,255,0.1)", marginTop: 18 }}>
        <div style={{ position: "absolute", inset: 0, width: pct(value), borderRadius: 999, background: brandGradient }} />
        <div
          style={{
            position: "absolute",
            left: pct(card.from),
            top: -10,
            bottom: -10,
            width: 4,
            background: colors.mistake,
            borderRadius: 2,
          }}
        />
      </div>
    </Card>
  );
};
