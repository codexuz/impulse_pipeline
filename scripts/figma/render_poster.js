// Impulse poster renderer for Figma (`use_figma`). Do not edit by hand per poster.
// `python scripts/poster_studio.py figma --id <poster_id>` puts the resolved poster spec into DOC below
// and writes workspace/05_posters/figma/<poster_id>.js. Pass that file's content to use_figma as `code`.
//
// DOC.mode:
//   "render": builds the poster's frames (Feed / Story / ...) and the component kit on the poster's own page.
//             Previous frames are kept on the page as an archive.
//   "texts":  changes only the texts (text layers and chip/contact labels) in the existing frames. Takes about 2 s.
// Every layer carries shared plugin data impulse/lid = the layer id from the spec, so it can be found later.
const DOC = __DOC__;

const NS = "impulse";
const tag = (node, key, value) => node.setSharedPluginData(NS, key, String(value));
const lid = (node) => node.getSharedPluginData(NS, "lid");

// ---------- Page ----------
let page = figma.root.children.find((p) => p.name === DOC.page);
if (!page) { page = figma.createPage(); page.name = DOC.page; }
await figma.setCurrentPageAsync(page);

// ---------- Fonts ----------
const available = await figma.listAvailableFontsAsync();
const styleSets = {};
for (const f of available) (styleSets[f.fontName.family] ||= new Set()).add(f.fontName.style);
const ALIASES = { "SemiBold": ["SemiBold", "Semi Bold"], "ExtraBold": ["ExtraBold", "Extra Bold"], "Black Italic": ["Black Italic", "ExtraBold Italic", "Bold Italic"] };
const fontCache = {};
async function font(family, style) {
  const key = family + "/" + style;
  if (fontCache[key]) return fontCache[key];
  const have = styleSets[family];
  if (!have) throw new Error(`Font family not available in Figma: ${family}`);
  const pick = (ALIASES[style] || [style]).find((s) => have.has(s));
  if (!pick) throw new Error(`Font style missing: ${family} ${style}. Available: ${[...have].join(", ")}`);
  const fontName = { family, style: pick };
  await figma.loadFontAsync(fontName);
  return (fontCache[key] = fontName);
}

// ---------- Helpers ----------
function applyBox(node, l) {
  if (l.opacity != null) node.opacity = l.opacity;
  if (l.radius != null && "cornerRadius" in node) node.cornerRadius = l.radius;
  if (l.fills && "fills" in node) node.fills = l.fills;
  if (l.strokes && "strokes" in node) { node.strokes = l.strokes; node.strokeWeight = l.strokeWeight ?? 1; }
  if (l.effects) node.effects = l.effects;
  if (l.blend) node.blendMode = l.blend;
}

async function styleText(t, l) {
  t.fontName = await font(l.font, l.style);
  t.fontSize = l.size;
  t.characters = l.segments.map((s) => s.text).join("");
  t.fills = l.fills;
  if (l.lineHeight != null) t.lineHeight = { unit: "PERCENT", value: l.lineHeight };
  if (l.letterSpacing != null) t.letterSpacing = { unit: "PERCENT", value: l.letterSpacing };
  if (l.align) t.textAlignHorizontal = l.align;
  if (l.case) t.textCase = l.case;
  let at = 0;
  for (const s of l.segments) {
    const end = at + s.text.length;
    if (s.text.length) {
      if (s.style || s.font) t.setRangeFontName(at, end, await font(s.font || l.font, s.style || l.style));
      if (s.size) t.setRangeFontSize(at, end, s.size);
      if (s.fills) t.setRangeFills(at, end, s.fills);
      if (s.letterSpacing != null) t.setRangeLetterSpacing(at, end, { unit: "PERCENT", value: s.letterSpacing });
    }
    at = end;
  }
  if (l.effects) t.effects = l.effects;
  if (l.opacity != null) t.opacity = l.opacity;
}

// ---------- Texts-only mode ----------
if (DOC.mode === "texts") {
  const changed = [];
  for (const fr of DOC.frames) {
    const frame = await figma.getNodeByIdAsync(DOC.targets[fr.fmt]);
    if (!frame) throw new Error(`Frame for ${fr.fmt} not found (${DOC.targets[fr.fmt]}). Run a full render.`);
    const byId = {};
    frame.findAll((n) => !!lid(n)).forEach((n) => (byId[lid(n)] = n));
    const walk = async (layers) => {
      for (const l of layers) {
        const node = byId[l.id];
        if (l.type === "text" && node && node.type === "TEXT") {
          const want = l.segments.map((s) => s.text).join("");
          if (node.characters !== want) {
            for (const seg of node.getStyledTextSegments(["fontName"])) await figma.loadFontAsync(seg.fontName);
            await styleText(node, l);
            changed.push(`${fr.fmt}:${l.id}`);
          }
        } else if (l.type === "item" && node && node.type === "INSTANCE") {
          const key = Object.keys(node.componentProperties).find((k) => k.startsWith("Label"));
          if (node.componentProperties[key].value !== l.text) {
            node.setProperties({ [key]: l.text });
            changed.push(`${fr.fmt}:${l.id}`);
          }
        }
        if (l.children) await walk(l.children);
      }
    };
    await walk(fr.layers);
    for (const l of fr.layers) {
      if (l.bottom != null && byId[l.id]) byId[l.id].y = fr.H - l.bottom - byId[l.id].height;
    }
  }
  return { mode: "texts", changed, bounds: await collectBounds() };
}

