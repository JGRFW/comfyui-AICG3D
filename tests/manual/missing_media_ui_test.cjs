const fs = require("fs");
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH);

(async () => {
  const workflowPath = process.env.WORKFLOW_PATH;
  if (!workflowPath || !fs.existsSync(workflowPath)) {
    throw new Error("WORKFLOW_PATH does not point to a workflow JSON file");
  }

  const browser = await chromium.launch({
    headless: true,
    executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    args: ["--disable-gpu"],
  });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  const dialogs = [];
  const acceptDialog = process.env.ACCEPT_DIALOG === "1";
  page.on("dialog", async (dialog) => {
    dialogs.push(dialog.message());
    await (acceptDialog ? dialog.accept() : dialog.dismiss());
  });

  await page.goto("http://127.0.0.1:8188", {
    waitUntil: "domcontentloaded",
    timeout: 120000,
  });
  await page.waitForFunction(
    () => Boolean(window.app?.graph && typeof window.app.loadGraphData === "function"),
    null,
    { timeout: 120000 },
  );

  const workflow = JSON.parse(fs.readFileSync(workflowPath, "utf8"));
  await page.evaluate(async (data) => {
    await window.app.loadGraphData(data, true, false);
  }, workflow);
  await page.waitForTimeout(5000);

  const result = await page.evaluate(() => {
    const nodes = window.app?.graph?._nodes || window.app?.graph?.nodes || [];
    const previousId = (node) => {
      const input = (node.inputs || []).find((item) => item?.name === "previous_segment");
      if (input?.link == null) return null;
      const link = window.app.graph.links?.[input.link] || window.app.graph._links?.[input.link];
      return link?.origin_id ?? link?.originId ?? null;
    };
    const ordinal = (node) => {
      const byId = new Map(nodes.map((item) => [String(item.id), item]));
      let value = 1;
      let current = node;
      const seen = new Set();
      while (current && !seen.has(String(current.id))) {
        seen.add(String(current.id));
        const parentId = previousId(current);
        const parent = parentId == null ? null : byId.get(String(parentId));
        if (!parent) break;
        value += 1;
        current = parent;
      }
      return value;
    };
    return {
      missingCards: document.querySelectorAll(".h3-media-loader-card.is-missing").length,
      missingButtons: [...document.querySelectorAll(".h3-sequence-actions button")]
        .map((button) => ({ text: button.textContent, title: button.title }))
        .filter((item) => String(item.text || "").includes("缺失")),
      nodeWarnings: nodes
        .filter((node) => Array.isArray(node.__h3MissingMedia) && node.__h3MissingMedia.length)
        .map((node) => ({
          id: node.id,
          type: node.type,
          missing: node.__h3MissingMedia.map((item) => item.filename),
        })),
      segmentChains: nodes
        .filter((node) => String(node.type || "").includes("SequenceSegment"))
        .map((node) => ({
          id: node.id,
          owned: node.properties?.minimax_h3_inline_media_owned,
          previousId: previousId(node),
          ordinal: ordinal(node),
        })),
      toast: document.querySelector("#aicg3d-toast .a3-toast-text")?.textContent || "",
    };
  });

  const screenshotPath = process.env.SCREENSHOT_PATH;
  if (screenshotPath) await page.screenshot({ path: screenshotPath, fullPage: true });
  console.log(JSON.stringify({ dialogs, result }, null, 2));
  await browser.close();

  const promptText = dialogs.join("\n");
  const passed = promptText.includes("视频段落 1")
    && promptText.includes("视频段落 3、4")
    && (acceptDialog
      ? result.nodeWarnings.length === 0 && result.missingCards === 0
      : result.nodeWarnings.length >= 2 && result.missingButtons.length >= 2);
  if (!passed) process.exitCode = 1;
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
