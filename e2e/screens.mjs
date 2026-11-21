// Catture delle pagine autenticate (desktop e mobile), dopo login con passkey virtuale.
import { chromium } from "playwright-core"

const EMAIL = process.argv[2] ?? "dev-admin@example.com"
const OUT = new URL("./out/", import.meta.url).pathname
// Chromium di Playwright già scaricato; sovrascrivibile con ARGO_E2E_CHROME.
const CHROME =
  process.env.ARGO_E2E_CHROME ??
  `${process.env.HOME}/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome`

async function latestLink() {
  const search = await (await fetch(`http://127.0.0.1:8025/api/v1/search?query=to:${EMAIL}`)).json()
  const id = search.messages[0].ID
  const msg = await (await fetch(`http://127.0.0.1:8025/api/v1/message/${id}`)).json()
  return msg.Text.match(/https?:\/\/\S+action-token\S+/)[0]
}

const browser = await chromium.launch({ executablePath: CHROME, chromiumSandbox: false })
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
const page = await context.newPage()
page.on("dialog", (d) => d.accept(`Dispositivo di prova ${Date.now()}`))
const cdp = await context.newCDPSession(page)
await cdp.send("WebAuthn.enable")
await cdp.send("WebAuthn.addVirtualAuthenticator", {
  options: {
    protocol: "ctap2",
    transport: "internal",
    hasResidentKey: true,
    hasUserVerification: true,
    isUserVerified: true,
    automaticPresenceSimulation: true,
  },
})

const step = async (name) => {
  await page.screenshot({ path: `${OUT}${name}.png` })
  console.log(`${name}: ${page.url().slice(0, 90)}`)
}

try {
  await page.goto(await latestLink())
  await step("1-link")
  const proceed = page.locator("a:has-text('qui'), a:has-text('click here'), a#kc-info-message a")
  if (await proceed.count()) await proceed.first().click()
  await page.waitForLoadState("networkidle")
  await step("2-registra")
  await page.locator("#registerWebAuthn, input[type=submit], button[type=submit]").first().click()
  await page.waitForLoadState("networkidle")
  await step("3-dopo-registrazione")

  await page.goto("http://localhost:5173/api/auth/login?next=/")
  await page.fill("input[name=username]", EMAIL)
  await page.locator("input[type=submit], button[type=submit]").first().click()
  await page.waitForLoadState("networkidle")
  await step("4-passkey")
  const passkeyButton = page.locator("#authenticateWebAuthnButton")
  if (await passkeyButton.count()) await passkeyButton.click()
  await page.waitForURL(/localhost:5173\//, { timeout: 15000 })
  await step("5-dashboard")
  for (const [name, path] of [
    ["panoramica", "/"],
    ["dipendenti", "/dipendenti"],
    ["sincronizzazione", "/sincronizzazione"],
    ["operazioni", "/operazioni"],
    ["applicazioni", "/applicazioni"],
    ["registro", "/registro"],
  ]) {
    for (const [width, height] of [
      [1440, 900],
      [390, 844],
    ]) {
      await page.setViewportSize({ width, height })
      await page.goto(`http://localhost:5173${path}`)
      await page.waitForLoadState("networkidle")
      await page.screenshot({ path: `${OUT}${name}-${width}.png`, fullPage: true })
    }
  }
  console.log("catture salvate in", OUT)
} catch (err) {
  await step("errore")
  console.log("ERRORE", err.message.split("\n")[0])
  console.log((await page.content()).replace(/\s+/g, " ").match(/<body.*/)?.[0].slice(0, 1500))
} finally {
  await browser.close()
}
