# Kurs Reklamasi — Uslub Qo'llanmasi

Struktura har doim: **Hook -> Og'riq -> Yechim -> Isbot -> Taklif -> CTA**.

## Video ritm
- Kadr almashishi: har **2.0–3.0 s** (eng dinamik format).
- Auto-zoom: har yangi argumentda punch-in `1.0x -> 1.12x`.
- Uzunlik: 20–40 s. Narx va sana videoning oxirgi 30% ida.

| Bosqich | Vaqt | Ko'rinish |
| :--- | :--- | :--- |
| Hook | 0–2 s | Katta sarlavha (`Hook` stili) + ustoz yuzi |
| Og'riq | 2–8 s | "Writing 6.0 dan oshmayaptimi?" — `mistake` rangida |
| Yechim | 8–18 s | Kurs dasturi, 3 ustunlik, `classroom_vibes/` B-roll |
| Isbot | 18–25 s | O'quvchi sertifikatlari (`ielts_certificates/`, **TRF raqamlari blur!**) + `band_meter` kartasi (6.0 → 8.0) |
| Taklif | 25–32 s | Sana, narx, chegirma, qolgan joylar |
| CTA | 32–40 s | `cta` (Lucide `MessageCircle` + 👇 Fluent emoji) — "Izohda 'KURS' deb yozing" |

## Audio
- BGM: `assets/audio/bgm/energetic_promo.mp3` yoki ElevenLabs "upbeat motivational corporate pop, punchy drums".
- SFX: har punch-in da `whoosh`, narx chiqqanda `ding_correct`.

## Poster (`poster_studio.py new --type promo`, Figma qatlamlari + Flow artwork)
- Sarlavha 2 qatordan oshmasin; ikkinchi qatori (`course_title_accent`) Impulse ko'k gradientida.
- 3 ta ustunlik — har biri 6 so'zdan kam, natijaga yo'naltirilgan ("Har hafta 2 ta Writing tekshiruvi").
- Eski narx chizilgan, yangi narx katta va yorug' ko'k.
- `seats_text` qizil belgi — kamlik (scarcity) faqat haqiqiy bo'lsa yoziladi.
- Rasmda (AI fonda) hech qanday matn bo'lmaydi.
