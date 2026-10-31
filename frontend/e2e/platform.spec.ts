import { test, expect } from "@playwright/test";

test("真实后端：开发工单、多 Agent、独立验收、轨迹和导出", async ({
  page,
  request,
  context,
}) => {
  const external: string[] = [];
  page.on("request", (r) => {
    if (!new URL(r.url()).hostname.match(/^(127\.0\.0\.1|localhost)$/))
      external.push(r.url());
  });
  await page.goto("/");
  await page.screenshot({ path: "test-results/overview.png", fullPage: false });
  await expect(
    page.getByRole("heading", { name: "研发工单工作台" }),
  ).toBeVisible();
  await expect(page.getByText("真实模型调用已关闭")).toBeVisible();
  await page.getByRole("button", { name: "导入本地开发夹具" }).click();
  await expect(
    page.getByRole("heading", { name: "clamp 未校验倒置边界" }).first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "发起运行" }).first().click();
  await page.getByLabel("执行策略").selectOption("adaptive");
  await page.getByRole("button", { name: "保存并继续" }).click();
  await expect(page.getByRole("heading", { name: "运行详情" })).toBeVisible();
  await expect(page.locator(".timeline")).toContainText("run.started");
  await expect(page.locator(".timeline summary").first()).toContainText(
    "执行数据",
  );
  await context.setOffline(true);
  await page.waitForTimeout(600);
  await context.setOffline(false);
  await expect(page.locator(".run-summary .status")).toHaveText("已通过", {
    timeout: 90000,
  });
  await expect(page.locator(".run-summary")).toContainText("脚本化测试");
  await page.getByRole("button", { name: "Agent 关系图" }).click();
  await expect(page.locator(".agent-card")).toHaveCount(4);
  await expect(page.locator(".agent-card.child .status")).toHaveText([
    "已验收",
    "已验收",
    "已验收",
  ]);
  await page.getByRole("button", { name: "补丁与验收" }).click();
  await expect(page.locator(".diff")).toContainText("raise ValueError");
  await expect(page.locator(".verification")).toContainText("tests_passed");
  const downloaded = page.waitForEvent("download");
  await page.getByRole("button", { name: "导出", exact: true }).click();
  const file = await downloaded;
  expect(file.suggestedFilename()).toMatch(/^run-.*\.json$/);
  await page.getByRole("button", { name: "执行时间线" }).click();
  await expect(page.locator(".timeline")).toContainText("verification.result");
  const health = await request.get("http://127.0.0.1:18080/health");
  expect((await health.json()).model_calls_enabled).toBe(false);
  expect(external).toEqual([]);
  await page.screenshot({ path: "test-results/workspace.png", fullPage: true });
});

test("知识版本、候选经验与工程实验配置使用真实接口", async ({ page }) => {
  const experimentName = `E2E 工程对照 ${Date.now()}`;
  await page.goto("/");
  await page
    .getByRole("button", { name: "知识与 Skills", exact: true })
    .click();
  await expect(page.locator(".skill-card")).toHaveCount(4);
  const previousVersion = Number(
    (
      await page
        .locator(".skill-card")
        .filter({ hasText: "analyze" })
        .locator("code")
        .innerText()
    ).slice(1),
  );
  await page.getByRole("button", { name: "创建新版本" }).click();
  await page
    .getByLabel("可复用步骤与完成条件")
    .fill(
      "Locate the failing code path, cite the source and public observations, and preserve all evidence before requesting independent verification.",
    );
  await page.getByRole("button", { name: "保存并继续" }).click();
  await expect(
    page.locator(".skill-card").filter({ hasText: "analyze" }),
  ).toContainText(`v${previousVersion + 1}`);
  await page.getByRole("button", { name: "实验比较", exact: true }).click();
  await page.getByRole("button", { name: "配置实验" }).click();
  await page.getByLabel("实验名称").fill(experimentName);
  await page.getByRole("button", { name: "保存并继续" }).click();
  await expect(
    page.getByRole("heading", { name: experimentName }),
  ).toBeVisible();
  await page
    .locator(".card-grid .panel")
    .filter({ has: page.getByRole("heading", { name: experimentName }) })
    .getByRole("button", { name: "比较结果" })
    .click();
  await expect(page.getByRole("heading", { name: "逐策略结果" })).toBeVisible();
  await page.getByRole("button", { name: "项目与仓库", exact: true }).click();
  await page.getByRole("button", { name: "添加版本化文档" }).first().click();
  await page.getByLabel("文档路径").fill("docs/e2e-contract.md");
  await page.getByLabel("文档版本").fill(`test-${Date.now()}`);
  await page
    .getByLabel("公开文档内容")
    .fill("A public clamp API contract: inverted bounds raise ValueError.");
  await page.getByRole("button", { name: "保存并继续" }).click();
  await page.getByLabel("检索内容").fill("clamp");
  await page.getByRole("button", { name: "检索", exact: true }).click();
  await expect(page.locator(".search-panel pre")).toContainText(
    "src/calculator.py",
  );
  await page.screenshot({ path: "test-results/projects.png", fullPage: true });
});

test("运行暂停、恢复以及错误补丁明确失败", async ({ page, request }) => {
  const headers = { Authorization: "Bearer local-dev-change-me" };
  const demo = await (
    await request.post("http://127.0.0.1:18080/api/demo", { headers })
  ).json();
  const run = await (
    await request.post("http://127.0.0.1:18080/api/runs", {
      headers,
      data: { issue_id: demo.issue.id, strategy: "single", script: "wrong" },
    })
  ).json();
  await request.post(
    `http://127.0.0.1:18080/api/runs/${run.id}/control/pause`,
    {
      headers,
    },
  );
  await page.goto("/");
  await page.getByRole("button", { name: "运行与交付", exact: true }).click();
  await page.getByText(run.id.slice(0, 8), { exact: true }).click();
  await expect(page.locator(".run-summary .status")).toHaveText("已暂停", {
    timeout: 15000,
  });
  await page.getByRole("button", { name: "继续", exact: true }).click();
  await expect(page.locator(".run-summary .status")).toHaveText("未通过", {
    timeout: 90000,
  });
  await expect(page.locator(".reason")).toContainText("tests_failed");
  await expect(page.getByRole("button", { name: "新建重试" })).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: "test-results/mobile.png", fullPage: true });
});
