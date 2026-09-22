import "dotenv/config";
import http from "node:http";
import { Telegraf, Context } from "telegraf";
import { prisma } from "./lib/prisma";
import { startCommand } from "./commands/start";
import { PostCommand } from "./commands/post";
import { PreferenceCommand } from "./commands/preference";
import { WatermarkCommand } from "./commands/watermark";
import { helpCommand } from "./commands/help";
import { SettingsCommand } from "./commands/settings";

const bot = new Telegraf<Context>(process.env.BOT_TOKEN!);

[startCommand, PostCommand, PreferenceCommand, WatermarkCommand, helpCommand, SettingsCommand].forEach((command) =>
  command(bot)
);

bot.on("channel_post", async (ctx) => {
  const post = ctx.channelPost;
  const chat = post?.chat;
  if (!chat || !post) return;

  const telegramId = chat.id.toString();
  const messageId = post.message_id;
  if (!messageId) return;

  try {
    const channel = await prisma.channel.findUnique({ where: { telegramId } });
    if (!channel) return;

    const watermark = await prisma.watermark.findFirst({
      where: { channelId: channel.id },
      orderBy: { id: "desc" },
    });
    if (!watermark) return;

    const postContent = getPostContent(post);
    if (!postContent) return;

    if (postContent.type === "text") {
      await bot.telegram.editMessageText(chat.id, messageId, undefined, `${postContent.content}\n\n${watermark.text}`, {
        parse_mode: "Markdown",
      });
    } else if (postContent.type === "caption") {
      await bot.telegram.editMessageCaption(chat.id, messageId, undefined, `${postContent.content}\n\n${watermark.text}`, {
        parse_mode: "Markdown",
      });
    }
  } catch (error) {
    console.error("Unable to append watermark to channel post:", error);
  }
});

const getPostContent = (post: any) => {
  if (!post) return null;
  if ("text" in post && typeof post.text === "string") return { type: "text", content: post.text };
  if ("caption" in post && typeof post.caption === "string") return { type: "caption", content: post.caption };
  return null;
};

const PORT = Number(process.env.PORT || 3000);
const WEBHOOK_PATH = process.env.WEBHOOK_PATH || "/webhook";

const webhookHandler = bot.webhookCallback(WEBHOOK_PATH);

const server = http.createServer((req, res) => {
  if (req.method === "GET" && (req.url === "/" || req.url === "/health")) {
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify({ message: "server is healthy" }));
    return;
  }
  webhookHandler(req, res);
});

server.listen(PORT, () => {
  console.log(`Watermark bot is listening on http://localhost:${PORT}${WEBHOOK_PATH}`);
});

const shutdown = (signal: string) => {
  console.log(`Received ${signal}, shutting down...`);
  server.close(() => {
    bot.stop(signal);
    process.exit(0);
  });
  setTimeout(() => process.exit(1), 10000).unref();
};

process.once("SIGINT", () => shutdown("SIGINT"));
process.once("SIGTERM", () => shutdown("SIGTERM"));