import { ConflictException, Injectable, UnauthorizedException } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { User } from '@prisma/client';
import { UsersService } from '../users/users.service';
import { AuthResponseDto, LoginDto, RegisterDto } from './dto';

@Injectable()
export class AuthService {
  constructor(private readonly users: UsersService, private readonly jwt: JwtService) {}

  async register(dto: RegisterDto): Promise<AuthResponseDto> {
    if (await this.users.findByUsername(dto.username)) {
      throw new ConflictException('Username is already taken');
    }
    const user = await this.users.create(dto.username, dto.password);
    return this.issue(user);
  }

  async login(dto: LoginDto): Promise<AuthResponseDto> {
    const user = await this.validateUser(dto.username, dto.password);
    return this.issue(user);
  }

  async validateUser(username: string, password: string): Promise<User> {
    const user = await this.users.findByUsername(username);
    if (!user || !(await this.users.verify(password, user.passwordHash))) {
      throw new UnauthorizedException('Invalid username or password');
    }
    return user;
  }

  private issue(user: User): AuthResponseDto {
    return {
      accessToken: this.jwt.sign({ sub: user.id, username: user.username }),
      user: { id: user.id, username: user.username },
    };
  }
}
