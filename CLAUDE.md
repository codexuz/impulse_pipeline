# CLAUDE.md - Instagram Video & Poster Pipeline Instructions

Sen ingliz tili ustozi va IELTS instruktori uchun Instagram Reels videolarini montaj qiluvchi hamda Reklama, E'lon va IELTS Natijalar posterlarini yaratib/tahrirlovchi AI Media Muhandisisan.

## Texnologiyalar (vazifalar taqsimoti)
- **Figma** (`use_figma`) — **barcha posterlar va Reels muqovalari**: logotip, har bir matn, ikonkalar, chip/kontakt komponentlari jonli (tahrirlanadigan) qatlamlar; Feed + Story bitta faylda, har poster o'z sahifasida (`brand_preset.json -> figma.file_key`).
- **Google Flow** (`flow` MCP) — **assetlar**: poster/muqova uchun MATNSIZ artwork, stikerlar, B-roll, foto tahriri (Nano Banana / Nano Banana Pro, 0 credit) va video clip'lar (Omni / Veo, credit sarflaydi).
- **Remotion** (`remotion/`) — **faqat video** yaratish va montaj (`Reel` kompozitsiyasi). Poster yoki muqova uchun Remotion ishlatilmaydi.
- **ElevenLabs** — Scribe (`scribe_v2`) transkripsiya va subtitr vaqtlari, SFX, BGM, TTS, Audio Isolation.
- **Brend:** Impulse Learning Center. Logotiplar `assets/brand/` (oq wordmark — posterlarda Figma qatlami, oq belgi, ko'k app ikonkasi). Asosiy rang — app ikonkasining ko'ki (`#0779FC`, gradient `#0099FF → #0F56F9`); oltin faqat mukofot uchun. Rasmiy aloqa: +998 95 525 99-66, Telegram @impulse_lc, Instagram @impulsestudy_lc (`brand_preset.json`).
- **Video dizayni:** Google Fonts (`@remotion/google-fonts`), Lucide / Iconify ikonkalar, Microsoft Fluent 3D emojilar (`scripts/fluent_emoji.py`).

## Asosiy Qoidalar
1. Har qanday montaj yoki poster dizaynini boshlashdan oldin `.env`, `config/brand_preset.json` va `reference/style_guides/` ichidagi mos yo'riqnomani o'qi.
2. Videolar har doim 9:16 (1080x1920, 60 fps). Posterlar bir vaqtning o'zida Feed (`1080x1350`, 4:5) va Story (`1080x1920`, 9:16) Figma frame'laridan PNG sifatida `workspace/05_posters/final/` ga eksport qilinadi.
3. Google Flow bilan ishlash:
   - Avval `mcp__flow__flow_status` — u hint qaytarsa (masalan, loyiha ochilmagan), foydalanuvchiga ayt va to'xta.
   - So'rovni skript yaratadi (`poster_studio.py art`, `render_pipeline.py assets`, `flow_assets.py request`); chiqqan argumentlar bilan **bitta** `mcp__flow__flow_generate` chaqir, `mcp__flow__flow_wait` ni `finished: true` bo'lguncha takrorla (job_ids bilan), keyin `scripts/flow_assets.py import <so'rov.json> [--variant N]`.
   - Rasmlar bepul. **Video generatsiyadan oldin** `estimated_credits` ni foydalanuvchiga ayt va aniq ruxsat ol.
   - Flow avtomatlashtiruvi xato bersa (masalan, "Add AI credits" banneri), foydalanuvchidan Flow oynasidagi bannerni yopishni so'ra.
4. SFX/BGM va Band 9.0 talaffuz namunalarini `scripts/generate_elevenlabs_audio.py` orqali yarat; transkripsiya faqat `scripts/transcribe_elevenlabs.py` (Scribe) orqali.
5. **Posterlar — Figma + Flow, bitta spec** (`scripts/poster_studio.py`, yo'riqnoma: `reference/style_guides/poster_design_guide.md`):
   - Spec `workspace/05_posters/drafts/<poster_id>.json` — matnlar (`texts`), qatlamlar (`layers`), uslublar (`styles`), artwork prompti (`art`), Figma node id'lari. Figma skripti undan avtomatik yasaladi (`scripts/figma/render_poster.js`): `figma --id` → fayl mazmuni `use_figma` ga (skillNames `figma-use,figma-generate-design`) → natija JSON → `record` → `download_assets` (png, scale 1) → `export` → `verify`.
   - **Dizayn manbasi — reference yoki foydalanuvchi istagi:**
     - **Reference berilsa (`new --reference`) — 100% parity:** `reference_grid.png` (koordinatalar = Figma px) va `poster_reference.py measure` bilan har bir blokning joyi, o'lchami, shrift og'irligi, rangi, qator/harf oralig'ini o'lchab qatlamlarni 1:1 yoz. Referencedan faqat kontent almashadi: matnlar, logotip, aloqa, foydalanuvchi assetlari (kubok, foto). `parity.text_boxes` ga referencedagi barcha matn/logo qutilarini yoz — Flow'ga matnsiz "clean plate" boradi. Flow prompti (`flow_design.py`) referencedagi sahnani aynan takrorlaydi (`art.description`, `art.replace`).
     - **Reference bo'lmasa:** maket `assets/poster_templates/<type>.json` yoki `--from <boshqa_poster>` dan; `art.description` ni foydalanuvchi istagidan yoz.
     - **Foydalanuvchi o'zgarish so'rasa** — reference'dan chetlashishga ruxsat: `edit --layer ... --request "<foydalanuvchi so'zi>"` yoki `art --change`; har biri `parity.deviations` da qayd etiladi. O'zing (so'ralmagan) o'zgarish kiritma.
   - Flow hech qachon matn, raqam, logotip yoki ikonka chizmaydi; Figma'da barcha matn jonli qatlam. Import'dan keyin artworkni och — harf qolmaganini tekshir.
   - **Matn tekshiruvi majburiy:** `verify` yaratgan `drafts/<id>_check.png` dagi har bir qatlamni kutilgan matn bilan harfma-harf solishtir (ism, ball, sana, telefon, @username, o'zbekcha apostroflar); xavfsiz zona ogohlantirishlarini tuzat; reference rejimida `refs/<id>/parity_<fmt>.png` ni ko'rib, maket referencega mosligini tekshir.
   - "Shu posterdagi sanani/ballni o'zgartir" → `edit --id ... --set date="..."` → `figma --id ... --texts` (faqat matnlar, ~2 soniya) → `record` → eksport. Maket/uslub o'zgarsa → `figma --id ...` (to'liq qayta chizish, eski versiya sahifada arxivlanadi).
   - Figma read-tool chaqiruvlari Starter rejada cheklangan bo'lishi mumkin — tejab ishlat; yozish (`use_figma`) cheklanmagan.
6. IELTS TRF sertifikati: rasmni **o'zing ko'rib**, `Candidate Number`, `TRF Number`, pasport/ID, tug'ilgan sana va shtrix-kod joylarini 0..1 ulushlarda ber: `poster_studio.py image --id ... --name trf --file ... --trf --blur-box x,y,w,h`. Figma'ga faqat blur qilingan nusxa yuklanadi, TRF hech qachon Flow'ga yuborilmaydi. `drafts/<nom>_blurred.png` va yakuniy posterni ko'z bilan tekshir.
7. Natijani topshirishdan oldin har doim ko'z bilan tekshir (posterlarni och, videodan bir nechta kadr ol).

## Standart Buyruqlar (Prompts)
- "Yangi insight videoni AI bilan montaj qil: [fayl_nomi]" -> `render_pipeline.py prepare` -> `edit_plan.json` tuz (`reference/prompts/transcript_analyzer.md`) -> `render_pipeline.py assets` (Flow vizuallar + ElevenLabs audio) -> Flow -> `flow_assets.py import` -> `render_pipeline.py render` (Remotion). Muqova: `poster_studio.py new --type cover` (Figma).
- "Fonni olib tashla / studio qil: [video]" -> `transcribe_elevenlabs.py` (matnni foydalanuvchi bilan tekshir) -> `matte_video.py <video> --grade` (RVM fon olib tashlash + soya/rang tuzatish + rangli devor aksini tozalash) -> `workspace/03_edit_plans/<id>.studio.json` (subtitr, zoom, emoji, badge, callout, headline, end card, SFX/BGM) -> `studio_render.py <plan> --stills 1,5,8` (kadrlarni ko'z bilan tekshir) -> `studio_render.py <plan>` (Remotion `Studio`).
- "IELTS natija posteri yasa: [o'quvchi_ismi va ballari]" -> `poster_studio.py new --type result [--reference ...]` -> `image` (foto, blur TRF) -> `art` -> Flow -> `upload` -> `figma` -> `record` -> `export` -> verify.
- "Reklama / E'lon posteri yasa: [kurs yoki tadbir ma'lumotlari]" -> `poster_studio.py new --type promo|announcement [--reference rasm | --from poster_id] --wishes "..."` -> `art` -> Flow -> `upload` -> `figma` -> `record` -> `export` -> verify.
- "Shu referencedagidek poster yasa" -> `new --reference <rasm>` -> grid + `measure` bilan 1:1 qatlamlar -> qolgani yuqoridagidek; `verify` parity varag'ini ko'r.
- "Posterni edit qil: [poster_id] [o'zgarishlar]" -> matn: `edit --set key="..."` -> `figma --texts`; maket/uslub: `edit --layer ... --request "..."` -> `figma`; artwork: `art --change "..."` -> Flow -> `upload` -> `figma`.
