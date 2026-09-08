import { ApiProperty } from '@nestjs/swagger';

export class FileDto {
  @ApiProperty() id!: string;
  @ApiProperty() name!: string;
  @ApiProperty() extension!: string;
  @ApiProperty() size!: number;
  @ApiProperty() createdAt!: string;
  @ApiProperty() updatedAt!: string;
  @ApiProperty() uploadedBy!: string;
  @ApiProperty() modifiedBy!: string;
}
