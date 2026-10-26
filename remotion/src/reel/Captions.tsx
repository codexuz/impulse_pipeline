import React from "react";
import { AbsoluteFill, Easing, interpolate, Sequence, useCurrentFrame, useVideoConfig } from "remotion";
import { headingFont } from "../fonts";
import { colors, safeZone, STYLE_COLORS } from "../theme";
import type { CaptionPage } from "./schema";

// 1–3 so'zli sahifalar; aytilayotgan so'z kattalashadi, kalit so'zlar brend rangida
export const Captions: React.FC<{ pages: CaptionPage[] }> = ({ pages }) => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill>
      {pages.map((page, i) => {
        const from = Math.round((page.startMs / 1000) * fps);
        const duration = Math.max(1, Math.round(((page.endMs - page.startMs) / 1000) * fps));
        return (
          <Sequence key={i} from={from} durationInFrames={duration} name={`Caption ${i + 1}`} layout="none">
            <Page page={page} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

const Page: React.FC<{ page: CaptionPage }> = ({ page }) => {
  const frame = useCurrentFrame();
  const { fps, height } = useVideoConfig();
  const nowMs = page.startMs + (frame / fps) * 1000;

  return (
    <AbsoluteFill
      style={{
        top: height - safeZone.bottom - 260,
        height: 260,
        justifyContent: "center",
        alignItems: "center",
        paddingLeft: safeZone.left,
        paddingRight: safeZone.right,
      }}
    >
      <div
        style={{
          fontFamily: headingFont,
          fontWeight: 900,
          fontSize: 78,
          lineHeight: 1.1,
          textAlign: "center",
          textTransform: "uppercase",
          color: colors.text,
          WebkitTextStroke: "14px rgba(0,0,0,0.9)",
          paintOrder: "stroke fill",
          textShadow: "0 8px 24px rgba(0,0,0,0.55)",
          scale: interpolate(frame, [0, 0.12 * fps], [0.86, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
        }}
      >
        {page.words.map((w, i) => {
          const active = nowMs >= w.startMs && nowMs < w.endMs;
          return (
            <span
              key={i}
              style={{
                display: "inline-block",
                marginRight: i < page.words.length - 1 ? 34 : 0,
                color: w.style ? STYLE_COLORS[w.style] : colors.text,
                scale: active ? 1.08 : 1,
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
