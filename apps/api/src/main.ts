import 'dotenv/config';
import { ValidationPipe } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import { AppModule } from './app.module';
import { loadConfig } from './config';

async function bootstrap() {
  const config = loadConfig();
  const app = await NestFactory.create(AppModule);
  app.enableCors({ origin: config.corsOrigins.includes('*') ? true : config.corsOrigins });
  app.useGlobalPipes(new ValidationPipe({ whitelist: true, transform: true }));
  const doc = new DocumentBuilder().setTitle('MiniDrive API').setVersion('0.1').addBearerAuth().build();
  SwaggerModule.setup('docs', app, SwaggerModule.createDocument(app, doc));
  await app.listen(config.port);
}

bootstrap();
