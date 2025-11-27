import express, { Request, Response } from "express";
import dotenv from "dotenv";
dotenv.config();

import { Telegraf } from "telegraf";
import { prisma } from "./lib/prisma";
import { startCommand } from "./commands/start";
import { PostCommand } from "./commands/post";
import { PreferenceCommand } from "./commands/preference";
import { WatermarkCommand } from "./commands/watermark";
import { helpCommand } from "./commands/help";
import { SettingsCommand } from "./commands/settings";

const app = express();
const bot = new Telegraf(process.env.BOT_TOKEN!);

// Register commands
[startCommand, PostCommand, PreferenceCommand, WatermarkCommand, helpCommand, SettingsCommand].forEach(
  (command) => command(bot)
);

// Helper function to safely get text or caption
const getPostContent = (post: any) => {
  if (!post) return null;
  if ("text" in post && typeof post.text === "string") return { type: "text", content: post.text };
  if ("caption" in post && typeof post.caption === "string") return { type: "caption", content: post.caption };
  return null;
};

// Handle channel posts and append watermark
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

// Health check endpoint
app.get("/health", (_req: Request, res: Response) => {
  res.json({ message: "server is healthy" });
});

bot.launch();

app.listen(process.env.PORT, () => {
  console.log(`Server running on port ${process.env.PORT}`);
});
