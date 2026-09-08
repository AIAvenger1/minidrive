import {
  Controller, Delete, Get, HttpCode, Param, Post, Res, StreamableFile, UploadedFile, UseGuards, UseInterceptors,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { ApiBearerAuth, ApiBody, ApiConsumes, ApiTags } from '@nestjs/swagger';
import type { Response } from 'express';
import { CurrentUser } from '../auth/current-user.decorator';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import type { JwtUser } from '../auth/jwt.strategy';
import { loadConfig } from '../config';
import { FileDto } from './file.dto';
import { FilesService } from './files.service';

@ApiTags('files')
@ApiBearerAuth()
@UseGuards(JwtAuthGuard)
@Controller('files')
export class FilesController {
  constructor(private readonly files: FilesService) {}

  @Get()
  list(@CurrentUser() user: JwtUser): Promise<FileDto[]> {
    return this.files.listFor(user.id);
  }

  @Post()
  @ApiConsumes('multipart/form-data')
  @ApiBody({ schema: { type: 'object', properties: { file: { type: 'string', format: 'binary' } } } })
  @UseInterceptors(FileInterceptor('file', { limits: { fileSize: loadConfig().maxFileBytes } }))
  upload(@CurrentUser() user: JwtUser, @UploadedFile() file: Express.Multer.File): Promise<FileDto> {
    return this.files.upsert(user, file);
  }

  @Get(':id/content')
  async download(@CurrentUser() user: JwtUser, @Param('id') id: string, @Res({ passthrough: true }) res: Response): Promise<StreamableFile> {
    const content = await this.files.getContent(user.id, id);
    res.set({
      'Content-Type': content.mimeType,
      'Content-Disposition': `attachment; filename*=UTF-8''${encodeURIComponent(content.name)}`,
    });
    if (content.size) res.set('Content-Length', String(content.size));
    return new StreamableFile(content.stream);
  }

  @Delete(':id')
  @HttpCode(204)
  remove(@CurrentUser() user: JwtUser, @Param('id') id: string): Promise<void> {
    return this.files.delete(user.id, id);
  }
}
