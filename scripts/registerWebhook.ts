import "dotenv/config";
import { Telegraf } from "telegraf";

const token = process.env.BOT_TOKEN;
const url = process.env.WEBHOOK_URL;
const ipAddress = process.env.WEBHOOK_IP_ADDRESS;

if (!token || !url) {
  console.error("BOT_TOKEN and WEBHOOK_URL must be set");
  process.exit(1);
}

const bot = new Telegraf(token);
await bot.telegram.setWebhook(url, { ip_address: ipAddress || undefined });
console.log("Webhook registered:", await bot.telegram.getWebhookInfo());