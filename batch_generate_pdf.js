const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const cliProgress = require('cli-progress');

chromium.use(StealthPlugin());  // Bật stealth plugin

function readJobs(inputPath) {
  return fs.readFileSync(inputPath, 'utf-8')
    .split('\n').filter(Boolean)
    .map((line, i) => {
      const [, url] = line.split('|||');
      return { index: String(i + 1).padStart(6, '0'), url: url.trim() };
    });
}

async function convertList(jobs, outputDir, errLog, browser, bar, skip = true) {
  for (const job of jobs) {
    const outFile = path.join(outputDir, `${job.index}.pdf`);
    if (skip && fs.existsSync(outFile)) {
      bar.increment({ title: '⏭️ Skip' });
      continue;
    }
    const context = await browser.newContext({
      userAgent:
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ' +
        'AppleWebKit/537.36 (KHTML, like Gecko) ' +
        'Chrome/116.0.0.0 Safari/537.36',
      viewport: { width: 1280, height: 800 },
      locale: 'vi-VN',
      timezoneId: 'Asia/Ho_Chi_Minh',
      bypassCSP: true
    });
    const page = await context.newPage();

    try {
      bar.increment({ title: job.index });
      await page.goto(job.url, {
        waitUntil: 'domcontentloaded',
        timeout: 90000
      });
      await page.waitForSelector('body', { timeout: 15000 });
      await page.waitForTimeout(5000);

      await page.pdf({
        path: outFile,
        format: 'A4',
        printBackground: true
      });
      console.log(`✅ Created: ${outFile}`);
    } catch (e) {
      fs.appendFileSync(
        errLog,
        `❌ ${job.index}|||${job.url}\n→ ${e.message}\n`
      );
      console.error(`❌ ${job.index} error:`, e.message);
    } finally {
      if (!page.isClosed()) await page.close();
      await context.close();
    }
  }
}

(async () => {
  const input = 'urls.txt';
  const outputDir = 'output';
  const errLog = 'error.log';

  if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, {
    recursive: true,
    mode: 0o777
  });
  fs.writeFileSync(errLog, '');

  const jobs = readJobs(input);
  const browser = await chromium.launch({ headless: true });
  const bar = new cliProgress.SingleBar({
    format: '📄 {bar} {percentage}% | {value}/{total} | {title}',
    barCompleteChar: '█',
    barIncompleteChar: '░',
    hideCursor: true
  });

  bar.start(jobs.length, 0, { title: '' });
  await convertList(jobs, outputDir, errLog, browser, bar, true);
  bar.stop();

  if (fs.existsSync(errLog)) {
    const errs = fs.readFileSync(errLog, 'utf-8')
      .split('\n').filter(l => l.includes('|||'))
      .map(l => {
        const [idx, url] = l.split('|||');
        return { index: idx.slice(2), url };
      });
    if (errs.length) {
      console.log(`🔁 Retrying ${errs.length} failed URLs...`);
      fs.writeFileSync(errLog, '');
      bar.start(errs.length, 0, { title: 'Retrying...' });
      await convertList(errs, outputDir, errLog, browser, bar, false);
      bar.stop();
    }
  }

  await browser.close();
  console.log('🎉 ALL DONE ✅');
})();
