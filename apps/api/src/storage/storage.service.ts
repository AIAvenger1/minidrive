import { Injectable, NotFoundException, OnModuleInit } from '@nestjs/common';
import {
  CreateBucketCommand,
  DeleteObjectCommand,
  GetObjectCommand,
  HeadBucketCommand,
  PutObjectCommand,
  S3Client,
} from '@aws-sdk/client-s3';
import type { Readable } from 'stream';
import { loadConfig } from '../config';

function isMissingBucketError(err: unknown): boolean {
  const e = err as { $metadata?: { httpStatusCode?: number }; name?: string };
  return (
    e?.$metadata?.httpStatusCode === 404 ||
    e?.name === 'NotFound' ||
    e?.name === 'NoSuchBucket'
  );
}

@Injectable()
export class StorageService implements OnModuleInit {
  constructor(
    private readonly s3: S3Client,
    private readonly bucket: string,
  ) {}

  static fromEnv(): StorageService {
    const { s3 } = loadConfig();
    const client = new S3Client({
      endpoint: s3.endpoint,
      region: s3.region,
      forcePathStyle: true,
      credentials: { accessKeyId: s3.accessKey, secretAccessKey: s3.secretKey },
    });
    return new StorageService(client, s3.bucket);
  }

  async onModuleInit() {
    try {
      await this.s3.send(new HeadBucketCommand({ Bucket: this.bucket }));
    } catch (err) {
      if (isMissingBucketError(err)) {
        await this.s3.send(new CreateBucketCommand({ Bucket: this.bucket }));
      } else {
        throw err;
      }
    }
  }

  async putObject(key: string, body: Buffer, mimeType: string): Promise<void> {
    await this.s3.send(
      new PutObjectCommand({
        Bucket: this.bucket,
        Key: key,
        Body: body,
        ContentType: mimeType,
      }),
    );
  }

  async getObject(
    key: string,
  ): Promise<{ stream: Readable; mimeType: string; size?: number }> {
    const res = await this.s3.send(
      new GetObjectCommand({ Bucket: this.bucket, Key: key }),
    );
    if (!res.Body) throw new NotFoundException('Object not found');
    return {
      stream: res.Body as Readable,
      mimeType: res.ContentType ?? 'application/octet-stream',
      size: res.ContentLength,
    };
  }

  async deleteObject(key: string): Promise<void> {
    await this.s3.send(
      new DeleteObjectCommand({ Bucket: this.bucket, Key: key }),
    );
  }
}
