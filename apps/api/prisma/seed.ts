import { PrismaClient } from '@prisma/client';
import * as bcrypt from 'bcrypt';

const prisma = new PrismaClient();

async function main() {
  const passwordHash = await bcrypt.hash('secret123', 10);
  for (const username of ['bohdan', 'olena', 'taras']) {
    await prisma.user.upsert({ where: { username }, update: {}, create: { username, passwordHash } });
  }
}

main().finally(() => prisma.$disconnect());