// ---------- Render mode ----------
// 1) Archive the previous version on this page
const archived = [];
const previous = page.children.filter((n) => n.getSharedPluginData(NS, "poster") === DOC.poster_id && !n.getSharedPluginData(NS, "archived"));
let originX = 0, originY = 0;
if (previous.length) {
  originX = Math.min(...previous.map((n) => n.x));
  originY = Math.min(...previous.map((n) => n.y));
  const bottom = Math.max(...page.children.map((n) => n.y + n.height));
  const stamp = DOC.stamp;
  for (const n of previous) {
    n.y = bottom + 400 + (n.y - originY);
    n.name = `[arxiv ${stamp}] ${n.name}`;
    tag(n, "archived", stamp);
    archived.push(n.id);
  }
}
// Upload placeholders created by upload_assets
for (const id of DOC.cleanup || []) {
  const n = await figma.getNodeByIdAsync(id);
  if (n && n.type !== "PAGE" && n.type !== "DOCUMENT") n.remove();
}

// 2) Component kit: icons + item components (chip, contact, ...)
const created = [];
const kitX = originX + DOC.frames.reduce((s, f) => s + f.W + 120, 0);
const kit = figma.createFrame();
kit.name = `${DOC.title} — Components`;
kit.fills = [{ type: "SOLID", color: { r: 0.04, g: 0.086, b: 0.19 } }];
kit.x = kitX; kit.y = originY;
tag(kit, "poster", DOC.poster_id); tag(kit, "role", "kit");
created.push(kit.id);

const icons = {};
let cx = 40, cy = 40, rowH = 0;
for (const [key, icon] of Object.entries(DOC.icons)) {
  const comp = figma.createComponent();
  comp.name = icon.name;
  comp.resize(icon.size, icon.size);
  comp.fills = [];
  const svg = figma.createNodeFromSvg(icon.svg);
  svg.name = "vector";
  svg.fills = [];
  comp.appendChild(svg);
  svg.x = 0; svg.y = 0;
  svg.resize(icon.size, icon.size);
  svg.constraints = { horizontal: "SCALE", vertical: "SCALE" };
  svg.findAll(() => true).forEach((n) => { if ("constraints" in n) n.constraints = { horizontal: "SCALE", vertical: "SCALE" }; });
  kit.appendChild(comp);
  comp.x = cx; comp.y = cy;
  cx += icon.size + 28; rowH = Math.max(rowH, icon.size);
  if (cx > 820) { cx = 40; cy += rowH + 28; rowH = 0; }
  icons[key] = comp;
}
cy += rowH + 60;

const items = {};
for (const [name, st] of Object.entries(DOC.styles)) {
  if (!st.used) continue;
  const comp = figma.createComponent();
  comp.name = st.title;
  comp.layoutMode = st.direction || "HORIZONTAL";
  comp.primaryAxisSizingMode = "AUTO"; comp.counterAxisSizingMode = "AUTO";
  comp.counterAxisAlignItems = "CENTER";
  comp.itemSpacing = st.gap ?? 12;
  [comp.paddingTop, comp.paddingRight, comp.paddingBottom, comp.paddingLeft] = st.padding || [0, 0, 0, 0];
  comp.fills = st.fills || [];
  if (st.radius != null) comp.cornerRadius = st.radius;
  if (st.strokes) { comp.strokes = st.strokes; comp.strokeWeight = st.strokeWeight ?? 1; }
  if (st.effects) comp.effects = st.effects;
  const iconInst = icons[st.sample_icon].createInstance();
  iconInst.name = "Icon";
  comp.appendChild(iconInst);
  const label = figma.createText();
  label.name = "Label";
  await styleText(label, { font: st.font, style: st.style, size: st.size, fills: st.textFills, letterSpacing: st.letterSpacing, segments: [{ text: st.sample_text }] });
  comp.appendChild(label);
  const labelKey = comp.addComponentProperty("Label", "TEXT", st.sample_text);
  label.componentPropertyReferences = { characters: labelKey };
  const iconKey = comp.addComponentProperty("Icon", "INSTANCE_SWAP", icons[st.sample_icon].id);
  iconInst.componentPropertyReferences = { mainComponent: iconKey };
  comp.description = st.description || "";
  kit.appendChild(comp);
  comp.x = 40; comp.y = cy; cy += comp.height + 40;
  items[name] = { comp, labelKey, iconKey };
}
kit.resize(900, Math.max(cy, 200));

