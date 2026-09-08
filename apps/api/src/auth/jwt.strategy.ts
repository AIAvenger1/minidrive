import { Injectable } from '@nestjs/common';
import { PassportStrategy } from '@nestjs/passport';
import { ExtractJwt, Strategy } from 'passport-jwt';
import { loadConfig } from '../config';

export type JwtUser = { id: string; username: string };

@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
  constructor() {
    super({ jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(), secretOrKey: loadConfig().jwtSecret });
  }

  validate(payload: { sub: string; username: string }): JwtUser {
    return { id: payload.sub, username: payload.username };
  }
}
