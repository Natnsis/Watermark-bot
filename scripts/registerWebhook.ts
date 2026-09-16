import "dotenv/config";
import { Telegraf } from "telegraf";

const token = process.env.BOT_TOKEN;
const url = process.env.WEBHOOK_URL;

if (!token || !url) {
  console.error("BOT_TOKEN and WEBHOOK_URL must be set");
  process.exit(1);
}

const bot = new Telegraf(token);
await bot.telegram.setWebhook(url);
console.log("Webhook registered:", await bot.telegram.getWebhookInfo());