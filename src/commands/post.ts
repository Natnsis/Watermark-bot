import { Telegraf, Context, Markup } from "telegraf";
import { prisma } from "../lib/prisma";
import { refineText, GeminiResult } from "../lib/gemini";

const waitingForPost: Record<string, boolean> = {};

export const PostCommand = (bot: Telegraf<Context>) => {
  bot.command("post", async (ctx) => {
    const user = ctx.from;
    if (!user) return;

    const userId = user.id.toString();

    const userExists = await prisma.user.findUnique({
      where: { telegramId: userId },
    });
    if (!userExists) {
      await prisma.user.create({
        data: {
          telegramId: userId,
          name: user.first_name ?? "unknown",
        },
      });
    }

    const refinement = await prisma.refinement.findUnique({
      where: { userId },
    });

    const optionsText =
      `Your refinement options are:\n` +
      `• Funny: ${refinement?.funnyRef ?? false ? "✅ Yes" : "❌ No"}\n` +
      `• Grammar: ${refinement?.grammarRef ?? true ? "✅ Yes" : "❌ No"}\n` +
      `• Professional: ${
        refinement?.professional ?? false ? "✅ Yes" : "❌ No"
      }\n\n` +
      `Do you want to edit them or are they fine?`;

    await ctx.reply(
      optionsText,
      Markup.inlineKeyboard([
        [Markup.button.callback("✏️ Edit Preferences", "edit_pref_post")],
        [
          Markup.button.callback(
            "✅ Preferences are fine",
            "confirm_pref_post"
          ),
        ],
      ])
    );
  });

  bot.action("edit_pref_post", async (ctx) => {
    await ctx.answerCbQuery();
    await ctx.reply("/preference");
  });

  bot.action("confirm_pref_post", async (ctx) => {
    const userId = ctx.from.id.toString();
    waitingForPost[userId] = true;

    await ctx.answerCbQuery();
    await ctx.editMessageText("Great! Now send your message.");
  });

  bot.on("text", async (ctx, next) => {
    const userId = ctx.from?.id.toString();
    if (!userId) return next();
    if (ctx.chat?.type !== "private") return next(); // only handle private messages for post flow
    if (!waitingForPost[userId]) return next();
    // Ignore messages that are Telegram commands (so global command handlers keep working)
    const entities =
      (ctx.message as any)?.entities ?? (ctx.message as any)?.caption_entities;
    const isCommand =
      Array.isArray(entities) && entities.some((e) => e.type === "bot_command");
    if (isCommand) return next();

    const message =
      (ctx.message as any)?.text ?? (ctx.message as any)?.caption ?? "";

    // Show a loading indicator and keep the user informed while we call Gemini
    try {
      // Immediately show a typing indicator
      await ctx.sendChatAction("typing");
    } catch (e) {
      /* ignore */
    }

    // Create a placeholder message that we'll edit once the AI response arrives
    const placeholder = await ctx.reply(
      "⏳ Refining your text, please wait..."
    );

    // Load user's preferences and refine the message via Gemini
    const refinement = await prisma.refinement.findUnique({
      where: { userId },
    });
    let refined = message;
    try {
      // Keep sending typing action while waiting to avoid client timeouts (best effort)
      let keepTyping = true;
      const typingInterval = setInterval(() => {
        if (!keepTyping) return;
        try {
          // ignore promise result, just signal typing
          ctx.sendChatAction("typing");
        } catch (err) {
          // ignore
        }
      }, 2500);

      const result: GeminiResult = await refineText(message, {
        grammar: refinement?.grammarRef ?? true,
        funny: refinement?.funnyRef ?? false,
        professional: refinement?.professional ?? false,
      });

      // stop the typing action interval
      keepTyping = false;
      clearInterval(typingInterval);

      // handle fallback / errors explicitly
      if (result.fallback) {
        // If fallback and no credentials present, notify the user
        if (!process.env.GEMINI_API_KEY) {
          await ctx.reply(
            "⚠️ Gemini is not configured (GEMINI_API_KEY missing). The text was returned unchanged."
          );
        } else {
          // Non-config / network error; log and inform user
          await ctx.reply(
            `⚠️ Gemini returned an error (${result.error}${
              result.status ? ` - ${result.status}` : ``
            }). The text was returned unchanged.`
          );
        }
      }
      refined = result.text;
    } catch (e) {
      console.error("Failed to refine text with Gemini", e);
      refined = message; // fallback
    }

    // Edit the placeholder message to show the refined message
    try {
      await ctx.telegram.editMessageText(
        ctx.chat!.id,
        placeholder.message_id,
        undefined,
        `Refined message:\n\n${refined}`
      );
    } catch (e) {
      // If editing failed (e.g., message too old), reply instead
      await ctx.reply(`Refined message:\n\n${refined}`);
    }

    delete waitingForPost[userId];
  });
};
