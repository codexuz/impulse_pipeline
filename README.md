# Claude Code: Instagram Reels & Poster Pipeline (AI Audio, Video & Design Studio)
**Yo'nalish:** Ingliz tili ustozi va IELTS instruktori (Shaxsiy brend, Kurs reklamalari, IELTS Insightlar, Natijalar va E'lon Posterlari)  
**AI Integratsiyalar:** Figma (posterlar va muqovalar — tahrirlanadigan qatlamlar) + Google Flow (assetlar: matnsiz poster artwork, stiker, B-roll, foto tahriri + Omni/Veo video clip) + ElevenLabs (Scribe STT, SFX, BGM, TTS, Audio Isolation) + Remotion (faqat video yaratish va montaj)  
**Brend:** Impulse Learning Center — logotip `assets/brand/`, ranglar app ikonkasining ko'k gradientidan (`#0099FF → #0779FC → #0F56F9`)  
**Video dizayni:** Google Fonts + Lucide / Iconify ikonkalar + Microsoft Fluent 3D emojilar

Ushbu loyiha **Claude Code** yordamida Instagram Reels videolarini avtomatlashtirilgan holda montaj qilish hamda **reklama, e'lon va IELTS natijalar posterlarini (Feed `4:5`, Story `9:16`, Carousel) rasm sifatida yaratish va mavjud posterlarni tahrirlash** uchun mo'ljallangan universal pipeline hisoblanadi.

## 1. Loyiha Arxitekturasi va Papkalar Tuzilmasi

