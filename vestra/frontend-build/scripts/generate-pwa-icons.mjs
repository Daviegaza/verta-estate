/**
 * PWA Icon Generator
 *
 * Generates minimal valid PNG icons for Vestra PWA at all sizes
 * referenced in manifest.json. Uses pure Node.js (no dependencies).
 *
 * Run: node scripts/generate-pwa-icons.mjs
 *
 * These are placeholder solid-color icons. For production, replace
 * with properly designed icons from a design tool.
 */
import fs from 'fs';
import path from 'path';
import zlib from 'zlib';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// -- Config -------------------------------------------------------------------
const EMERALD_R = 0x05;
const EMERALD_G = 0x96;
const EMERALD_B = 0x69;

const SCREENSHOT_TOP_R = EMERALD_R;
const SCREENSHOT_TOP_G = EMERALD_G;
const SCREENSHOT_TOP_B = EMERALD_B;
const SCREENSHOT_BOT_R = 0x06;
const SCREENSHOT_BOT_G = 0x74;
const SCREENSHOT_BOT_B = 0x4e;

const ICON_SIZES = [72, 96, 128, 144, 152, 192, 384, 512];

const PUBLIC_DIR = path.join(__dirname, '..', 'public');
const ICONS_DIR = path.join(PUBLIC_DIR, 'icons');
const SCREENSHOTS_DIR = path.join(PUBLIC_DIR, 'screenshots');

// -- CRC-32 (PNG uses this, not Adler-32 like zlib) ---------------------------
function crc32(buf) {
  let crc = 0xffffffff;
  const table = new Int32Array(256);
  for (let i = 0; i < 256; i++) {
    let c = i;
    for (let j = 0; j < 8; j++) {
      c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1);
    }
    table[i] = c;
  }
  for (let i = 0; i < buf.length; i++) {
    crc = table[(crc ^ buf[i]) & 0xff] ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

// -- PNG Chunk ----------------------------------------------------------------
function pngChunk(type, data) {
  const typeB = Buffer.from(type, 'ascii');
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length);
  const crcInput = Buffer.concat([typeB, data]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(crcInput));
  return Buffer.concat([len, typeB, data, crc]);
}

// -- Full PNG generator -------------------------------------------------------
function createPNG(width, height, getPixel) {
  const signature = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

  // IHDR
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8;  // bit depth
  ihdr[9] = 2;  // color type: RGB
  ihdr[10] = 0; // compression: deflate
  ihdr[11] = 0; // filter: adaptive
  ihdr[12] = 0; // interlace: none
  const ihdrChunk = pngChunk('IHDR', ihdr);

  // Raw pixel data: each row = [filter_byte(0), R, G, B, R, G, B, ...]
  const rowBytes = 1 + width * 3;
  const raw = Buffer.alloc(height * rowBytes);
  for (let y = 0; y < height; y++) {
    const rowStart = y * rowBytes;
    raw[rowStart] = 0; // filter: None
    for (let x = 0; x < width; x++) {
      const [r, g, b] = getPixel(x, y, width, height);
      const off = rowStart + 1 + x * 3;
      raw[off] = r;
      raw[off + 1] = g;
      raw[off + 2] = b;
    }
  }

  // IDAT (zlib-compressed raw data)
  const compressed = zlib.deflateSync(raw);
  const idatChunk = pngChunk('IDAT', compressed);

  // IEND
  const iendChunk = pngChunk('IEND', Buffer.alloc(0));

  return Buffer.concat([signature, ihdrChunk, idatChunk, iendChunk]);
}

// -- Main ---------------------------------------------------------------------
function main() {
  // Ensure directories exist
  for (const dir of [ICONS_DIR, SCREENSHOTS_DIR]) {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
      console.log(`  Created ${path.relative(PUBLIC_DIR, dir)}/`);
    }
  }

  // Solid emerald icons
  for (const size of ICON_SIZES) {
    const png = createPNG(size, size, () => [EMERALD_R, EMERALD_G, EMERALD_B]);
    const filename = `icon-${size}x${size}.png`;
    fs.writeFileSync(path.join(ICONS_DIR, filename), png);
    const kb = (png.length / 1024).toFixed(1);
    console.log(`  ${filename}  (${size}x${size}, ${kb} KB)`);
  }

  // Maskable icon: emerald center 80%, white margin for safe zone
  const maskable = createPNG(512, 512, (x, y, w) => {
    const margin = w * 0.1;
    if (x < margin || x >= w - margin || y < margin || y >= w - margin) {
      return [0xff, 0xff, 0xff];
    }
    return [EMERALD_R, EMERALD_G, EMERALD_B];
  });
  fs.writeFileSync(path.join(ICONS_DIR, 'maskable-icon-512x512.png'), maskable);
  const kb = (maskable.length / 1024).toFixed(1);
  console.log(`  maskable-icon-512x512.png  (512x512, ${kb} KB)`);

  // Screenshot: home (1280x720) - vertical gradient
  const homePng = createPNG(1280, 720, (x, y, h) => {
    const t = y / h;
    return [
      Math.round(SCREENSHOT_TOP_R + (SCREENSHOT_BOT_R - SCREENSHOT_TOP_R) * t),
      Math.round(SCREENSHOT_TOP_G + (SCREENSHOT_BOT_G - SCREENSHOT_TOP_G) * t),
      Math.round(SCREENSHOT_TOP_B + (SCREENSHOT_BOT_B - SCREENSHOT_TOP_B) * t),
    ];
  });
  fs.writeFileSync(path.join(SCREENSHOTS_DIR, 'home.png'), homePng);
  const kb1 = (homePng.length / 1024).toFixed(1);
  console.log(`  screenshots/home.png  (1280x720, ${kb1} KB)`);

  // Screenshot: home-mobile (750x1334) - vertical gradient
  const mobilePng = createPNG(750, 1334, (x, y, h) => {
    const t = y / h;
    return [
      Math.round(SCREENSHOT_TOP_R + (SCREENSHOT_BOT_R - SCREENSHOT_TOP_R) * t),
      Math.round(SCREENSHOT_TOP_G + (SCREENSHOT_BOT_G - SCREENSHOT_TOP_G) * t),
      Math.round(SCREENSHOT_TOP_B + (SCREENSHOT_BOT_B - SCREENSHOT_TOP_B) * t),
    ];
  });
  fs.writeFileSync(path.join(SCREENSHOTS_DIR, 'home-mobile.png'), mobilePng);
  const kb2 = (mobilePng.length / 1024).toFixed(1);
  console.log(`  screenshots/home-mobile.png  (750x1334, ${kb2} KB)`);

  console.log('\n  All PWA assets generated successfully.');
  console.log('  Tip: Replace with proper designs from a design tool for production.');
}

main();
