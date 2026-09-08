import { StorageService } from './storage.service';

describe('StorageService', () => {
  it('sends put, get and delete commands with the configured bucket', async () => {
    const send = jest.fn().mockResolvedValue({ Body: 'stream', ContentType: 'text/plain', ContentLength: 3 });
    const service = new StorageService({ send } as never, 'minidrive');
    await service.putObject('users/u1/f1', Buffer.from('abc'), 'text/plain');
    const got = await service.getObject('users/u1/f1');
    await service.deleteObject('users/u1/f1');
    expect(send).toHaveBeenCalledTimes(3);
    expect(send.mock.calls[0][0].input).toMatchObject({ Bucket: 'minidrive', Key: 'users/u1/f1', ContentType: 'text/plain' });
    expect(got).toMatchObject({ mimeType: 'text/plain', size: 3 });
  });
});
