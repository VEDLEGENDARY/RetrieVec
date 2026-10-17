import { readFile, readdir } from "node:fs/promises";
import { gzipSync } from "node:zlib";
const baseline = {
  revision: "a5673cbc6a716356a9c77816c7656651e36426db",
  gzipBytes: 114664,
};
const directory = new URL("../dist/assets/", import.meta.url);
const files = (await readdir(directory)).filter((file) =>
  /\.(css|js)$/.test(file),
);
const sizes = await Promise.all(
  files.map(async (file) => ({
    file,
    gzipBytes: gzipSync(await readFile(new URL(file, directory))).length,
  })),
);
const total = sizes.reduce((sum, item) => sum + item.gzipBytes, 0);
const growth = total - baseline.gzipBytes;
console.log(
  JSON.stringify(
    {
      baseline,
      assets: sizes,
      totalGzipBytes: total,
      growthGzipBytes: growth,
      limitBytes: 25000,
    },
    null,
    2,
  ),
);
if (growth >= 25000)
  throw new Error(
    "Task 03 runtime JavaScript/CSS growth must stay below 25 KB gzipped",
  );
