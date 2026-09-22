-- CreateTable
CREATE TABLE "Channel" (
    "id" SERIAL NOT NULL,
    "telegramId" TEXT NOT NULL,
    "name" TEXT,

    CONSTRAINT "Channel_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "User" (
    "id" SERIAL NOT NULL,
    "telegramId" TEXT NOT NULL,
    "name" TEXT,
    "channelId" INTEGER,

    CONSTRAINT "User_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Watermark" (
    "id" SERIAL NOT NULL,
    "text" TEXT NOT NULL,
    "channelId" INTEGER NOT NULL,

    CONSTRAINT "Watermark_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Refinement" (
    "id" SERIAL NOT NULL,
    "userId" TEXT NOT NULL,
    "funnyRef" BOOLEAN NOT NULL,
    "grammarRef" BOOLEAN NOT NULL,
    "professional" BOOLEAN NOT NULL,

    CONSTRAINT "Refinement_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "Channel_telegramId_key" ON "Channel"("telegramId");

-- CreateIndex
CREATE UNIQUE INDEX "User_telegramId_key" ON "User"("telegramId");

-- CreateIndex
CREATE UNIQUE INDEX "Refinement_userId_key" ON "Refinement"("userId");

-- AddForeignKey
ALTER TABLE "User" ADD CONSTRAINT "User_channelId_fkey" FOREIGN KEY ("channelId") REFERENCES "Channel"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Watermark" ADD CONSTRAINT "Watermark_channelId_fkey" FOREIGN KEY ("channelId") REFERENCES "Channel"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Refinement" ADD CONSTRAINT "Refinement_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("telegramId") ON DELETE RESTRICT ON UPDATE CASCADE;