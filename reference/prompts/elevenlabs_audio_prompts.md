# ElevenLabs Audio Prompt Shablonlari

Avval `assets/audio/` dagi doimiy kutubxonani ishlating; faqat mos fayl bo'lmasa generatsiya qiling
(`generate_elevenlabs_audio.py` natijani `assets/ai_generated/` ga keshlaydi).

## SFX — `POST /v1/sound-generation` (0.5–3 s)
| Holat | Prompt | Davomiylik |
| :--- | :--- | :--- |
| Stiker chiqishi | soft bubbly pop, clean UI accent | 0.6 |
| Kadr o'tishi | fast airy whoosh transition | 0.8 |
| To'g'ri javob | bright two-note success chime | 1.0 |
| Xato | short cartoon buzzer, playful not harsh | 0.8 |
| Idioma sehri | short sparkling magical shimmer | 1.0 |
| Ball oshishi | rising synth riser ending with a soft impact | 2.0 |
| Yozish | pen scribbling quickly on paper | 1.5 |

Formula: `[ovoz manbai], [xarakter], [davomiylik his-tuyg'usi]` — musiqa atamalarisiz, aniq va qisqa.

## BGM / Ambient loop (10–22 s, `bgm` buyrug'i)
- **Insight:** warm lo-fi study beat, mellow electric piano, vinyl crackle, soft drums, no vocals, seamless loop
- **Promo:** upbeat motivational pop, punchy drums, bright synth plucks, no vocals, energetic
- **Storytelling:** warm intimate acoustic piano, slow tempo, gentle strings, no vocals
- **Mock exam / jiddiy:** minimal ticking clock ambience with low soft synth pad

## TTS — Band 9.0 talaffuz namunalari (`tts` buyrug'i)
- Model: `eleven_multilingual_v2` (`brand_preset.json`)
- `--accent british` (standart) yoki `american`, yoki to'g'ridan-to'g'ri `voice_id`.
- Matn: to'liq, tabiiy gap — faqat ibora emas. ✅ "I was over the moon when I got my results." ❌ "over the moon"
- Tinish belgilari intonatsiyani boshqaradi: vergul = qisqa pauza, nuqta = to'liq pauza.

## Audio Isolation
- Ko'cha, kafe, shovqinli xona yozuvlari uchun: `python scripts/silence_remover.py <video> --isolate`
