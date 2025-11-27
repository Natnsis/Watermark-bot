import express from "express";
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

startCommand(bot);
PostCommand(bot);
PreferenceCommand(bot);
WatermarkCommand(bot);
helpCommand(bot);
SettingsCommand(bot);

// Handle channel post – attempt to append watermark to channel messages
bot.on("channel_post", async (ctx) => {
  const channelChat = ctx.channelPost?.chat;
  if (!channelChat) return;
  const telegramId = channelChat.id.toString();
  const messageId = ctx.channelPost?.message_id;
  if (!messageId) return;

  try {
    const channel = await prisma.channel.findUnique({ where: { telegramId } });
    if (!channel) return; // nothing to do for this channel

    const watermark = await prisma.watermark.findFirst({
      where: { channelId: channel.id },
      orderBy: { id: "desc" },
    });
    if (!watermark) return;

    // If it's a text post, edit the text. If it's media with a caption, edit the caption.
    if (ctx.channelPost?.text) {
      const newText = `${ctx.channelPost.text}\n\n${watermark.text}`;
      await bot.telegram.editMessageText(
        channelChat.id,
        messageId,
        undefined,
        newText,
        { parse_mode: "Markdown" }
      );
    } else if (ctx.channelPost?.caption) {
      const newCaption = `${ctx.channelPost.caption}\n\n${watermark.text}`;
      await bot.telegram.editMessageCaption(
        channelChat.id,
        messageId,
        undefined,
        newCaption,
        { parse_mode: "Markdown" }
      );
    }
  } catch (e) {
    console.error("Unable to append watermark to channel post", e);
  }
});

bot.launch();

app.listen(process.env.PORT, () => {
  console.log(`server running on port ${process.env.PORT}`);
});
