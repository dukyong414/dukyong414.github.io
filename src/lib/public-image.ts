import { existsSync } from "node:fs";
import { join } from "node:path";

/** Keep a public image URL only while the file is still in public/images. */
export function publicImage(src: string | undefined): string | undefined {
  if (!src || !src.startsWith("/images/")) return undefined;
  const name = src.slice("/images/".length);
  if (!/^[A-Za-z0-9._-]+$/.test(name)) return undefined;
  const file = join(process.cwd(), "public", "images", name);
  return existsSync(file) ? src : undefined;
}
