const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH);

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    args: ["--disable-gpu"],
  });
  const page = await browser.newPage({ viewport: { width: 1500, height: 1000 } });
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(String(error?.stack || error)));
  page.on("console", (message) => {
    if (message.type() === "error") pageErrors.push(message.text());
  });

  await page.goto("http://127.0.0.1:8188", {
    waitUntil: "domcontentloaded",
    timeout: 120000,
  });
  await page.waitForFunction(
    () => Boolean(window.app?.graph && window.LiteGraph?.createNode),
    null,
    { timeout: 120000 },
  );

  const nodeId = await page.evaluate(() => {
    const node = window.LiteGraph.createNode("AICG3D_H3Loader");
    if (!node) throw new Error("AICG3D_H3Loader was not registered");
    node.pos = [500, 250];
    window.app.graph.add(node);
    window.__folderMenuTestNode = node;
    window.app.graph.setDirtyCanvas(true, true);
    return node.id;
  });
  await page.waitForTimeout(5000);
  await page.evaluate(() => window.__folderMenuTestNode?.__a3LoaderSync?.());
  await page.waitForTimeout(500);

  const modelRow = page.locator(".a3-panel .a3-row", { hasText: "FL2VA 模型" }).first();
  await modelRow.locator(".a3-select").click();
  await page.waitForSelector(".a3-menu", { state: "visible", timeout: 10000 });

  const rootState = await page.evaluate(() => ({
    widgetOptionCount: (() => {
      const widget = window.__folderMenuTestNode?.widgets?.find((item) => item.name === "fl2va_model");
      const values = widget?.options?.values || widget?.options;
      return Array.isArray(values) ? values.length : -1;
    })(),
    folders: [...document.querySelectorAll(".a3-menu .a3-folder > .a3-folder-summary .a3-folder-name")]
      .map((item) => item.textContent),
    rootOptions: [...document.querySelectorAll(".a3-menu-list > .a3-option .a3-option-label")]
      .map((item) => item.textContent),
    hasSearch: Boolean(document.querySelector(".a3-menu .a3-menu-search")),
  }));
  if (process.env.ROOT_SCREENSHOT_PATH) {
    await page.screenshot({ path: process.env.ROOT_SCREENSHOT_PATH, fullPage: true });
  }

  const minimaxFolder = page.locator(".a3-menu .a3-folder", { hasText: "MiniMax" }).first();
  if (await minimaxFolder.count()) {
    const open = await minimaxFolder.evaluate((item) => item.open);
    if (!open) await minimaxFolder.locator("summary").click();
  }
  await page.waitForTimeout(250);
  const miniMaxModels = await page.evaluate(() => [
    ...document.querySelectorAll('.a3-menu .a3-folder[open] .a3-option-label'),
  ].map((item) => item.textContent));

  const search = page.locator(".a3-menu .a3-menu-search");
  await search.fill("fastvideo");
  await page.waitForTimeout(250);
  const searchState = await page.evaluate(() => ({
    options: [...document.querySelectorAll(".a3-menu-list .a3-option")].map((item) => ({
      label: item.querySelector(".a3-option-label")?.textContent || "",
      path: item.querySelector(".a3-option-meta")?.textContent || "",
    })),
    folders: document.querySelectorAll(".a3-menu .a3-folder").length,
  }));

  const firstSearchOption = page.locator(".a3-menu-list .a3-option").first();
  const searchOptionCount = await firstSearchOption.count();
  if (searchOptionCount) await firstSearchOption.click();
  const selected = await page.evaluate(() => {
    const node = window.__folderMenuTestNode;
    return String(node?.widgets?.find((widget) => widget.name === "fl2va_model")?.value || "");
  });
  const loraSelect = page.locator(".a3-lora-rows .a3-select").first();
  await loraSelect.click();
  await page.waitForSelector(".a3-menu", { state: "visible", timeout: 10000 });
  const loraFolders = await page.evaluate(() => [
    ...document.querySelectorAll(".a3-menu .a3-folder > .a3-folder-summary .a3-folder-name"),
  ].map((item) => item.textContent));
  await page.keyboard.press("Escape");
  console.log(JSON.stringify({ debug: { rootState, miniMaxModels, searchState, searchOptionCount }, pageErrors }, null, 2));

  const screenshotPath = process.env.SCREENSHOT_PATH;
  if (screenshotPath) await page.screenshot({ path: screenshotPath, fullPage: true });
  console.log(JSON.stringify({ nodeId, rootState, miniMaxModels, searchState, loraFolders, selected }, null, 2));
  await browser.close();

  const passed = rootState.hasSearch
    && rootState.folders.includes("MiniMax")
    && rootState.folders.includes("Krea2")
    && miniMaxModels.some((label) => label.includes("fastvideo"))
    && searchState.options.length > 0
    && searchState.options.every((item) => item.label.toLowerCase().includes("fastvideo"))
    && loraFolders.some((name) => name.includes("Krea2"))
    && selected.toLowerCase().includes("fastvideo");
  if (!passed) process.exitCode = 1;
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
