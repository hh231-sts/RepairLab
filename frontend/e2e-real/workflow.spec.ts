import { test, expect } from "@playwright/test";

test("界面新建工单、复用验收、选择真实模型入口并降低预算（模型HTTP为替身）", async ({
  page,
  request,
}) => {
  const name = `UI 新工单 ${Date.now()}`;
  await page.goto("/");
  await expect(page.getByText("真实模型模式已启用")).toBeVisible();
  const importing = page.waitForResponse(
    (r) => r.url().endsWith("/api/demo") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "导入本地开发夹具" }).click();
  const demo = await (await importing).json();
  await page.getByRole("button", { name: "新建工单", exact: true }).click();
  await page.getByLabel("项目", { exact: true }).selectOption(demo.project.id);
  await page
    .getByLabel("执行环境与验收模板（同项目）")
    .selectOption(demo.issue.id);
  await page.getByLabel("工单标题").fill(name);
  await page
    .getByLabel("问题描述与验收条件")
    .fill(
      "clamp 在 low > high 时应抛出 ValueError，请复现并修复，保留公开测试和独立验收结果。",
    );
  await page.getByRole("button", { name: "保存并继续" }).click();
  await page
    .locator(".issue-row")
    .filter({ has: page.getByRole("heading", { name }) })
    .getByRole("button", { name: "发起运行" })
    .click();
  await expect(page.getByLabel("模型来源")).toHaveValue("deepseek");
  await expect(page.getByLabel("开发脚本")).toHaveCount(0);
  await page.getByLabel("费用上限（元）").fill("0.25");
  await page.getByLabel("最多模型调用次数").fill("12");
  await page.getByLabel("执行期限（秒）").fill("300");
  const submitting = page.waitForResponse(
    (r) => r.url().endsWith("/api/runs") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "发起真实模型运行" }).click();
  const run = await (await submitting).json();
  expect(run.model_source).toBe("deepseek");
  expect(run.versions.limits).toEqual({
    max_cost_cny: 0.25,
    max_calls: 12,
    max_seconds: 300,
  });
  await expect(page.locator(".run-summary .status")).toHaveText("已通过", {
    timeout: 90000,
  });
  const detail = await (
    await request.get(`http://127.0.0.1:18081/api/runs/${run.id}`, {
      headers: { Authorization: "Bearer local-dev-change-me" },
    })
  ).json();
  expect(detail.verifications[0].passed).toBe(true);
  expect(detail.reserved).toBe(0);
  expect(
    detail.model_calls.every(
      (call: { status: string }) => call.status === "settled",
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "工具与证据" }).click();
  await expect(
    page.getByRole("heading", { name: "模型调用与计费" }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results-real/workflow.png",
    fullPage: false,
  });
});
