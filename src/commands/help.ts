import { Telegraf, Context } from "telegraf";

export const helpCommand = (bot: Telegraf<Context>) => {
  bot.help((ctx) => {
    ctx.reply(
      "Hi there! I am Poster Boi — I help you prepare posts for your channels and attach a watermark.\n\n" +
        "How to use:\n" +
        "• /start - Welcome message and quick commands overview\n" +
        "• /help - This message\n" +
        "• /preference - Select how I should refine your posts (grammar, funny, professional)\n" +
        "• /post - Start composing a refined post; follow prompts\n" +
        "• /watermark - Register your channel and set the watermark text; you must forward a channel message or send the channel username (e.g. @mychannel), and add me as an admin with edit rights to the channel for watermarking to work\n\n" +
        "If you need help with the /post flow, send /post and follow the prompts. I use a model (Gemini) to refine posts according to your preferences, so set your preferences with /preference. I only edit channel messages when I have admin privileges and a watermark configured for that channel."
    );
  });
};