```text
impulse_pipeline/
├── .env.example                     # ELEVENLABS_API_KEY (+ ixtiyoriy FLOW_OUTPUT_ROOT) shabloni
├── CLAUDE.md                        # Claude Code uchun doimiy tizim qoidalari (Video + Poster Studio)
├── README.md                        # Loyiha hujjati va ishlatish yo'riqnomasi
├── requirements.txt                 # Python: httpx, python-dotenv, pillow
├── config/
│   └── brand_preset.json            # Ranglar, shriftlar, o'lchamlar, Flow va ElevenLabs sozlamalari (yagona manba)
├── assets/                          # Doimiy va AI-generatsiya qilingan brend resurslari
│   ├── brand/
│   │   ├── logo_full_white.png      # Oq Impulse wordmark (shaffof) — Reels watermark
│   │   ├── logo_icon_white.png      # Oq kitob belgisi (shaffof)
│   │   ├── logo_app_icon.png        # Ko'k app ikonkasi — brend ranglari shundan olingan
│   │   └── instructor_cutouts/      # Ustozning foni kesilgan (PNG) portretlari (reklama posterlari uchun reference)
│   ├── elements/                    # Poster assetlari (masalan, trophy_silver_blue.png) — Flow reference sifatida
│   ├── poster_templates/            # Poster maketlari (spec JSON): announcement.json, cover.json
│   ├── emoji/fluent3d/              # Fluent 3D emoji keshi (fluent_emoji.py avtomatik yuklaydi)
│   ├── b_roll/
│   │   ├── ielts_certificates/      # O'quvchilarning Band 7.5 - 8.5 sertifikatlari (TRF blur!)
│   │   ├── classroom_vibes/         # Dars jarayoni, atmosfera, speaking club kadrlari
│   │   ├── writing_checking/        # Essay tekshirish va Band Descriptor tahlili kadrlari
│   │   └── lifestyle/               # Shaxsiy brend: kitob o'qish, qahva, ish stoli, sayohat
│   ├── ai_generated/                # Flow va ElevenLabs natijalari keshi
│   │   ├── images/                  # Flow stiker (shaffof) va B-roll rasmlar
│   │   ├── videos/                  # Flow video clip'lar (Omni / Veo)
│   │   ├── photos/                  # Studiya yorug'ligiga keltirilgan o'quvchi/ustoz fotolari (Flow)
│   │   ├── sfx/                     # ElevenLabs Sound Effects
│   │   ├── bgm/                     # ElevenLabs ambient/fon musiqalari
│   │   └── voiceovers/              # ElevenLabs TTS Band 9.0 talaffuz namunalari
│   └── audio/                       # Bazaviy doimiy audio kutubxona
│       ├── bgm/                     # lofi_study.mp3, energetic_promo.mp3, storytelling_warm.mp3
│       └── sfx/                     # whoosh.wav, pop.wav, ding_correct.wav, buzzer_wrong.wav
├── remotion/                        # Remotion loyihasi — FAQAT video (React + TypeScript)
│   ├── src/Root.tsx                 # `Reel` kompozitsiyasi
│   ├── src/theme.ts, fonts.ts       # brand_preset.json dan ranglar va Google Fonts
│   ├── src/components/primitives.tsx# Emoji (Fluent 3D), Icon (Lucide + Iconify), Chip, Card
│   └── src/reel/                    # Zoom, Flow vizuallar, emojilar, kartalar, subtitr, audio ducking, watermark
├── reference/                       # Claude Code qaror qabul qilishi uchun mezonlar va namunalar
│   ├── style_guides/
│   │   ├── personal_brand_guide.md  # Shaxsiy brend videolari ritmi, ranglari va hissiyoti
│   │   ├── course_promo_guide.md    # Hook -> og'riq -> yechim -> CTA strukturasi
│   │   ├── ielts_insights_guide.md  # IELTS Speaking/Writing insightlarida vizual ko'rgazmalilik qoidalari
│   │   └── poster_design_guide.md   # Poster tipografiyasi, emoji/ikonka qoidalari va kompozitsiya
│   ├── example_edits/
│   │   ├── ref_insight_pacing.json  # Namunaviy kadr almashish tezligi (har 2.5-3.5 soniyada)
│   │   ├── sample_posters/          # Reference posterlar (`new --reference` bilan 100% parity)
│   │   └── sample_hooks.md          # Ingliz tili va IELTS auditoriyasi uchun 50 ta Hook
│   └── prompts/
│       ├── transcript_analyzer.md   # Transkripsiyadan edit_plan.json tuzish va uning sxemasi
│       ├── bilingual_subtitles.md   # O'zbekcha-Inglizcha subtitr qoidalari (Scribe + Remotion)
│       ├── flow_prompts.md          # Google Flow rasm/video/fon/foto-tahrir promptlari
│       └── elevenlabs_audio_prompts.md # ElevenLabs SFX va ambient BGM prompt shablonlari
├── workspace/                       # Joriy montaj va dizayn jarayonidagi fayllar
│   ├── 01_raw/                      # Xom videolar (.mp4) hamda o'quvchi rasm/sertifikatlari
│   ├── 02_transcripts/              # Scribe so'zma-so'z vaqtlari (.json) va .srt
│   ├── 03_edit_plans/               # Claude Code tuzgan edit_plan.json rejalari
│   ├── 04_exports/                  # Tayyor Reels videolari
│   ├── flow_requests/               # Flow so'rovlari (scene -> reja/poster maydoni xaritasi)
│   └── 05_posters/
│       ├── drafts/                  # Poster spec'lari (<id>.json), matn tekshiruv varaqlari, blur qilingan TRF'lar
│       ├── refs/<id>/               # Reference tahlili: grid, measure, clean plate, parity varag'i
│       ├── figma/                   # use_figma skriptlari (<id>.js) va rasm hash keshi
│       └── final/                   # Figma'dan eksport PNG posterlar (aniq 1080x1350 / 1080x1920)
└── scripts/                         # Claude Code ishga tushiradigan yordamchi skriptlar
    ├── silence_remover.py           # Pauza va duduqlanishlarni kesish (auto-cut) + -14 LUFS
    ├── transcribe_elevenlabs.py     # ElevenLabs Scribe v2: o'zbek+ingliz nutq, so'z vaqtlari, keyterms, .srt
    ├── build_captions.py            # Remotion uchun 1–3 so'zli subtitr sahifalari va kalit so'z ranglari
    ├── generate_elevenlabs_audio.py # ElevenLabs SFX, BGM, Audio Isolation va Native TTS
    ├── flow_design.py               # Flow artwork promptlari (reference parity / istak / edit), formatlar va xavfsiz zonalar
    ├── poster_reference.py          # Reference tahlili: grid, measure, clean plate, parity compare
    ├── flow_assets.py               # Google Flow so'rovi va natijalarni import qilish (variant tanlash, stiker fonini shaffof qilish)
    ├── fluent_emoji.py              # Fluent 3D emoji qidirish va yuklash
    ├── remotion_utils.py            # Video uchun fayllarni remotion/public ga joylash va render chaqirish
    ├── poster_studio.py             # Posterlar: spec (new/edit/image), Flow art, Figma upload/render/export, verify, TRF blur
    ├── figma/render_poster.js       # Spec -> Figma qatlamlari (render / faqat matn rejimi); Lucide + Simple Icons (npm)
    ├── matte_video.py               # Fonni olib tashlash (Robust Video Matting, ONNX, CPU): alfa WebM + grade + despill
    ├── studio_render.py             # Studio montaj: kesilgan spiker animatsion Impulse studiyasida (Remotion `Studio`)
    └── render_pipeline.py           # Reels: prepare -> assets -> render (Remotion)
```

