export type AppConfig = {
  port: number;
  databaseUrl: string;
  jwtSecret: string;
  s3: { endpoint: string; accessKey: string; secretKey: string; bucket: string; region: string };
  corsOrigins: string[];
  maxFileBytes: number;
};

export function loadConfig(env: NodeJS.ProcessEnv = process.env): AppConfig {
  const required = (key: string): string => {
    const value = env[key];
    if (!value) throw new Error(`Missing environment variable ${key}`);
    return value;
  };
  return {
    port: Number(env.PORT ?? 3000),
    databaseUrl: required('DATABASE_URL'),
    jwtSecret: required('JWT_SECRET'),
    s3: {
      endpoint: required('S3_ENDPOINT'),
      accessKey: required('S3_ACCESS_KEY'),
      secretKey: required('S3_SECRET_KEY'),
      bucket: env.S3_BUCKET ?? 'minidrive',
      region: env.S3_REGION ?? 'us-east-1',
    },
    corsOrigins: (env.CORS_ORIGINS ?? '*').split(',').map((s) => s.trim()).filter(Boolean),
    maxFileBytes: Number(env.MAX_FILE_MB ?? 50) * 1024 * 1024,
  };
}
