// Google Fonts: brand_preset.json -> typography.heading / typography.body dan tanlanadi.
// Faqat tanlangan ikkita shrift yuklanadi; yangi shrift qo'shish uchun shu ro'yxatga qator qo'shing.
import { loadFont as bebasNeue } from "@remotion/google-fonts/BebasNeue";
import { loadFont as inter } from "@remotion/google-fonts/Inter";
import { loadFont as manrope } from "@remotion/google-fonts/Manrope";
import { loadFont as montserrat } from "@remotion/google-fonts/Montserrat";
import { loadFont as nunito } from "@remotion/google-fonts/Nunito";
import { loadFont as oswald } from "@remotion/google-fonts/Oswald";
import { loadFont as playfairDisplay } from "@remotion/google-fonts/PlayfairDisplay";
import { loadFont as poppins } from "@remotion/google-fonts/Poppins";
import { loadFont as rubik } from "@remotion/google-fonts/Rubik";
import { loadFont as unbounded } from "@remotion/google-fonts/Unbounded";
import { typography } from "./theme";

// O'zbek lotin harflari (oʻ, gʻ) uchun latin-ext ham yuklanadi
const subsets: ["latin", "latin-ext"] = ["latin", "latin-ext"];

const LOADERS: Record<string, () => string> = {
  Montserrat: () => montserrat("normal", { weights: ["500", "700", "800", "900"], subsets }).fontFamily,
  Inter: () => inter("normal", { weights: ["400", "500", "600", "700"], subsets }).fontFamily,
  Poppins: () => poppins("normal", { weights: ["400", "600", "700", "800"], subsets }).fontFamily,
  Unbounded: () => unbounded("normal", { weights: ["500", "700", "900"], subsets }).fontFamily,
  Manrope: () => manrope("normal", { weights: ["400", "600", "800"], subsets }).fontFamily,
  Rubik: () => rubik("normal", { weights: ["400", "600", "800"], subsets }).fontFamily,
  "Bebas Neue": () => bebasNeue("normal", { weights: ["400"], subsets }).fontFamily,
  "Playfair Display": () => playfairDisplay("normal", { weights: ["600", "800", "900"], subsets }).fontFamily,
  Nunito: () => nunito("normal", { weights: ["400", "700", "900"], subsets }).fontFamily,
  Oswald: () => oswald("normal", { weights: ["400", "600", "700"], subsets }).fontFamily,
};

const load = (name: string, fallback: string) => (LOADERS[name] ?? LOADERS[fallback])();

export const headingFont = load(typography.heading, "Montserrat");
export const bodyFont =
  typography.body === typography.heading ? headingFont : load(typography.body, "Inter");
