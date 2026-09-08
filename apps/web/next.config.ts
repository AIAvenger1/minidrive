import path from 'path';
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'standalone',
  devIndicators: false,
  agentRules: false,
  outputFileTracingRoot: path.resolve(__dirname, '../..'),
  transpilePackages: ['@minidrive/shared', '@minidrive/ui'],
};

export default nextConfig;
