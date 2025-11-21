import express from 'express';
import dotenv from 'dotenv';
import { bot } from './bot/main';
import { startCommand } from './commands/start';
dotenv.config();

//constants
const app = express();
const port = process.env.PORT;

startCommand(bot);
bot.launch();

app.listen(port, () => {
  console.log(`🚀 Server ready at http://localhost:${port}`);
});
