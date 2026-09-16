import { Telegraf, Context } from "telegraf";
import { prisma } from "./lib/prisma";
import { startCommand } from "./commands/start";
import { PostCommand } from "./commands/post";
import { PreferenceCommand } from "./commands/preference";
import { WatermarkCommand } from "./commands/watermark";
import { helpCommand } from "./commands/help";
import { SettingsCommand } from "./commands/settings";

let bot: Telegraf<Context> | undefined;

const getBot = () => {
  if (!bot) {
    bot = new Telegraf<Context>(process.env.BOT_TOKEN!);
    [startCommand, PostCommand, PreferenceCommand, WatermarkCommand, helpCommand, SettingsCommand].forEach(
      (command) => command(bot!)
    );
    bot!.on("channel_post", async (ctx) => {
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
          await bot!.telegram.editMessageText(chat.id, messageId, undefined, `${postContent.content}\n\n${watermark.text}`, {
            parse_mode: "Markdown",
          });
        } else if (postContent.type === "caption") {
          await bot!.telegram.editMessageCaption(chat.id, messageId, undefined, `${postContent.content}\n\n${watermark.text}`, {
            parse_mode: "Markdown",
          });
        }
      } catch (error) {
        console.error("Unable to append watermark to channel post:", error);
      }
    });
  }
  return bot;
};

const getPostContent = (post: any) => {
  if (!post) return null;
  if ("text" in post && typeof post.text === "string") return { type: "text", content: post.text };
  if ("caption" in post && typeof post.caption === "string") return { type: "caption", content: post.caption };
  return null;
};

export default {
  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/health") {
      return new Response(JSON.stringify({ message: "server is healthy" }), {
        headers: { "content-type": "application/json" },
      });
    }

    if (request.method === "POST") {
      const update = await request.json();
      await getBot().handleUpdate(update);
      return new Response("ok", { status: 200 });
    }

    return new Response("Not found", { status: 404 });
  },
};