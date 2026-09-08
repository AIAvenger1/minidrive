import { ApiProperty } from '@nestjs/swagger';
import { IsString, Length, Matches } from 'class-validator';
import type {
  AuthResponseDto as SharedAuthResponseDto,
  UserDto as SharedUserDto,
} from '@minidrive/shared';

export class RegisterDto {
  @ApiProperty({ example: 'bohdan' })
  @IsString()
  @Length(3, 32)
  @Matches(/^[a-zA-Z0-9_.-]+$/)
  username!: string;

  @ApiProperty({ example: 'secret123' })
  @IsString()
  @Length(6, 72)
  password!: string;
}

export class LoginDto extends RegisterDto {}

export class UserDto implements SharedUserDto {
  @ApiProperty() id!: string;
  @ApiProperty() username!: string;
}

export class AuthResponseDto implements SharedAuthResponseDto {
  @ApiProperty() accessToken!: string;
  @ApiProperty({ type: UserDto }) user!: UserDto;
}
