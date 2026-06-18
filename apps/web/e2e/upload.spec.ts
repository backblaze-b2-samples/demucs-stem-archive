import { test, expect } from "@playwright/test";

test.describe("Stem archive flows", () => {
  test("should display the add-track page", async ({ page }) => {
    await page.goto("/upload");
    await expect(page).toHaveURL(/upload/);
  });

  test("should display the stem library", async ({ page }) => {
    await page.goto("/library");
    await expect(page).toHaveURL(/library/);
    await expect(page.getByRole("heading", { name: "Stem Library" })).toBeVisible();
  });

  test("should navigate to files page", async ({ page }) => {
    await page.goto("/files");
    await expect(page).toHaveURL(/files/);
  });

  test("should display the dashboard", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("body")).toBeVisible();
  });
});