// 3) Frames
async function build(l, parent, fr, inStack) {
  let node;
  if (l.type === "text") {
    node = figma.createText();
    await styleText(node, l);
  } else if (l.type === "rect" || l.type === "image") {
    node = figma.createRectangle();
    node.resize(l.w, l.h);
    if (l.type === "image") {
      const img = DOC.images[l.image];
      node.fills = [{ type: "IMAGE", imageHash: img.hash, scaleMode: l.fit || "FILL" }];
    }
  } else if (l.type === "ellipse") {
    node = figma.createEllipse();
    node.resize(l.w, l.h);
  } else if (l.type === "icon") {
    node = icons[l.icon].createInstance();
  } else if (l.type === "item") {
    const it = items[l.style];
    node = it.comp.createInstance();
    node.setProperties({ [it.labelKey]: l.text, [it.iconKey]: icons[l.icon].id });
  } else if (l.type === "stack") {
    node = figma.createAutoLayout(l.direction || "VERTICAL", { name: l.name || l.id, itemSpacing: l.gap ?? 0 });
    node.fills = [];
    if (l.padding) [node.paddingTop, node.paddingRight, node.paddingBottom, node.paddingLeft] = l.padding;
    if (l.justify) node.primaryAxisAlignItems = l.justify;
    if (l.align) node.counterAxisAlignItems = l.align;
  } else {
    throw new Error(`Unknown layer type: ${l.type}`);
  }
  node.name = l.name || l.id;
  tag(node, "lid", l.id);
  if (l.type !== "text") applyBox(node, l);
  parent.appendChild(node);

  if (l.type === "text" && l.w != null) {
    node.resize(l.w, node.height);
    node.textAutoResize = "HEIGHT";
  }
  if (l.type === "stack" && l.w != null) {
    // Fixed width before the children are added, so their "fill" width has something to fill
    node.resize(l.w, Math.max(1, node.height));
    const horizontal = (l.direction || "VERTICAL") === "HORIZONTAL";
    node.primaryAxisSizingMode = horizontal ? "FIXED" : "AUTO";
    node.counterAxisSizingMode = horizontal ? "AUTO" : "FIXED";
  }
  if (inStack && l.fill) {
    node.layoutSizingHorizontal = "FILL";
    if (l.type === "text") node.textAutoResize = "HEIGHT";
  }
  if (l.type === "stack") for (const c of l.children || []) await build(c, node, fr, true);
  if (inStack && l.absolute) { node.layoutPositioning = "ABSOLUTE"; }
  if (!inStack || l.absolute) {
    node.x = l.x != null ? l.x : l.right != null ? fr.W - l.right - node.width : l.centerX ? (fr.W - node.width) / 2 : 0;
    node.y = l.y != null ? l.y : l.bottom != null ? fr.H - l.bottom - node.height : l.centerY ? (fr.H - node.height) / 2 : 0;
  }
  if (l.locked) node.locked = true;
  if (l.hidden) node.visible = false;
  return node;
}

const frames = {};
let fx = originX;
for (const fr of DOC.frames) {
  const frame = figma.createFrame();
  frame.name = fr.name;
  frame.resize(fr.W, fr.H);
  frame.x = fx; frame.y = originY;
  frame.clipsContent = true;
  frame.fills = fr.fills;
  tag(frame, "poster", DOC.poster_id); tag(frame, "fmt", fr.fmt);
  for (const l of fr.layers) await build(l, frame, fr, false);
  if (fr.safe) {
    // Instagram UI zones (hidden guide): top and bottom bars of the Story
    const guide = figma.createFrame();
    guide.name = "Safe zones (guide)"; guide.fills = []; guide.resize(fr.W, fr.H); guide.x = 0; guide.y = 0;
    for (const [y, h] of [[0, fr.safe.top], [fr.H - fr.safe.bottom, fr.safe.bottom]]) {
      const r = figma.createRectangle(); r.resize(fr.W, h); r.y = y; r.name = "Instagram UI";
      r.fills = [{ type: "SOLID", color: { r: 1, g: 0.32, b: 0.32 }, opacity: 0.18 }];
      guide.appendChild(r);
    }
    frame.appendChild(guide); guide.locked = true; guide.visible = false;
  }
  frames[fr.fmt] = frame.id;
  created.push(frame.id);
  fx += fr.W + 120;
}

async function collectBounds() {
  const out = {};
  for (const fr of DOC.frames) {
    const frame = await figma.getNodeByIdAsync((DOC.mode === "texts" ? DOC.targets : frames)[fr.fmt]);
    const fb = frame.absoluteBoundingBox;
    out[fr.fmt] = {};
    for (const n of frame.findAll((n) => !!lid(n) && (n.type === "TEXT" || n.type === "INSTANCE" || lid(n) === "logo"))) {
      const b = n.absoluteBoundingBox;
      out[fr.fmt][lid(n)] = [Math.round(b.x - fb.x), Math.round(b.y - fb.y), Math.round(b.width), Math.round(b.height)];
    }
  }
  return out;
}

return { mode: "render", page: page.id, frames, kit: kit.id, archived, createdNodeIds: created, bounds: await collectBounds() };
