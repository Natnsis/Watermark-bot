import express, { Request, Response } from 'express'
import { prisma } from './lib/prisma';
import dotenv from 'dotenv'
dotenv.config();


const app = express();

app.get('/', async (req: Request, res: Response) => {
  const data = await prisma.user.findMany()
  res.json(data)
})

app.listen(process.env.PORT, () => {
  console.log(`server running on port ${process.env.PORT}`)
})
