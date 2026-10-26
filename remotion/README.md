# Remotion — faqat video (Reels)

Remotion bu loyihada **faqat video yaratish va montaj** uchun. Posterlar va Reels muqovalari Figma'da
(`scripts/poster_studio.py` + `scripts/figma/render_poster.js`, artwork — Google Flow) yaratiladi.

Kompozitsiyalar: `Reel` (oddiy Reels montaji) va `Studio` (`src/studio/` — `matte_video.py` kesib olgan spiker animatsion
Impulse studiyasida: nur, halo, bokeh, rim light + soya, karaoke subtitr, badge, callout, headline, end card, SFX, BGM ducking;
`scripts/studio_render.py`).

`scripts/render_pipeline.py render` fayllarni `public/runs/<run_id>/` ga joylaydi, props JSON yozadi va
`npx remotion render Reel` ni ishga tushiradi.

| Kompozitsiya | O'lcham | Tarkibi |
| :--- | :--- | :--- |
| `Reel` | 1080x1920, 60 fps, davomiylik props'dan | Zoom punch-in, Flow B-roll/clip/stiker, Fluent 3D emojilar, `compare`/`band_meter`/`callout` kartalari, rangli subtitrlar, hook, CTA, Impulse watermark, BGM ducking, SFX, TTS |

- Ranglar, shriftlar, profil: `../config/brand_preset.json` (`src/theme.ts`, `src/fonts.ts`).
- Ikonkalar: `lucide-react` (PascalCase nom) va Iconify `simple-icons:<nom>` (Telegram, Instagram) — `src/components/primitives.tsx -> Icon`.
- Emojilar: Fluent 3D PNG (`scripts/fluent_emoji.py` yuklaydi).

```bash
npm install
npm run dev     # Studio: Reel'ni namunaviy props bilan ko'rish
npm run lint    # eslint + tsc
```