## 2. Xizmatlar va Vazifalari

| Modul / Xizmat | Texnologiya | Pipeline'dagi Vazifasi | Saqlanish Joyi |
| :--- | :--- | :--- | :--- |
| **Figma — posterlar** | `use_figma` + `scripts/figma/render_poster.js` | Natija, reklama, e'lon, karusel, Reels muqovasi: logotip, Montserrat matnlar, Lucide/Simple Icons, chip/kontakt komponentlari — barchasi tahrirlanadigan qatlam; Feed + Story bitta sahifada. | `workspace/05_posters/final/` |
| **Google Flow — poster artwork** | `flow` MCP, Nano Banana Pro (0 credit) | Faqat MATNSIZ sahna/hero obyekt; prompt reference'dan (100% parity, clean plate) yoki foydalanuvchi istagidan. | `assets/ai_generated/posters_bg/` |
| **Google Flow — rasm** | `flow` MCP, Nano Banana (0 credit) | Video uchun stikerlar (oq fon → shaffof), 9:16 B-roll, foto tahriri (reference bilan). | `assets/ai_generated/images/`, `photos/` |
| **Google Flow — video** | `flow` MCP, Omni 1.1 Flash / Veo 3.1 (credit) | Qisqa 9:16 kinematografik clip'lar (`kind: clip`). Har generatsiyadan oldin foydalanuvchi ruxsati. | `assets/ai_generated/videos/` |
| **ElevenLabs Scribe** | `POST /v1/speech-to-text` (`scribe_v2`) | O'zbek+ingliz nutqni so'zma-so'z vaqtlar bilan yozish, IELTS atamalari `keyterms`, `.srt` eksport. Subtitrlar shu vaqtlardan. | `workspace/02_transcripts/` |
| **ElevenLabs Sound Effects** | `POST /v1/sound-generation` | Maxsus SFX va ambient BGM loop. | `assets/ai_generated/sfx/`, `bgm/` |
| **ElevenLabs Audio Isolation** | `POST /v1/audio-isolation` | Shovqinli yozuvni studiya darajasida tozalash. | `workspace/01_raw/*_clean.wav` |
| **ElevenLabs TTS** | `POST /v1/text-to-speech/{voice_id}` | Band 9.0 British/American talaffuz namunalari. | `assets/ai_generated/voiceovers/` |
| **Remotion — Reel** | `remotion/src/reel/Reel.tsx` | Zoom punch-in, Ken Burns, Flow clip/stiker, Fluent emoji, `compare`/`band_meter`/`callout` kartalari, rangli subtitr, BGM ducking, CTA → 1080x1920, 60 fps. | `workspace/04_exports/` |
| **Video dizayni** | Google Fonts, `lucide-react` + Iconify (`simple-icons`), Fluent Emoji 3D | Reels'dagi shrift, ikonka (Telegram/Instagram ham) va 3D emojilar. | `config/brand_preset.json`, `assets/emoji/fluent3d/` |

## 3. Poster Studio: Figma poster + Google Flow artwork

