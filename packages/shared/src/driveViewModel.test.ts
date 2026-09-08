import { describe, expect, it } from 'vitest';
import type { FileDto } from './types';
import { DriveViewModel } from './driveViewModel';
import { makeFileDto } from './testFixtures';

const f = (name: string): FileDto => makeFileDto({ id: name, name });

describe('DriveViewModel', () => {
  it('applies sort by name and the cpp/png filter to visibleFiles', () => {
    const vm = new DriveViewModel();
    vm.setFiles([f('z.png'), f('a.cs'), f('m.cpp'), f('B.txt')]);
    expect(vm.visibleFiles.map((x) => x.name)).toEqual(['a.cs', 'B.txt', 'm.cpp', 'z.png']);
    vm.setOrder('desc');
    expect(vm.visibleFiles.map((x) => x.name)).toEqual(['z.png', 'm.cpp', 'B.txt', 'a.cs']);
    vm.setFilter('cpp-png');
    expect(vm.visibleFiles.map((x) => x.name)).toEqual(['z.png', 'm.cpp']);
  });

  it('cannot hide the name column', () => {
    const vm = new DriveViewModel();
    vm.toggleColumn('name');
    vm.toggleColumn('size');
    expect(vm.columns.name).toBe(true);
    expect(vm.columns.size).toBe(false);
  });
});
