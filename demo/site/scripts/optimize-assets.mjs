// One-off: optimize the Higgsfield asset pack into web-ready files.
// Images -> WebP (sized per placement). Videos -> H.264 MP4, 1080p max, CRF 28,
// no audio, +faststart, plus a WebP poster frame extracted per video.
// Usage: node scripts/optimize-assets.mjs <source-dir>

import { execFileSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import sharp from "sharp";
import ffmpeg from "ffmpeg-static";

const SRC = process.argv[2];
if (!SRC) throw new Error("pass the source dir");
const OUT = join(import.meta.dirname, "..", "public", "assets");
mkdirSync(OUT, { recursive: true });

// name -> [sourceFile, targetWidth]
const IMAGES = {
  "observatory.webp": ["hf_20260711_104236_368b4019-c8ea-4679-9a7a-6cb070789603.png", 2000],
  "terrain.webp": ["hf_20260711_104236_77cd5ffd-4a4a-4c6f-a58d-599d629569a0.png", 1200],
  "flow.webp": ["hf_20260711_104236_c3dc2f83-0ac0-42bd-8a01-bb97bafcfa47.png", 1200],
  "balance.webp": ["hf_20260711_104236_c659771b-4634-420d-aaec-e54f1fb2ab09.png", 1200],
  "seal.webp": ["hf_20260711_104237_2050b530-5a28-4a25-b1ed-788dfc551a88.png", 900],
  "desk.webp": ["hf_20260711_104237_b824b6f7-2043-40fe-9ec1-0b40e47fb9f0.png", 2200],
  "dots.webp": ["hf_20260711_104237_ede79da3-727d-4306-a083-9550b56e7e01.png", 2000],
  "eth-dark.webp": ["hf_20260711_104237_f7d1970a-daa3-4d81-9306-e1a571dfb6a7.png", 1000],
  "eth-gold.webp": ["hf_20260711_104507_1ffd046c-aedc-4363-aae5-b8ebe3fc5328.png", 1000],
};

const VIDEOS = {
  "observatory-loop.mp4": "hf_20260711_104417_679b9422-809f-4376-ad6d-42a35447aa98.mp4",
  "video-b287.mp4": "hf_20260711_104417_b2870930-c080-4a11-a68b-364c5e091d04.mp4",
  "video-e122.mp4": "hf_20260711_104417_e1224300-a64d-4d19-a105-5ae9552434b7.mp4",
  "video-8eda.mp4": "hf_20260711_105136_8edaf04d-954a-4046-a312-3ca244e673d0.mp4",
};

for (const [out, [src, width]] of Object.entries(IMAGES)) {
  const img = sharp(join(SRC, src)).resize({ width, withoutEnlargement: true });
  await img.webp({ quality: 82 }).toFile(join(OUT, out));
  console.log("img ok:", out);
}

for (const [out, src] of Object.entries(VIDEOS)) {
  execFileSync(ffmpeg, [
    "-y", "-i", join(SRC, src),
    "-vf", "scale='min(1920,iw)':-2",
    "-c:v", "libx264", "-crf", "28", "-preset", "slow",
    "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an",
    join(OUT, out),
  ], { stdio: "pipe" });
  // poster frame from t=0.5s
  execFileSync(ffmpeg, [
    "-y", "-ss", "0.5", "-i", join(OUT, out), "-frames:v", "1",
    join(OUT, out.replace(".mp4", "-poster.png")),
  ], { stdio: "pipe" });
  await sharp(join(OUT, out.replace(".mp4", "-poster.png")))
    .webp({ quality: 78 }).toFile(join(OUT, out.replace(".mp4", "-poster.webp")));
  console.log("vid ok:", out);
}
console.log("done");
