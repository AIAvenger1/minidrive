import path from 'path';
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'standalone',
  devIndicators: false,
  outputFileTracingRoot: path.join(process.cwd(), '../..'),
  transpilePackages: ['@minidrive/shared', '@minidrive/ui'],
};

export default nextConfig;