Har bir poster — bitta **spec** (`workspace/05_posters/drafts/<id>.json`): matnlar, qatlamlar, uslublar, artwork prompti va Figma node id'lari.
**Figma** spec'dan posterni tahrirlanadigan qatlamlar bilan quradi; **Google Flow** faqat matnsiz artwork chizadi — shuning uchun matnda AI xatosi bo'lmaydi.

### Dizayn manbasi
| Rejim | Qachon | Maket | Flow prompti |
| :--- | :--- | :--- | :--- |
| **reference** (`new --reference rasm`) | Foydalanuvchi namunaviy poster bergan | Referencedan **100% parity**: grid (koordinata = Figma px) + `measure` bilan har bir blok 1:1 o'lchanadi | Reference'ning **clean plate**'i (matnlari o'chirilgan) reference 1; sahna aynan takrorlanadi, faqat foydalanuvchi assetlari almashadi |
| **wishes** (`new --wishes "..."`) | Reference yo'q | `assets/poster_templates/<type>.json` yoki `--from <poster_id>` | Foydalanuvchi istagidan `art.description` + Impulse uslubi |
| **o'zgarish** (`edit --layer`, `art --change`) | Foydalanuvchi so'raganda | Reference'dan chetlashish mumkin, `parity.deviations` da qayd | Joriy artwork reference 1, faqat o'zgarish |

### Spec qatlamlari (qisqacha)
```json
{"id": "title", "type": "text", "text": "{title}\n{lead} {accent}", "style": "Bold", "size": 92,
 "ranges": {"accent": {"style": "Black Italic", "color": {"gradient": 0, "stops": [["$brand_glow", 0], ["$brand_primary", 1]]}}}}
{"id": "date", "type": "item", "style": "chip", "icon": "lucide:calendar", "text": "{date}"}
{"id": "art", "type": "image", "image": "art", "x": 0, "y": -250, "w": 1080, "h": "auto", "locked": true, "shift": false}
{"id": "content", "type": "stack", "direction": "vertical", "gap": 34, "x": 80, "bottom": 64, "w": 920, "children": ["..."]}
```
Turlar: `image`, `rect`, `ellipse`, `text` (`{kalit}` → `texts`), `icon` (`lucide:*`, `simple-icons:*`), `item` (`styles` dagi komponent: chip, contact), `stack` (auto-layout).
Ranglar `#RRGGBB` yoki `$brand_token`; `fill` — rang, `{"color","opacity"}` yoki `{"gradient": burchak, "stops"}`; `effects` — `shadow`, `bg_blur`, `blur`.
Koordinatalar base formatda (odatda Feed); boshqa formatda `y`/`bottom` xavfsiz zona farqiga avtomatik siljiydi, aniq farqlar `formats.<fmt>.overrides` da.

### Matn aniqligi va parity
`export` dan keyin `verify` avtomatik: `drafts/<id>_check.png` — har bir matn qatlami eksportdan kesilib kutilgan matn bilan yonma-yon (harfma-harf tekshiriladi), Story xavfsiz zonasi tekshiruvi, reference rejimida `refs/<id>/parity_feed.png` (reference | eksport | ustma-ust) va layout/rang balli.

## 4. Bosqichma-Bosqich Ishlash Jarayoni

### A. Video Montaj Oqimi
1. **Ingest:** `render_pipeline.py prepare <video> [--isolate]` — ElevenLabs Audio Isolation (ixtiyoriy), `0.35s` dan uzun pauzalarni kesish, `-14 LUFS`.
2. **Transkripsiya (ElevenLabs Scribe v2):** so'zma-so'z vaqtlar, IELTS `keyterms`, `.srt`.
3. **AI Rejissyorlik:** Claude Code `reference/prompts/transcript_analyzer.md` bo'yicha `edit_plan.json` tuzadi (hook, zoom, emojilar, kartalar, Flow vizuallar, audio).
4. **Assetlar:** `render_pipeline.py assets <plan>` — ElevenLabs SFX/BGM/TTS + Flow so'rovi (vizuallar va sarlavhali Reels muqovasi) → Claude `flow_generate` / `flow_wait` → `flow_assets.py import`.
5. **Render (Remotion):** `render_pipeline.py render <plan>` — subtitr sahifalari, emojilar, watermark, `Reel` kompozitsiyasi 1080x1920 60 fps.

