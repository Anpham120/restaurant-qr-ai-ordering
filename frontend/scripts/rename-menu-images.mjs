#!/usr/bin/env node
/**
 * rename-menu-images.mjs
 * Rename Vietnamese menu images to URL-friendly filenames
 * "01 - Gỏi cuốn tôm thịt.png" → "01-goi-cuon-tom-thit.png"
 */
import { readdirSync, renameSync } from 'fs';
import { join } from 'path';

const dir = join(import.meta.dirname, '..', 'apps', 'customer-web', 'public', 'menu-images');

// Vietnamese diacritics → ASCII map
const vnMap = {
  'à':'a','á':'a','ả':'a','ã':'a','ạ':'a','ă':'a','ằ':'a','ắ':'a','ẳ':'a','ẵ':'a','ặ':'a',
  'â':'a','ầ':'a','ấ':'a','ẩ':'a','ẫ':'a','ậ':'a','đ':'d','è':'e','é':'e','ẻ':'e','ẽ':'e',
  'ẹ':'e','ê':'e','ề':'e','ế':'e','ể':'e','ễ':'e','ệ':'e','ì':'i','í':'i','ỉ':'i','ĩ':'i',
  'ị':'i','ò':'o','ó':'o','ỏ':'o','õ':'o','ọ':'o','ô':'o','ồ':'o','ố':'o','ổ':'o','ỗ':'o',
  'ộ':'o','ơ':'o','ờ':'o','ớ':'o','ở':'o','ỡ':'o','ợ':'o','ù':'u','ú':'u','ủ':'u','ũ':'u',
  'ụ':'u','ư':'u','ừ':'u','ứ':'u','ử':'u','ữ':'u','ự':'u','ỳ':'y','ý':'y','ỷ':'y','ỹ':'y','ỵ':'y',
  'À':'a','Á':'a','Ả':'a','Ã':'a','Ạ':'a','Ă':'a','Ằ':'a','Ắ':'a','Ẳ':'a','Ẵ':'a','Ặ':'a',
  'Â':'a','Ầ':'a','Ấ':'a','Ẩ':'a','Ẫ':'a','Ậ':'a','Đ':'d','È':'e','É':'e','Ẻ':'e','Ẽ':'e',
  'Ẹ':'e','Ê':'e','Ề':'e','Ế':'e','Ể':'e','Ễ':'e','Ệ':'e','Ì':'i','Í':'i','Ỉ':'i','Ĩ':'i',
  'Ị':'i','Ò':'o','Ó':'o','Ỏ':'o','Õ':'o','Ọ':'o','Ô':'o','Ồ':'o','Ố':'o','Ổ':'o','Ỗ':'o',
  'Ộ':'o','Ơ':'o','Ờ':'o','Ớ':'o','Ở':'o','Ỡ':'o','Ợ':'o','Ù':'u','Ú':'u','Ủ':'u','Ũ':'u',
  'Ụ':'u','Ư':'u','Ừ':'u','Ứ':'u','Ử':'u','Ữ':'u','Ự':'u','Ỳ':'y','Ý':'y','Ỷ':'y','Ỹ':'y','Ỵ':'y',
};

function toSlug(str) {
  return str
    .split('').map(c => vnMap[c] || c).join('')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

const files = readdirSync(dir).filter(f => f.endsWith('.png'));
const mapping = {};

for (const oldName of files) {
  const base = oldName.replace('.png', '');
  const slug = toSlug(base);
  const newName = `${slug}.png`;
  
  if (oldName !== newName) {
    renameSync(join(dir, oldName), join(dir, newName));
  }
  
  // Extract number
  const num = parseInt(base.split(' - ')[0]);
  mapping[num] = `/menu-images/${newName}`;
  console.log(`  ${oldName} → ${newName}`);
}

// Output the mapping as JSON for seed script
console.log('\n📋 Image mapping JSON:');
console.log(JSON.stringify(mapping, null, 2));
console.log(`\n✅ Renamed ${files.length} files`);
