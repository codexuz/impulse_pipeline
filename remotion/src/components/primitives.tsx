import { icons as simpleIcons } from "@iconify-json/simple-icons";
import { getIconData } from "@iconify/utils";
import { icons, type LucideProps } from "lucide-react";
import React from "react";
import { Img, staticFile } from "remotion";
import { bodyFont } from "../fonts";
import { brandGradient, colors, radius } from "../theme";

// Props'dagi yo'llar remotion/public/ ga nisbatan ("runs/<id>/...") yoki to'liq URL bo'ladi
export const asset = (src: string) => (/^https?:\/\//.test(src) ? src : staticFile(src));

// Iconify to'plamlari oflayn (render paytida tarmoq kerak emas). Yangi to'plam: npm i @iconify-json/<prefix>
const ICONIFY_SETS = { "simple-icons": simpleIcons };

/**
 * Ikonka nomi bo'yicha:
 *  - Lucide (PascalCase): "Calendar", "MapPin", "CircleCheck"
 *  - Iconify "prefix:nom": "simple-icons:instagram", "simple-icons:telegram" (brend logotiplari)
 */
export const Icon: React.FC<{ name: string } & LucideProps> = ({ name, size = 24, color = "currentColor", style }) => {
  if (name.includes(":")) {
    const [prefix, iconName] = name.split(":");
    const set = ICONIFY_SETS[prefix as keyof typeof ICONIFY_SETS];
    const data = set ? getIconData(set, iconName) : null;
    if (data) {
      return (
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${data.width ?? 24} ${data.height ?? 24}`}
          style={{ color: color as string, flex: "none", ...style }}
          dangerouslySetInnerHTML={{ __html: data.body }}
        />
      );
    }
  }
  const Component = icons[name as keyof typeof icons] ?? icons.Sparkles;
  return <Component strokeWidth={2.2} size={size} color={color} style={style} />;
};

/** Microsoft Fluent 3D emoji (scripts/fluent_emoji.py yuklagan PNG). */
export const Emoji: React.FC<{ src?: string; size: number; style?: React.CSSProperties }> = ({
  src,
  size,
  style,
}) => {
  if (!src) return null;
  return (
    <Img
      src={asset(src)}
      style={{
        width: size,
        height: size,
        objectFit: "contain",
        filter: "drop-shadow(0 18px 30px rgba(0, 0, 0, 0.45))",
        ...style,
      }}
    />
  );
};

export const Chip: React.FC<{
  icon?: string;
  children: React.ReactNode;
  tone?: "brand" | "gold" | "glass" | "red" | "green";
  size?: number;
  style?: React.CSSProperties;
}> = ({ icon, children, tone = "glass", size = 28, style }) => {
  const tones = {
    brand: { background: brandGradient, color: colors.text, border: "none" },
    gold: { background: colors.award, color: colors.navy, border: "none" },
    glass: { background: "rgba(30,41,59,0.82)", color: colors.text, border: `2px solid ${colors.hairline}` },
    red: { background: colors.mistake, color: colors.text, border: "none" },
    green: { background: colors.correct, color: colors.navy, border: "none" },
  }[tone];
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: size * 0.45,
        padding: `${size * 0.45}px ${size * 0.85}px`,
        borderRadius: 999,
        fontFamily: bodyFont,
        fontWeight: 700,
        fontSize: size,
        ...tones,
        ...style,
      }}
    >
      {icon ? <Icon name={icon} size={size * 1.15} /> : null}
      {children}
    </div>
  );
};

export const Card: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({ children, style }) => (
  <div
    style={{
      background: "rgba(30,41,59,0.86)",
      border: `2px solid rgba(0,153,255,0.32)`,
      borderRadius: radius,
      boxShadow: "0 24px 60px rgba(0,0,0,0.35)",
      ...style,
    }}
  >
    {children}
  </div>
);