### B. Poster Oqimi
1. **Spec:** `poster_studio.py new --id <id> --type <tur> [--reference rasm | --from poster | --wishes "..."] --texts t.json [--asset fayl::rol]`; foto/TRF: `image --name ... [--trf --blur-box ...]`.
2. **Reference bo'lsa:** `refs/<id>/reference_grid.png` + `poster_reference.py measure` → `layers`, `styles`, `parity.text_boxes`, `art.description/replace` 1:1.
3. **Artwork:** `poster_studio.py art --id <id>` → `flow_generate` → `flow_wait` → `flow_assets.py import workspace/flow_requests/<id>_art.json` (artworkda harf yo'qligini ko'z bilan tekshir).
4. **Figma:** `upload --id <id>` → `upload_assets(count=N)` → `upload --id <id> --url ...` → `figma --id <id>` → `use_figma(<id>.js mazmuni)` → `record --id <id> --result natija.json`.
5. **Eksport + tekshiruv:** `download_assets(nodeId, png, scale 1)` → `export --id <id> --url feed=... --url story=...` → `verify` (matn varag'i, xavfsiz zona, parity).
6. **Tahrir:** matn `edit --set key="..."` → `figma --texts`; maket `edit --layer id.xossa=qiymat --request "..."` → `figma` (eski versiya sahifada arxiv); artwork `art --change "..."`.

## 5. `config/brand_preset.json`

Brend (`brand`: nom va logotip yo'llari), Impulse ko'k ranglari (`colors.brand_*`), shriftlar (`typography.heading/body`), xavfsiz zona, BGM/ducking darajasi, Flow modellari va credit chegarasi, ElevenLabs `stt_model` (`scribe_v2`) — barchasi shu faylda. Remotion (video), `poster_studio.py` (Figma posterlar, `figma.file_key`) va `flow_design.py` (artwork) uni to'g'ridan-to'g'ri o'qiydi, shuning uchun brendni o'zgartirish uchun kodga tegish shart emas.

```json
"typography": { "heading": "Montserrat", "body": "Inter",
                "available": ["Montserrat", "Inter", "Poppins", "Unbounded", "Manrope", "Rubik", "Bebas Neue", "Playfair Display", "Nunito", "Oswald"] },
"ai_generation": {
  "flow": { "image_model": "Nano Banana", "poster_model": "Nano Banana Pro", "video_model": "Omni 1.1 Flash", "video_max_credits_per_scene": 12 },
  "elevenlabs": { "stt_model": "scribe_v2", "tts_model": "eleven_multilingual_v2" }
}
```

## 6. Buyruqlar

```bash
# Poster (Figma + Flow artwork)
python scripts/poster_studio.py new --id olimpiada_2027 --type announcement --reference reference/example_edits/sample_posters/olympiad_blue_trophy_ref.jpg --texts t.json --asset "assets/elements/trophy_silver_blue.png::the exact silver trophy"
python scripts/poster_studio.py new --id olimpiada_2027 --type announcement --from olimpiada_2026 --set date="1-noyabr, 2027-yil"
python scripts/poster_reference.py measure --image workspace/05_posters/refs/olimpiada_2027/reference_design.png --box title=70,805,620,235 --out workspace/05_posters/refs/olimpiada_2027/measure.png
python scripts/poster_studio.py art --id olimpiada_2027
python scripts/poster_studio.py upload --id olimpiada_2027
python scripts/poster_studio.py figma --id olimpiada_2027
python scripts/poster_studio.py record --id olimpiada_2027 --result natija.json
python scripts/poster_studio.py export --id olimpiada_2027 --url feed=<url> --url story=<url>
python scripts/poster_studio.py edit --id olimpiada_2026 --set date="2-noyabr, 2026-yil"     # -> figma --texts
python scripts/poster_studio.py edit --id olimpiada_2026 --layer title.size=96 --request "sarlavha kattaroq"
python scripts/poster_studio.py image --id sardor_80 --name trf --file workspace/01_raw/sardor_trf.jpg --trf --blur-box 0.62,0.08,0.30,0.05
python scripts/poster_studio.py verify --id olimpiada_2026
python scripts/poster_studio.py list

# Google Flow (Claude: flow_generate -> flow_wait orasida)
python scripts/flow_assets.py import workspace/flow_requests/olimpiada_2027_art.json --variant 1
python scripts/flow_assets.py request --poster sardor_80 --image student --edit-photo
python scripts/flow_assets.py request --plan workspace/03_edit_plans/speaking_idioms.json

# Video
python scripts/render_pipeline.py prepare workspace/01_raw/speaking_idioms.mp4 --isolate
python scripts/render_pipeline.py assets workspace/03_edit_plans/speaking_idioms.json
python scripts/render_pipeline.py render workspace/03_edit_plans/speaking_idioms.json

# Studio (fon olib tashlanadi, spiker animatsion studiyada)
python scripts/matte_video.py workspace/01_raw/studio_take1.mp4 --grade          # -> <nom>_matte.webm (alfa + ovoz)
python scripts/studio_render.py workspace/03_edit_plans/studio_take1.studio.json --stills 1.2,5,8.2
python scripts/studio_render.py workspace/03_edit_plans/studio_take1.studio.json

# Dizayn
python scripts/fluent_emoji.py --search moon
cd remotion && npm run dev          # Remotion Studio: Reel kompozitsiyasini jonli ko'rish
```

## 7. `CLAUDE.md`

Loyiha ildizidagi `CLAUDE.md` — Claude Code uchun doimiy qoidalar: Figma (poster) / Flow (asset) / Remotion (video) taqsimoti, reference parity va deviatsiyalar, video credit ruxsati, har bir poster matnini majburiy tekshirish, TRF maxfiyligi (Claude rasmni ko'rib blur maydonlarini aniqlaydi), holat JSON'lari va standart buyruqlar.

## 8. Claude Code Orqali Ishga Tushirish Promptlari

### A. IELTS Natijalar Posteri
> `"O'quvchimiz Sardorbek Karimov IELTS dan Overall 8.0 oldi (L 8.5, R 8.5, W 7.0, S 8.0). Rasmi workspace/01_raw/sardor.jpg, sertifikati workspace/01_raw/sardor_trf.jpg. Flow orqali rasmini studiya yorug'ligiga keltir, TRF raqamlarini blur qil va 'Before 6.0 -> After 8.0 (8 haftada)' bilan Feed + Story natija posterini Figma'da yasa, barcha ballarni tekshir."`

### B. Kurs Reklamasi
> `"'IELTS Writing & Speaking Marathon' uchun reklama posteri: 5-noyabr, 3 hafta, 490,000 so'm (chegirma bilan 350,000), 15 joy. to'q navy va Impulse ko'kidagi akademik uslubda (artwork Flow'da, poster Figma'da), ustoz rasmi bilan Feed + Story poster yarat."`

### C. Mavjud Posterni Edit Qilish
> `"writing_marathon posterini edit qil: 'Faqat 3 ta joy qoldi!' va sanani 8-noyabrga sur. Shuningdek fonga yorqinroq ko'k nurlar va 3D qalam/kitob qo'sh."`

### D. IELTS Insight Video
> `"workspace/01_raw/speaking_part2_idioms.mp4 ni IELTS Insights uslubida montaj qil. Har bir Band 8.0 idioma uchun Fluent emoji yoki Flow stiker, Band 5.5 vs 8.0 compare kartasi, ElevenLabs British TTS namunasi, pop/whoosh SFX va lo-fi BGM bilan workspace/04_exports/ ga render qil."`

## 9. Tizim Talablari

* **Claude Code** + ulangan **Google Flow MCP** (`flow`) — Flow Chrome oynasida tizimga kirilgan, loyiha ochilgan va "Add AI credits" kabi bannerlar yopilgan bo'lishi kerak.
* **Node.js 20+** (Remotion): `cd remotion && npm install`
* **FFmpeg 7+** (`ffmpeg`, `ffprobe` PATH'da) — auto-cut va audio ajratish uchun.
* **Python 3.10+:**
  ```bash
  pip install -r requirements.txt
  ```
* **API kalit:** `.env` faylida `ELEVENLABS_API_KEY`. OpenAI kerak emas.
