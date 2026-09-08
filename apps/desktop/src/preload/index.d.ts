import type { MinidriveApi } from './index';

declare global {
  interface Window {
    minidrive: MinidriveApi;
  }
}
