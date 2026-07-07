#!/usr/bin/env node
/**
 * update-seed-images.mjs
 * Replace all Unsplash URLs in seed-menu.mjs with local /menu-images/ paths
 */
import { readFileSync, writeFileSync } from 'fs';
import { join } from 'path';

const seedPath = join(import.meta.dirname, 'seed-menu.mjs');
let content = readFileSync(seedPath, 'utf-8');

const localImages = [
  "/menu-images/01-goi-cuon-tom-thit.png",
  "/menu-images/02-nem-ran-ha-noi.png",
  "/menu-images/03-banh-xeo-mien-tay.png",
  "/menu-images/04-banh-cuon-thanh-tri.png",
  "/menu-images/05-goi-xoai-tom-su.png",
  "/menu-images/06-banh-mi-pate-sai-gon.png",
  "/menu-images/07-sup-mang-cua.png",
  "/menu-images/08-pho-bo-tai-nam.png",
  "/menu-images/09-pho-ga-ta.png",
  "/menu-images/10-bun-bo-hue.png",
  "/menu-images/11-bun-cha-ha-noi.png",
  "/menu-images/12-bun-rieu-cua-dong.png",
  "/menu-images/13-bun-mam-mien-tay.png",
  "/menu-images/14-bun-dau-mam-tom.png",
  "/menu-images/15-com-tam-suon-bi-cha.png",
  "/menu-images/16-com-ga-hoi-an.png",
  "/menu-images/17-com-suon-nuong.png",
  "/menu-images/18-com-ca-kho-to.png",
  "/menu-images/19-com-chien-sai-gon.png",
  "/menu-images/20-com-hen-hue.png",
  "/menu-images/21-com-bo-luc-lac.png",
  "/menu-images/22-tom-hum-nuong-mo-hanh.png",
  "/menu-images/23-ca-loc-nuong-trui.png",
  "/menu-images/24-tom-rang-muoi-tay-ninh.png",
  "/menu-images/25-cua-rang-me.png",
  "/menu-images/26-muc-xao-sa-te.png",
  "/menu-images/27-ngheu-hap-sa.png",
  "/menu-images/28-oc-huong-rang-bo-toi.png",
  "/menu-images/29-lau-chua-ca-lang.png",
  "/menu-images/30-lau-bo-nhung-giam.png",
  "/menu-images/31-lau-nam-chay.png",
  "/menu-images/32-lau-ga-la-e-da-lat.png",
  "/menu-images/33-lau-hai-san-chua-cay.png",
  "/menu-images/34-lau-de-thuoc-bac.png",
  "/menu-images/35-lau-mam-mien-tay.png",
  "/menu-images/36-ga-nuong-mat-ong.png",
  "/menu-images/37-ga-hap-la-chanh.png",
  "/menu-images/38-canh-ga-chien-nuoc-mam.png",
  "/menu-images/39-ga-xao-sa-ot.png",
  "/menu-images/40-ga-nuong-muoi-ot-xanh.png",
  "/menu-images/41-ga-tiem-thuoc-bac.png",
  "/menu-images/42-ga-ro-ti-kieu-viet.png",
  "/menu-images/43-mi-quang-tom-thit.png",
  "/menu-images/44-cao-lau-hoi-an.png",
  "/menu-images/45-be-thui-cau-mong.png",
  "/menu-images/46-hu-tieu-nam-vang.png",
  "/menu-images/47-banh-trang-cuon-thit-heo.png",
  "/menu-images/48-chao-long-sai-gon.png",
  "/menu-images/49-xoi-ga-ha-noi.png",
  "/menu-images/50-pho-chay-nam-dong-co.png",
  "/menu-images/51-com-chien-chay-ngu-sac.png",
  "/menu-images/52-goi-cuon-chay.png",
  "/menu-images/53-canh-kho-qua-nhoi-nam.png",
  "/menu-images/54-dau-hu-sot-ca-chua.png",
  "/menu-images/55-mi-quang-chay.png",
  "/menu-images/56-bun-chay-hue.png",
  "/menu-images/57-ca-phe-sua-da.png",
  "/menu-images/58-ca-phe-trung-ha-noi.png",
  "/menu-images/59-bac-xiu-sai-gon.png",
  "/menu-images/60-tra-dao-cam-sa.png",
  "/menu-images/61-tra-sen-tay-ho.png",
  "/menu-images/62-tra-sua-tran-chau.png",
  "/menu-images/63-ca-phe-dua.png",
  "/menu-images/64-nuoc-ep-cam-tuoi.png",
  "/menu-images/65-sinh-to-bo-dak-lak.png",
  "/menu-images/66-nuoc-ep-dua-hau.png",
  "/menu-images/67-sinh-to-xoai-hoa-loc.png",
  "/menu-images/68-nuoc-rau-ma.png",
  "/menu-images/69-sinh-to-dau-tay-da-lat.png",
  "/menu-images/70-nuoc-mia-sai-gon.png",
  "/menu-images/71-che-khuc-bach.png",
  "/menu-images/72-banh-flan-caramel.png",
  "/menu-images/73-che-buoi.png",
  "/menu-images/74-suong-sa-hat-luu.png",
  "/menu-images/75-che-troi-nuoc.png",
  "/menu-images/76-banh-chuoi-nuong.png",
  "/menu-images/77-xoi-xoai.png",
  "/menu-images/78-dia-trai-cay-theo-mua.png",
  "/menu-images/79-xoai-cat-hoa-loc.png",
  "/menu-images/80-sau-rieng-ri6.png",
  "/menu-images/81-dua-hau-lanh.png",
  "/menu-images/82-buoi-da-xanh-ben-tre.png",
  "/menu-images/83-thanh-long-binh-thuan.png",
  "/menu-images/84-du-du-chin-mat-ong.png",
  "/menu-images/85-bia-sai-gon-special.png",
  "/menu-images/86-bia-ha-noi.png",
  "/menu-images/87-bia-tiger-crystal.png",
  "/menu-images/88-bia-hoi-ha-noi.png",
  "/menu-images/89-ruou-nep-cam.png",
  "/menu-images/90-ruou-mo-ha-noi.png",
  "/menu-images/91-cocktail-chanh-dao-mat-ong.png",
];

// Find all img: "..." occurrences in order and replace
let idx = 0;
content = content.replace(/img:\s*"[^"]+"/g, (match) => {
  if (idx < localImages.length) {
    const replacement = `img: "${localImages[idx]}"`;
    console.log(`  #${idx+1}: ${match.slice(0, 60)}... → ${localImages[idx]}`);
    idx++;
    return replacement;
  }
  return match;
});

writeFileSync(seedPath, content, 'utf-8');
console.log(`\n✅ Replaced ${idx} image URLs with local paths`);
