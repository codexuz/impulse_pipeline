// Yagona manba: config/brand_preset.json — ranglar, profil va xavfsiz zona shu yerdan olinadi
import brand from "../../config/brand_preset.json";

const c = brand.colors;

// "#0A1631" -> "rgba(10,22,49,0.8)" — fon ustidagi gradientlar brend rangidan hisoblanadi
export const rgba = (hex: string, alpha: number) => {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${alpha})`;
};

export const colors = {
  text: c.primary_text,
  // Brend ko'ki (Impulse app ikonkasidan): aksent matn/ikonka uchun yorug'i, to'ldirish uchun gradient
  brand: c.brand_primary,
  accent: c.brand_light,
  brandDark: c.brand_dark,
  glow: c.brand_glow,
  navy: c.background_card,
  surface: c.card_surface,
  // Semantik ranglar: kalit so'zlar va Band 5.5 / 8.0
  english: c.highlight_english,
  correct: c.correct_band8,
  mistake: c.mistake_band5,
  // Faqat mukofot (Overall medal, kubok) uchun
  award: c.award_gold,
  muted: "rgba(255, 255, 255, 0.72)",
  hairline: "rgba(255, 255, 255, 0.14)",
};

export const STYLE_COLORS: Record<string, string> = {
  english: colors.english,
  correct: colors.correct,
  mistake: colors.mistake,
};

export const profile = brand.instructor_profile;
export const safeZone = brand.video_settings.safe_zone;
export const radius = brand.design.corner_radius;
export const typography = brand.typography;

/** App ikonkasidagi kabi tepadan pastga ko'k gradient — tugmalar, chiplar, progress uchun (oq matn bilan). */
export const brandGradient = `linear-gradient(180deg, ${colors.accent}, ${colors.brandDark})`;
/** To'q fonda o'qiladigan yorug' ko'k gradient — sarlavha aksentlari uchun (background-clip: text). */
export const brandTextGradient = `linear-gradient(135deg, ${colors.glow}, ${colors.accent})`;
