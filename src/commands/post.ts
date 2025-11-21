import { Telegraf, Context } from 'telegraf';

export const PostCommand = (bot: Telegraf<Context>) => {
  bot.command('post', async ctx => {
    await ctx.reply(
      'Send the text you want to refine.\n\n(Note: Stickers and GIFs are not allowed.)'
    );

    bot.once('message', async msgCtx => {
      const message = msgCtx.message; // <- properly typed Message object

      // ❌ Stickers
      if ('sticker' in message) {
        return msgCtx.reply(
          '❌ Stickers are not allowed. Please send a text message.'
        );
      }

      // ❌ GIFs (Telegram animations)
      if ('animation' in message) {
        return msgCtx.reply(
          '❌ GIFs are not allowed. Please send a text message.'
        );
      }

      // ❌ Documents (GIFs sometimes)
      if ('document' in message) {
        return msgCtx.reply(
          '❌ Documents/GIFs are not allowed. Please send a text message.'
        );
      }

      // ❌ Photos / videos / voice / video notes
      if (
        'photo' in message ||
        'video' in message ||
        'voice' in message ||
        'video_note' in message
      ) {
        return msgCtx.reply('❌ Only text is allowed. Please send text only.');
      }

      // ✅ Text
      if ('text' in message) {
        return msgCtx.reply(`You sent:\n\n${message.text}`);
      }

      // Anything else
      return msgCtx.reply('❌ Unsupported content. Please send text only.');
    });
  });
};
