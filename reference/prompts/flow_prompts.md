# Google Flow Prompt Shablonlari

`scripts/flow_assets.py` har bir promptga avtomatik qo'shadi:
- Uslub: `config/brand_preset.json` → `ai_generation.flow.default_visual_style` (stikerlar uchun `sticker_style`)
- Himoya: "Absolutely no text, letters, numbers, logos or watermarks anywhere in the image."

Video assetlari (stiker, B-roll, clip) uchun promptda faqat **mavzu, harakat va kompozitsiya** yoziladi — matnsiz.
Posterlar va muqovalar uchun ham Flow faqat MATNSIZ artwork chizadi — matn, logotip va ikonkalar Figma qatlamlari (4- va 7-bo'limlar).
Promptlar inglizcha. Tartib: obyekt va harakat → kadr va kamera → joy → uslub → yorug'lik.

## Narx
| Tur | Model | Credit |
| :--- | :--- | :--- |
| Rasm (sticker, broll, fon, foto tahriri) | Nano Banana | 0 |
| Video clip 4–10 s | Omni 1.1 Flash (standart) | ~7–15 |
| Video 8 s | Veo 3.1 Fast / Quality | 20 / 100 |

Video so'rovidan oldin `estimated_credits` ni foydalanuvchiga ayting va ruxsat oling.

## 0. Avval bepul variantlar
- His-tuyg'u va oddiy obyekt → **Fluent 3D emoji** (`emojis`): 🌕 full moon, 🎂 birthday cake, 🧊 ice, 📚 books.
- Qiyos, ball, ro'yxat → **Remotion kartalari** (`cards`) va **Lucide** ikonkalari.

## 1. Idioma stikerlari (`kind: sticker`, 1:1, oq fon → shaffof)
Formula: `[so'zma-so'z metafora sahnasi], single object`

| Idioma | Prompt |
| :--- | :--- |
| over the moon | a joyful cartoon student jumping over a glowing crescent moon |
| a piece of cake | a single slice of strawberry cake on a small plate with a tiny graduation cap on top |
| break the ice | a cute character cracking a block of ice with a hammer, ice shards flying |
| hit the books | a stack of textbooks wearing cartoon boxing gloves |
| under the weather | a sad little cloud wearing a scarf and holding a thermometer |

## 2. B-roll rasm (`kind: broll`, 9:16)
- quiet modern exam hall with soft morning light, rows of empty desks
- close-up of a student's hands writing an essay at a wooden desk, warm lamp light
- cozy desk with open books, coffee cup and laptop, golden hour

## 3. Video clip (`kind: clip`, 9:16, ovozsiz ishlatiladi)
Bitta kadr, bitta kamera harakati, aniq nomlang (static locked-off, slow push-in, orbit).
- rainy London street at dusk, a red double-decker bus passes, slow push-in, cinematic
- a student nervously walks into a bright exam hall and sits down, static locked-off camera
- electric blue light particles slowly rising around an open book on a deep navy background, slow orbit

## 4. Poster artwork (`poster_studio.py art`) — faqat matnsiz
Poster Figma'da quriladi; Flow faqat sahna/hero obyektni chizadi. Prompt `flow_design.art_scenes()` da spec'dan yig'iladi:
- **Reference rejimi (100% parity):** reference 1 = referencening clean plate'i (matnlari o'chirilgan), 2–3 = foydalanuvchi assetlari
  (`source.assets[].role`). Claude `art.description` ga referencedagi sahnani aniq yozadi (obyekt, kamera, yorug'lik, rang, tekstura)
  va `art.replace` ga almashtirishni: "Replace the reference's golden cup with the exact silver trophy from reference image 2, same position and scale."
  Prompt kompozitsiya, kamera, yorug'lik va palitrani aynan takrorlashni talab qiladi; matn joylari `parity.text_boxes` dan.
- **Istak rejimi:** `art.description` foydalanuvchi so'zidan. Formula: `[sahna va hero obyekt], [yorug'lik], [qayer bo'sh qoladi]`
  - **Natija:** deep navy background with soft electric blue light rays from above and a few golden confetti pieces, celebratory, empty center area
  - **Kurs reklamasi:** deep navy academic atmosphere with floating electric blue particles, open books and a fountain pen on the right, empty left side
  - **E'lon (Mock Exam):** minimal dark navy desk with exam papers and a clock, dramatic top light, empty upper half
  - **Speaking Club:** cozy dark navy café interior with warm bokeh lights and glowing speech bubble shapes
- **Tahrir:** `poster_studio.py art --id <id> --change "add brighter electric blue light rays"` — joriy artwork reference 1, faqat o'zgarish.
- Har promptga avtomatik: "no text, letters, numbers, logos, icons, badges, buttons or UI elements". Import'dan keyin artworkni ochib tekshir.

## 5. Foto tahriri (`--edit-photo`, reference bilan)
- **Studiya portreti (standart):** skript tayyor promptni ishlatadi — yuz va shaxs o'zgarmaydi.
- **Rasmiy kiyim:** "Same person from the reference photo wearing a tailored dark navy suit and white shirt, identical face, hair and pose, studio light"

## 6. Karusel slayd rasmi (`flow_assets.py request --poster <id> --image slide1 --prompt ...`, 1:1)
- a cartoon student floating happily above the moon, clean illustration, plenty of empty space

## 7. Reels muqovasi (`thumbnail.prompt`, 9:16)
- Muqova — `poster_studio.py new --type cover` (Figma, `assets/poster_templates/cover.json`). `art.description` faqat sahna: "excited student holding a score sheet, electric blue light"; sarlavha (`title/accent/tag`) Figma matn qatlami.
