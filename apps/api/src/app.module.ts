import { Controller, Get, Module } from '@nestjs/common';
import { AuthModule } from './auth/auth.module';
import { PrismaModule } from './prisma/prisma.module';
import { UsersModule } from './users/users.module';
import { StorageModule } from './storage/storage.module';
import { FilesModule } from './files/files.module';

@Controller('health')
class HealthController {
  @Get()
  health() {
    return { status: 'ok' };
  }
}

@Module({ imports: [PrismaModule, UsersModule, AuthModule, StorageModule, FilesModule], controllers: [HealthController] })
export class AppModule {}
