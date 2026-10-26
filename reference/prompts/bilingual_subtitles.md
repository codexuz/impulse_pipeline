# O'zbekcha-Inglizcha Subtitr Qoidalari

Ustoz o'zbekcha gapiradi, lekin IELTS atamalari va misollar inglizcha. Subtitr nutqni **o'zgartirmasdan** aks ettiradi.

## Oqim
1. `scripts/transcribe_elevenlabs.py` — ElevenLabs Scribe (`scribe_v2`) so'zma-so'z vaqtlar bilan yozadi.
   `edit_plan.json` → `keywords` va standart IELTS atamalari `keyterms` sifatida yuboriladi (to'g'ri yozilishi uchun).
2. Claude transkripsiyani tekshiradi va xatolarni `workspace/02_transcripts/<nom>.json` → `words[].word` da tuzatadi
   (vaqtlarga tegmasdan).
3. Render vaqtida `scripts/build_captions.py` 1–3 so'zli sahifalar yasaydi; Remotion (`remotion/src/reel/Captions.tsx`)
   ularni chizadi: aytilayotgan so'z kattalashadi, kalit so'zlar rangda.

## Qoidalar
1. **Inglizcha atamalar tarjima qilinmaydi**: "Lexical Resource", "Task Response", "over the moon" — asl holida.
2. Scribe xato yozgan inglizcha so'zlarni tuzating (masalan "ova da mun" -> "over the moon"), o'zbekcha gap tartibini o'zgartirmang.
3. O'zbek lotin imlosi: `o'`, `g'` uchun to'g'ri apostrof, `sh`, `ch`, `ng`.
4. Band ballari raqam bilan: "Band 8.0", "7.5" — so'z bilan emas.
5. Har ekranda **≤ 3 so'z / ≤ 22 belgi** (`build_captions.py` avtomatik bo'ladi).
6. Katta harf (UPPERCASE) — Reels uslubi; kalit so'zlar rang bilan ajratiladi, qo'shtirnoq ishlatilmaydi.
7. Parazit so'zlar ("eee", "mmm", "xullas" takrori) transkripsiyadan o'chiriladi — vaqtlar qolgan so'zlarda saqlanadi.

## Rang xaritasi (`brand_preset.json -> colors`)
| Kalit | Rang | Misol |
| :--- | :--- | :--- |
| `english` | Sariq #FFD700 | IDIOM, COLLOCATION, OVER THE MOON |
| `correct` | Yashil #00E676 | I WAS THRILLED |
| `mistake` | Qizil #FF5252 | VERY HAPPY |

## Tekshiruv
- `edit_plan.json` → `keywords` dagi iboralar transkripsiyadagi so'zlar bilan aynan mos bo'lishi kerak.
- Scribe eksport qilgan `.srt` (`workspace/02_transcripts/<nom>.srt`) Instagram'ga alohida subtitr sifatida ham yuklanishi mumkin.
