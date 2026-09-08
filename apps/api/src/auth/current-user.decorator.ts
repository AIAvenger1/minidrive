import { createParamDecorator, ExecutionContext } from '@nestjs/common';
import { JwtUser } from './jwt.strategy';

export const CurrentUser = createParamDecorator((_: unknown, ctx: ExecutionContext): JwtUser => {
  return ctx.switchToHttp().getRequest().user;
});
