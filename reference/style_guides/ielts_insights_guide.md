# IELTS Insights Videolari — Vizual Ko'rgazmalilik Qoidalari

Maqsad: tomoshabin **ovozsiz** ko'rsa ham darsni tushunsin.

## Ritm
- Kadr almashishi: har **2.5–3.5 s** (`reference/example_edits/ref_insight_pacing.json`).
- Har bir yangi idiom/collocation = yangi vizual hodisa (Fluent emoji, Flow stiker, zoom yoki Remotion karta).
- Uzunlik: 30–75 s.

## "Don't say X, say Y" formati
1. Band 5.5 variant — `mistake` rangi (#FF5252) + `buzzer_wrong` SFX.
2. Band 8.0 variant — `correct` rangi (#00E676) + `ding_correct` SFX.
3. Ikkalasi ekranda `compare` kartasi bilan (Lucide ❌/✅ ikonkalar, qizil/yashil qatorlar).
4. Darhol ElevenLabs British TTS talaffuz namunasi (`voiceovers`), ustoz ovozi pauzasida.

## Stikerlar va emojilar
- Oddiy his-tuyg'u/obyekt uchun avval **Fluent 3D emoji** (`emojis`, bepul): 🌕 full moon, 🔥 fire, 🧠 brain.
- Murakkab metafora uchun **Google Flow** stikeri (`visuals` `kind: sticker`, Nano Banana, 0 credit).

### Flow stikerlari
- Har bir idioma uchun **so'zma-so'z vizual metafora** ("over the moon" -> oy ustida sakrayotgan odam).
- Joylashuv: yuqori xavfsiz zona (`position: "top"`), kengligi ~620px, ustoz yuzini yopmasin.
- Ekranda 2.5–4 s turadi, fade in/out 0.2 s, `pop` SFX bilan chiqadi.

## Subtitr ranglari
| Tur | Rang | Qachon |
| :--- | :--- | :--- |
| `english` | #FFD700 | Har qanday inglizcha atama/idioma |
| `correct` | #00E676 | Band 8.0+ variant |
| `mistake` | #FF5252 | Band 5.5 / xato variant |

## Auto-zoom
- Hook (0–2.5 s) da `1.12x`, keyin har yangi idiomada qisqa punch-in (`1.08–1.12x`, 1–2 s).

## Yakun
- Oxirgi 3 s: `cta` (Lucide ikonka + 👇 Fluent emoji) — "Izohda 'IELTS' deb yozing" yoki "Saqlab qo'ying".
