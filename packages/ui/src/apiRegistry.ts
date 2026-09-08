import { ApiClient } from '@minidrive/shared';

let client = new ApiClient('http://localhost:3000');

export function configureApi(baseUrl: string, token: string | null): ApiClient {
  client = new ApiClient(baseUrl, token);
  return client;
}

export function getApi(): ApiClient {
  return client;
}
