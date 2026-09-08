import { ApiProperty } from '@nestjs/swagger';
import type { FileDto as SharedFileDto } from '@minidrive/shared';

export class FileDto implements SharedFileDto {
  @ApiProperty() id!: string;
  @ApiProperty() name!: string;
  @ApiProperty() extension!: string;
  @ApiProperty() size!: number;
  @ApiProperty() createdAt!: string;
  @ApiProperty() updatedAt!: string;
  @ApiProperty() uploadedBy!: string;
  @ApiProperty() modifiedBy!: string;
}
