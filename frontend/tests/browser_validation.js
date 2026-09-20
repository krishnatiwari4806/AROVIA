// browser_validation.js
// Playwright script to launch installed Chrome/Edge, navigate to AROVIA system design staged UI, and capture screenshot/report.

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const possiblePaths = [
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
  ];
  let execPath = null;
  for (const p of possiblePaths) {
    if (fs.existsSync(p)) { execPath = p; break; }
  }
  if (!execPath) {
    console.error('Chrome/Edge executable not found.');
    process.exit(1);
  }

  const browser = await chromium.launch({ headless: false, executablePath: execPath });
  const context = await browser.newContext();
  const page = await context.newPage();

  page.on('console', msg => console.log('PAGE LOG:', msg.text()));

  const url = 'http://localhost:5173/?practice_mode=system_design_staged';
  try {
    await page.goto(url, { waitUntil: 'networkidle' });
    console.log('Navigated to', url);
  } catch (e) {
    console.error('Navigation failed', e);
    await browser.close();
    process.exit(1);
  }

  const stepperSel = '[data-testid="stage-stepper"]';
  let stepperFound = false;
  try {
    await page.waitForSelector(stepperSel, { timeout: 10000 });
    stepperFound = true;
    console.log('Stage stepper present');
  } catch {
    console.warn('Stage stepper not found');
  }

  const screenshotPath = path.resolve(__dirname, 'browser_validation_screenshot.png');
  await page.screenshot({ path: screenshotPath, fullPage: true });
  console.log('Screenshot saved to', screenshotPath);

  let stages = [];
  try {
    const els = await page.$$('[data-testid^="stage-"]');
    for (const el of els) {
      const txt = await el.innerText();
      stages.push(txt.trim());
    }
    console.log('Stages detected', stages);
  } catch (e) {
    console.warn('Error extracting stages', e);
  }

  const report = {
    execPath,
    url,
    stepperFound,
    stages,
    screenshot: screenshotPath,
    timestamp: new Date().toISOString()
  };
  const reportPath = path.resolve(__dirname, 'browser_validation_report.json');
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
  console.log('Report written to', reportPath);

  await browser.close();
})();
