import { expect, type Page, test } from "@playwright/test";

const username = process.env.E2E_ADMIN_USERNAME ?? "admin";
const password = process.env.E2E_ADMIN_PASSWORD ?? "choose-a-local-demo-password";

async function signIn(page: Page) {
  await page.goto("/login");
  await expect(page).toHaveTitle("Insidi_OS");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Insidi_OS Overview" })).toBeVisible();
}

test("protects the console and authenticates an analyst", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
  if (process.env.LOGIN_SCREENSHOT) await page.screenshot({ path: process.env.LOGIN_SCREENSHOT, fullPage: true, animations: "disabled" });
  await signIn(page);
  await expect(page.getByText("Events (24h)")).toBeVisible();
});

test("runs the deterministic demo and opens its investigation", async ({ page }) => {
  await signIn(page);
  await page.getByRole("link", { name: "Live Showcase", exact: true }).click();
  await page.getByText("Instant investigation generator", { exact: true }).click();
  await page.getByRole("button", { name: "Run safe scenario" }).click();

  await expect(page).toHaveURL(/\/investigations\//, { timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Attack investigation" })).toBeVisible();
  await expect(page.getByText("198.51.100.42").first()).toBeVisible();
  await expect(page.getByText(/T1059/).first()).toBeVisible();
});

for (const scenario of [
  { button: "Run employee data misuse", account: "demo-employee-001", evidence: "Sensitive data was transferred to an unapproved external destination." },
  { button: "Run privileged administrator misuse", account: "demo-admin-001", evidence: "Audit logging was disabled without an approved change." },
]) {
  test(`investigates ${scenario.account} activity`, async ({ page }) => {
    await signIn(page);
    await page.getByRole("link", { name: "Live Showcase", exact: true }).click();
    await page.getByText("Instant investigation generator", { exact: true }).click();
    await page.getByRole("button", { name: scenario.button, exact: true }).click();
    await expect(page).toHaveURL(/\/investigations\//, { timeout: 15_000 });
    await expect(page.getByText(scenario.account, { exact: false }).first()).toBeVisible();
    await expect(page.getByText(scenario.evidence, { exact: true })).toBeVisible();
    await expect(page.getByText("Score 0").first()).toBeVisible();
    await page.getByRole("link", { name: "Events", exact: true }).click();
    await page.getByRole("textbox", { name: "Filter by account ID" }).fill(scenario.account);
    await expect(page.getByText(scenario.evidence, { exact: true }).first()).toBeVisible();
  });
}

test("shows timed attacks, real alerts and sandbox containment", async ({ page }) => {
  await signIn(page);
  await page.getByRole("link", { name: "Live Showcase", exact: true }).click();
  await page.getByLabel("Demo pace").selectOption("2");
  await page.getByRole("button", { name: "Start live demo", exact: true }).click();
  const attacks = page.getByRole("log", { name: "Attacker activity" });
  const detection = page.getByRole("log", { name: "Detection engine" });
  const responses = page.getByRole("log", { name: "System response" });
  await expect(attacks.getByText("Valid account signs in", { exact: true })).toBeVisible();
  await expect(detection.getByText("No alert required", { exact: true }).first()).toBeVisible();
  await page.getByRole("button", { name: "Pause", exact: true }).click();
  await expect(page.getByText("PAUSED · ready to explain")).toBeVisible();
  const pausedStep = await page.getByText(/Step \d+ of 6/).innerText();
  await page.waitForTimeout(2500);
  await expect(page.getByText(pausedStep, { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Resume", exact: true }).click();
  await expect(responses.getByText("Transfer blocked in sandbox", { exact: true })).toBeVisible({ timeout: 20_000 });
  await expect(responses.getByText("Denied by existing containment", { exact: true })).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText("COMPLETE · evidence retained")).toBeVisible({ timeout: 10_000 });
  if (process.env.SHOWCASE_SCREENSHOT) await page.screenshot({ path: process.env.SHOWCASE_SCREENSHOT, fullPage: true, animations: "disabled" });
  const session = await page.locator("span").filter({ hasText: /^live-/ }).innerText();
  await page.reload();
  await expect(page.getByText(session, { exact: true })).toBeVisible();
  await expect(page.getByText("Account: contained", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Presenter view" }).click();
  await expect(page.locator("aside")).toBeHidden();
  await page.getByRole("button", { name: "Exit presenter view" }).click();
  await expect(page.locator("aside")).toBeVisible();
});

test("supports pause, manual steps and a fresh replay", async ({ page }) => {
  await signIn(page);
  await page.getByRole("link", { name: "Live Showcase", exact: true }).click();
  await page.getByRole("button", { name: "Administrator abuse" }).click();
  await page.getByRole("button", { name: "Start in step mode" }).click();
  await expect(page.getByText("PAUSED · ready to explain")).toBeVisible();
  await page.getByRole("button", { name: "Next step", exact: true }).click();
  await expect(page.getByRole("log", { name: "Attacker activity" }).getByText("Administrator signs in", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Next step", exact: true }).click();
  await expect(page.getByRole("log", { name: "Attacker activity" }).getByText("Approved privilege maintenance", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Next step", exact: true }).click();
  await expect(page.getByRole("log", { name: "System response" }).getByText("Audit logging restored in sandbox", { exact: true })).toBeVisible();
  const cursor = await page.getByText(/Step \d+ of 7/).innerText();
  await page.waitForTimeout(2500);
  await expect(page.getByText(cursor, { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Stop", exact: true }).click();
  await page.getByRole("button", { name: "Start in step mode" }).click();
  await expect(page.getByText("Step 0 of 7", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Stop", exact: true }).click();
});

test("distinguishes current decoy connections, totals and unavailable tracking", async ({ page }) => {
  await signIn(page);
  let active: number | null = 1;
  await page.route("**/api/v1/honeypots?**", (route) => route.fulfill({ json: {
    total: 1, items: [{
      id: "connection-test", name: "Connection tracking test", honeypot_type: "ssh", status: "running",
      container_id: "test", ip_address: "172.28.0.2", ports: "127.0.0.1:32768->22/tcp",
      total_connections: 3, total_commands: 0, unique_attackers: 2,
      active_connections: active, connection_tracking: active === null ? "unavailable" : "live",
      created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    }],
  } }));
  await page.getByRole("link", { name: "Local Decoys", exact: true }).click();
  const card = page.getByRole("article", { name: "Connection tracking test", exact: true });
  await expect(card.getByText("Connected · live TCP connections", { exact: true })).toBeVisible();
  await expect(card.getByText("Total connections observed", { exact: true }).locator("..")).toHaveText("Total connections observed3");
  active = 0;
  await expect(card.getByText("No active TCP connections", { exact: true })).toBeVisible({ timeout: 8_000 });
  active = null;
  await expect(card.getByText("Docker connection tracking is unavailable", { exact: true })).toBeVisible({ timeout: 8_000 });
  await expect(card.getByText("Unavailable", { exact: true })).toBeVisible();
});
