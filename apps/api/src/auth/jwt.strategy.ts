import { Injectable, UnauthorizedException } from '@nestjs/common';
import { PassportStrategy } from '@nestjs/passport';
import { ExtractJwt, Strategy } from 'passport-jwt';
import { loadConfig } from '../config';
import { UsersService } from '../users/users.service';

export type JwtUser = { id: string; username: string };

@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
  constructor(private readonly users: UsersService) {
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      secretOrKey: loadConfig().jwtSecret,
    });
  }

  async validate(payload: { sub: string; username: string }): Promise<JwtUser> {
    const user = await this.users.findById(payload.sub);
    if (!user) throw new UnauthorizedException();
    return { id: user.id, username: user.username };
  }
}
