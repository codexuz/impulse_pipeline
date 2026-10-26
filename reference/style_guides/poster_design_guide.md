# Poster Dizayn Qo'llanmasi — Reklama, E'lon, Natija, Karusel, Reels muqovasi

Posterlar **Figma'da** quriladi, **Google Flow** faqat matnsiz artwork beradi. Har bir poster — bitta spec
(`workspace/05_posters/drafts/<id>.json`), Figma skripti undan avtomatik yasaladi (`scripts/poster_studio.py figma`).

## Vazifalar taqsimoti
- **Flow** — sahna, hero obyekt (kubok, kitob), nur, tekstura, foto tahriri. Matn, raqam, logotip, ikonka — hech qachon.
- **Figma** — logotip (`assets/brand/logo_full_white.png`), barcha matnlar (Montserrat, jonli qatlam), ikonka komponentlari
  (`Icon/*`: Lucide, Simple Icons), komponentlar (`Info chip`, `Contact item` — Label va Icon xossalari bilan),
  Feed + Story frame'lari bitta sahifada (sahifa nomi = poster_id). Yangi render eski versiyani o'chirmaydi — sahifada arxivlanadi.
- Fayl: `brand_preset.json -> figma.file_key` (namuna: Olimpiada 2026 — https://www.figma.com/design/9wddCiUx8nGrplQnK24Jg6, sahifa `olimpiada_2026`).

## Reference → 100% parity
Foydalanuvchi namunaviy poster bersa, u **aynan** takrorlanadi; faqat kontent bizniki bo'ladi.
1. `new --reference <rasm>` → `refs/<id>/reference_grid.png`: reference Figma o'lchamiga (1080 px kenglik) keltirilgan,
   to'r har 54 px, yozuvlar har 108 px — o'qilgan koordinata = Figma px.
2. `poster_reference.py measure --box nom=x,y,w,h` → 3x kattalashtirilgan bo'laklar (10 px to'r) + matn/fon rangi.
3. Har bir blok uchun yoz: joy (`x`, `y` yoki `bottom`), kenglik, shrift og'irligi (Regular/Medium/SemiBold/Bold/Black, kursiv),
   o'lcham (bosh harf balandligi ≈ 0.7 × font size), qator oralig'i (`lineHeight` %), harf oralig'i (`letterSpacing` %),
   rang, tekislash, bloklar orasidagi masofa (`gap`). Shrift oilasi — referencedagiga eng yaqin Google Font
   (`brand_preset.json -> typography.available`); aniq bo'lmasa Montserrat.
4. Referencedan almashadigan kontent: matnlar → foydalanuvchiniki, ularning logotipi → Impulse logotipi, telefon/handle →
   Impulse aloqalari, hero obyekt → foydalanuvchi asseti (`--asset fayl::rol`). Qolgan hamma narsa — reference'dagidek.
5. `parity.text_boxes` — referencedagi barcha matn/logo/ikonka qutilari: shulardan clean plate yasaladi (Flow matn ko'rmaydi).
6. Reference matni bizning matndan uzunroq/qisqaroq bo'lsa: shrift o'lchamini emas, birinchi navbatda qator bo'linishini
   moslashtir; blok chegarasi (`w`) referencedagidek qoladi.
7. `verify` → `refs/<id>/parity_<fmt>.png` (reference | eksport | ustma-ust): bloklar ustma-ust tushishi kerak.

## O'zgarishlar (deviatsiyalar)
- Foydalanuvchi so'ragan o'zgarish reference'dan chetlashishi mumkin: `edit --layer ... --request "<foydalanuvchi so'zi>"` yoki
  `art --change "..."`. Har biri `parity.deviations` da qayd etiladi va `verify` da ko'rsatiladi.
- So'ralmagan "yaxshilash" kiritma: reference rejimida baseline — reference.

## Oltin qoida: matn aniqligi
- Har bir matn `texts` da **aynan foydalanuvchi bergan holda** (ism, ball, sana, vaqt, narx, telefon, @username, o'zbek apostroflari).
- Uydirma shior yoki va'da qo'shma. Matn qatlamda `{kalit}` bilan ishlatiladi; kursiv/rangli aksent — `ranges`.
- `export` dan keyin `drafts/<id>_check.png` — har bir qatlam eksportdan kesilib kutilgan matn yonida: harfma-harf tekshir.

## Brend
| Token | Hex | Ishlatilishi |
| :--- | :--- | :--- |
| `brand_light` → `brand_dark` | #0099FF → #0F56F9 | Impulse app ikonkasi gradienti: tugmalar, chiplar, nur lentalari |
| `brand_primary` | #0779FC | Asosiy brend ko'ki |
| `brand_glow` | #4DB8FF | To'q fonda aksent matn, ikonkalar, chip chegarasi |
| `background_card` | #0A1631 | Asosiy to'q navy fon |
| `award_gold` | #F59E0B | **Faqat** mukofot: Overall medal, kubok |
| `correct_band8` / `mistake_band5` | #00E676 / #FF5252 | Band 8.0 vs 5.5 qiyoslari |

Spec'da ranglar `$token` bilan yoziladi (`"$brand_glow"`). Reference rejimida reference ranglari ustun, lekin logotip va aloqa — Impulse.

## Format va xavfsiz zonalar
- **Feed** 1080x1350, chetdan ≥ 64 px. **Story** 1080x1920: yuqori 230 px va pastki 269 px Instagram UI uchun bo'sh
  (Figma'da yashirin "Safe zones (guide)" qatlami). `verify` bu zonalarni avtomatik tekshiradi.
- Story base layout'dan avtomatik: yuqoriga bog'langan qatlamlar +188 px, pastga bog'langanlar +206 px; farqlar `formats.story.overrides`.
- Ko'z harakati: Sarlavha → Asosiy raqam (Overall / narx / sana) → Tafsilotlar → Aloqa.

## Turlar
- **Natija (`result`):** o'quvchi portreti (`image --name student`, kerak bo'lsa Flow studiya portreti), oltin Overall medal
  (yagona oltin element), L/R/W/S kartalari, "before → after". TRF faqat `image --trf --blur-box` bilan; Flow'ga yuborilmaydi.
- **Kurs reklamasi (`promo`):** sarlavha, 3 ustunlik, sana/davomiylik, narx (eski narx chizilgan), "joy qoldi", CTA.
- **E'lon / Olimpiada (`announcement`):** shablon `assets/poster_templates/announcement.json` — hero obyekt yuqorida, pastda yirik
  sarlavha + kursiv aksent, sana/vaqt chiplari, chiziq, aloqa qatori.
- **Karusel (`carousel`):** har slayd alohida spec (`--from` bilan bir uslub), slayd raqami yuqori o'ngda.
- **Reels muqovasi (`cover`):** shablon `cover.json` — faqat Story, katta sarlavha yuqori uchdan birda.

## Eksportdan oldin tekshiruv
- [ ] Artworkda (Flow) birorta harf/raqam/logotip yo'q
- [ ] `_check.png` dagi har bir matn aynan, ortiqcha so'z yo'q
- [ ] Logotip buzilmagan va to'g'ri joyda
- [ ] Xavfsiz zona ogohlantirishi yo'q
- [ ] Reference rejimida: parity varag'ida bloklar mos, farqlar faqat `deviations` dagilar
- [ ] TRF maxfiy maydonlari ko'rinmaydi
- [ ] Feed va Story ikkalasi `workspace/05_posters/final/` da, aniq o'lchamda
