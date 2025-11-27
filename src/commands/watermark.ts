import { Telegraf, Context } from "telegraf";
import { prisma } from "../lib/prisma";

// We'll keep track of command states per user while they provide channel and watermark
const waitingForChannel: Record<string, boolean> = {};
const waitingForWatermarkText: Record<string, number> = {};

export const WatermarkCommand = (bot: Telegraf<Context>) => {
  bot.command("watermark", async (ctx) => {
    const userId = ctx.from?.id.toString();
    if (!userId) return;

    // Ask user to forward a message from their channel OR send the channel username (@mychannel)
    waitingForChannel[userId] = true;
    await ctx.reply(
      "Please forward any message from the channel you want me to watermark, or send the channel username (e.g. @mychannel).\n\n" +
        "Make sure you have added me to the channel and granted admin rights (edit messages) so I can add the watermark."
    );
  });

  // Handle text messages that could be channel usernames, and forwarded messages
  bot.on("message", async (ctx, next) => {
    const userId = ctx.from?.id?.toString();
    if (!userId) return;
    // Only allow this flow via private chats
    if (ctx.chat?.type !== "private") return next();

    // Skip processing if the user isn't in the watermark flow
    if (!waitingForChannel[userId] && !waitingForWatermarkText[userId])
      return next();

    // Prevent processing of messages that are bot commands
    const entities = ((ctx.message as any)?.entities ??
      (ctx.message as any)?.caption_entities) as any[] | undefined;
    const isCommand =
      Array.isArray(entities) && entities.some((e) => e.type === "bot_command");
    if (isCommand) return next();

    // If user is waiting for channel info
    if (waitingForChannel[userId]) {
      // If forwarded from a chat, use forwarded chat info
      const forwarded = (ctx.message as any)?.forward_from_chat as
        | any
        | undefined;
      let chatId: number | undefined;
      let chatTitle: string | undefined;

      if (forwarded) {
        chatId = forwarded.id;
        chatTitle = forwarded.title;
      } else if ((ctx.message as any)?.text) {
        const text = ((ctx.message as any).text as string).trim();
        // If user supplied @username or https://t.me/username
        if (text.startsWith("@")) {
          try {
            const chat = await bot.telegram.getChat(text);
            chatId = chat.id;
            chatTitle = (chat as any).title ?? text;
          } catch (e) {
            await ctx.reply(
              "Could not find that channel. Please make sure the username is correct and the bot can access it."
            );
            return;
          }
        } else if (text.startsWith("https://t.me/")) {
          const username = text.split("/").pop();
          if (username) {
            try {
              const chat = await bot.telegram.getChat("@" + username);
              chatId = chat.id;
              chatTitle = (chat as any).title ?? username;
            } catch (e) {
              await ctx.reply(
                "Could not find that channel. Please ensure the link is correct and I have access."
              );
              return;
            }
          }
        }
      }

      if (!chatId) {
        await ctx.reply(
          "Please forward a message from the channel or send the channel username starting with @"
        );
        return;
      }

      // Save or upsert the channel
      const telegramId = chatId.toString();
      let channel = await prisma.channel.findUnique({ where: { telegramId } });
      if (!channel) {
        channel = await prisma.channel.create({
          data: { telegramId, name: chatTitle },
        });
      }

      // Connect or update the user to link to this channel
      const user = await prisma.user.upsert({
        where: { telegramId: userId },
        create: {
          telegramId: userId,
          name: ctx.from?.first_name ?? "unknown",
          channelId: channel.id,
        },
        update: { channelId: channel.id },
      });

      // Ask for watermark text and move to next step
      waitingForWatermarkText[userId] = channel.id;
      waitingForChannel[userId] = false;

      await ctx.reply(
        "Nice! Now send the watermark text you want to attach to messages in that channel."
      );
      return;
    }

    // If user is in the watermark text step, create a watermark record
    if (waitingForWatermarkText[userId]) {
      const channelId = waitingForWatermarkText[userId];
      const watermarkText = ((ctx.message as any)?.text ??
        (ctx.message as any)?.caption ??
        "") as string;

      if (!watermarkText) {
        await ctx.reply("Please send some text to use as the watermark.");
        return;
      }

      await prisma.watermark.create({
        data: {
          text: watermarkText,
          channel: { connect: { id: channelId } },
        },
      });

      delete waitingForWatermarkText[userId];
      await ctx.reply(
        "✔️ Watermark saved. I will attempt to add it to future posts in that channel (if I have admin rights to edit messages)."
      );
    }
  });
};
