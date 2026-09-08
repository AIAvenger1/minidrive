import { Module } from '@nestjs/common';
import { StorageService } from './storage.service';

@Module({
  providers: [{ provide: StorageService, useFactory: () => StorageService.fromEnv() }],
  exports: [StorageService],
})
export class StorageModule {}
