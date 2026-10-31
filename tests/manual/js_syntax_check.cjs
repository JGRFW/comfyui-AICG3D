const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const root = path.resolve(__dirname, "..", "..");
const web = path.join(root, "web");
const files = fs.readdirSync(web)
    .filter((name) => name.endsWith(".js"))
    .map((name) => path.join(web, name));

for (const file of files) {
    execFileSync(process.execPath, ["--check", file], { stdio: "pipe" });
}
console.log(`PASS ${files.length} frontend JavaScript syntax checks`);
