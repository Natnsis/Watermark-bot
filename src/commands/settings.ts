import { Telegraf, Context } from "telegraf";
import { refineText } from "../lib/gemini";

const API_KEY = process.env.GEMINI_API_KEY;
const BEARER_TOKEN =
  process.env.GEMINI_BEARER_TOKEN || process.env.GOOGLE_ACCESS_TOKEN;
const MODEL = process.env.GEMINI_MODEL || "text-bison-001";

export const SettingsCommand = (bot: Telegraf<Context>) => {
  bot.command("settings", async (ctx) => {
    const userId = ctx.from?.id?.toString();
    if (!userId) return;

    await ctx.reply(
      `Checking Gemini configuration...\nModel: ${MODEL}\nAuth: ${
        BEARER_TOKEN ? "Bearer token" : API_KEY ? "API key" : "None"
      }`
    );

    const testText =
      "This is a short test to validate the Gemini API key and model connectivity.";

    try {
      const result = await refineText(testText, { grammar: true });
      if (result.fallback) {
        if (result.status === 404) {
          await ctx.reply(
            `❌ Gemini model not found (404). Double-check the model name in GEMINI_MODEL and ensure the model is available to your project.`
          );
          return;
        }
        if (!API_KEY && !BEARER_TOKEN) {
          await ctx.reply(
            "⚠️ No Gemini API key or token was found. Please set `GEMINI_API_KEY` or `GEMINI_BEARER_TOKEN` in your environment and retry."
          );
          return;
        }
        await ctx.reply(
          `❌ Gemini test failed (${result.error}${
            result.status ? ` - ${result.status}` : ""
          }). Check the logs for details.`
        );
        return;
      }
      await ctx.reply(
        `✅ Gemini test succeeded. Sample output:\n\n${result.text}`
      );
    } catch (e) {
      console.error("Gemini settings test failed:", e);
      await ctx.reply(
        "❌ Gemini test failed. Check the bot logs for details and make sure GEMINI_API_KEY and GEMINI_MODEL are set correctly."
      );
    }
  });
};
