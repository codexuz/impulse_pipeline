# Transkripsiya Tahlili -> `edit_plan.json`

Claude Code `workspace/02_transcripts/<nom>.json` (ElevenLabs Scribe) ni o'qib, `workspace/03_edit_plans/<nom>.json` rejasini tuzadi.
Undan keyin:
```bash
python scripts/render_pipeline.py assets workspace/03_edit_plans/<nom>.json   # ElevenLabs audio + Flow so'rovi
# Claude: mcp__flow__flow_generate -> flow_wait -> python scripts/flow_assets.py import workspace/flow_requests/<nom>.json
python scripts/render_pipeline.py render workspace/03_edit_plans/<nom>.json   # Remotion -> workspace/04_exports/
```

## Tahlil vazifasi
1. Video turini aniqlang (insight / promo / personal brand) va mos `reference/style_guides/*.md` ni o'qing.
2. **Hook**: birinchi 2.5 s ichidagi eng kuchli gapni topib, qisqa sarlavha qiling (≤ 5 so'z) va mos Fluent emoji tanlang.
3. **Kalit so'zlar**: barcha inglizcha idioma/collocation/atamalarni `english`, Band 8.0 variantlarni `correct`, Band 5.5 variantlarni `mistake` ga yozing. Transkripsiyadagi yozilishi bilan aynan bir xil bo'lsin.
4. **Vizual nuqtalar** (arzonidan qimmatiga):
   - `emojis` — Fluent 3D emoji (bepul, darhol): his-tuyg'u, oddiy obyektlar (🌕 full moon, 🔥 fire, 🧠 brain).
   - `cards` — Remotion kartalari: `compare` (Band 5.5 vs 8.0), `band_meter` (6.0 -> 8.0), `callout` (Lucide ikonka + qisqa matn).
   - `visuals` `sticker` / `broll` — Google Flow rasm (Nano Banana, 0 credit).
   - `visuals` `clip` — Google Flow video (credit sarflaydi; faqat foydalanuvchi ruxsati bilan).
   `ref_insight_pacing.json` ritmiga rioya qiling — 3.5 s dan uzun "bo'sh" kadr qoldirmang.
5. **Zoomlar**: hook va har bir yangi argument boshida punch-in.
6. **Audio**: stiker/emoji chiqishida `pop`, kadr o'tishida `whoosh`, to'g'ri/xato qiyosda `ding_correct`/`buzzer_wrong`. Inglizcha namunalar uchun TTS — ustoz pauzasidan keyin (`at` = gap tugagan vaqt + 0.1 s).
7. Flow promptlari `flow_prompts.md`, audio promptlari `elevenlabs_audio_prompts.md` bo'yicha yoziladi.

## `edit_plan.json` sxemasi

```json
{
  "id": "speaking_part2_idioms",
  "type": "insight",
  "source": "workspace/01_raw/speaking_part2_idioms_cut.mp4",
  "transcript": "workspace/02_transcripts/speaking_part2_idioms_cut.json",
  "output": "workspace/04_exports/speaking_part2_idioms.mp4",

  "hook": { "text": "Band 8.0 idioms", "emoji": "fire", "start": 0.0, "end": 2.5 },
  "keywords": {
    "english": ["over the moon", "a piece of cake"],
    "correct": ["I was over the moon"],
    "mistake": ["very happy"]
  },
  "zooms": [
    { "start": 0.0, "end": 2.5, "scale": 1.12 },
    { "start": 9.4, "end": 11.0, "scale": 1.08 }
  ],
  "emojis": [
    { "name": "full moon", "start": 4.2, "end": 6.8, "position": "right", "size": 260 }
  ],
  "cards": [
    { "type": "compare", "weak": "very happy", "strong": "over the moon", "weak_label": "BAND 5.5", "strong_label": "BAND 8.0", "start": 9.4, "end": 12.0 },
    { "type": "band_meter", "from": 6.0, "to": 8.0, "label": "Speaking", "start": 20.0, "end": 22.5 },
    { "type": "callout", "icon": "BookOpen", "text": "Part 2 uchun ideal", "tone": "brand", "start": 13.0, "end": 15.0 }
  ],
  "visuals": [
    {
      "id": "over_the_moon",
      "kind": "sticker",
      "prompt": "a joyful cartoon student jumping over a glowing crescent moon",
      "start": 4.2, "end": 7.0,
      "position": "top",
      "file": null
    },
    {
      "id": "exam_hall",
      "kind": "broll",
      "prompt": "quiet modern exam hall with soft morning light, slow dolly",
      "start": 14.0, "end": 16.8,
      "file": null
    },
    {
      "id": "london_rain",
      "kind": "clip",
      "prompt": "rainy London street at dusk, red double-decker bus passes, slow push-in",
      "start": 24.0, "end": 28.0,
      "file": null
    }
  ],
  "cta": { "text": "Izohda 'IELTS' deb yozing", "icon": "MessageCircle", "emoji": "backhand index pointing down", "start": 31.0 },
  "audio": {
    "voice_volume": 1.0,
    "bgm": { "id": "lofi_study", "file": "assets/audio/bgm/lofi_study.mp3", "ducking": true },
    "sfx": [
      { "id": "pop", "file": "assets/audio/sfx/pop.wav", "at": 4.2 },
      { "id": "ding", "file": "assets/audio/sfx/ding_correct.wav", "at": 10.1 },
      { "id": "magic_shimmer", "prompt": "short sparkling magical shimmer", "duration": 1.0, "at": 4.25, "file": null }
    ],
    "voiceovers": [
      { "id": "over_the_moon_uk", "text": "I was over the moon when I got my results.", "accent": "british", "at": 7.1, "file": null }
    ]
  },
  "thumbnail": {
    "title": "Band 8.0", "accent": "idioms", "tag": "IELTS Speaking", "emoji": "star-struck",
    "prompt": "excited student holding a score sheet, golden light", "file": null
  }
}
```

### Maydonlar
- `file: null` + `prompt` — `assets` bosqichida yaratiladi (Flow yoki ElevenLabs) va yo'l rejaga yoziladi (kesh).
- `file` mavjud bo'lsa — tayyor kutubxona fayli ishlatiladi (`assets/audio/`, `assets/b_roll/`).
- `emoji` / `emojis[].name` — Fluent emoji nomi yoki belgisi (`python scripts/fluent_emoji.py --search moon`).
- `icon` — Lucide nomi PascalCase'da (`BookOpen`, `Trophy`, `MessageCircle`) — https://lucide.dev/icons
- `visuals[].kind`: `sticker` (1:1, oq fon avtomatik shaffof qilinadi), `broll` (9:16 rasm, Ken Burns), `clip` (9:16 Flow video, ovozsiz).
- `cards[].tone` (callout): `brand` (ko'k, standart), `gold` (faqat mukofot/natija), `glass`, `red`, `green`.
- `watermark: false` — Impulse logotipini videodan olib tashlaydi (standart: yuqorida kichik oq logotip).
- `audio.bgm.volume_db` ixtiyoriy; standart va ducking darajasi `brand_preset.json -> video_settings` da.
- `thumbnail.title` bo'lsa — `assets` bosqichida Reels muqovasi to'liq Google Flow'da (sarlavha, tag, aksent matni va logotip bilan) yaratiladi va import'da `<output>_cover.png` (1080x1920) bo'ladi. Matnini ko'z bilan tekshiring.
- Barcha vaqtlar **kesilgan** (`_cut.mp4`) video bo'yicha, soniyada.
