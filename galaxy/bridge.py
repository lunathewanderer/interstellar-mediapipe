"""Windows named, pagefile-backed memory. No image files and no network sockets.

Protocol v1: 8-byte magic, uint64 sequence, uint32 JSON length, uint32 RGBA length;
JSON starts at 32; RGBA at 65568. Odd sequence = writer busy. Reader accepts only
an unchanged, even sequence. Single writer enforced by Windows named mutex.
"""
import ctypes
import json
import mmap
import os
import struct

MAGIC = b'GLXY0001'
HEADER = struct.Struct('<8sQII8x')
JSON_CAPACITY = 65536
PIXEL_OFFSET = HEADER.size + JSON_CAPACITY
SIZE = PIXEL_OFFSET + 1280 * 720 * 4
NAME = r'Local\GalaxyHandsFrames_v1'
MUTEX = r'Local\GalaxyHandsWriter_v1'


class CameraBusyError(RuntimeError):
    pass


class FrameBridge:
    def __init__(self, writer=False, backing_file=None):
        self.writer, self.sequence, self.handle, self.file = writer, 0, None, None
        if backing_file is not None:  # Only automated tests use a temporary disk file.
            self.file = open(backing_file, 'w+b' if writer else 'r+b')
            if writer:
                self.file.truncate(SIZE)
            self.memory = mmap.mmap(self.file.fileno(), SIZE)
        elif os.name == 'nt':
            if writer:
                self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
                self.kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
                self.kernel.CreateMutexW.restype = ctypes.c_void_p
                self.kernel.CloseHandle.argtypes = [ctypes.c_void_p]
                self.handle = self.kernel.CreateMutexW(None, False, MUTEX)
                if not self.handle:
                    raise ctypes.WinError(ctypes.get_last_error())
                if ctypes.get_last_error() == 183:
                    self.kernel.CloseHandle(self.handle)
                    self.handle = None
                    raise CameraBusyError('Another Galaxy Hands tracker is running. Close it first.')
            self.memory = mmap.mmap(-1, SIZE, tagname=NAME, access=mmap.ACCESS_WRITE)
        else:
            raise RuntimeError('Named bridge requires Windows. Tests may use backing_file.')
        if writer:
            self.memory[:HEADER.size] = HEADER.pack(MAGIC, 0, 0, 0)

    def write(self, metadata, rgba_bytes):
        if not self.writer:
            raise RuntimeError('Only the tracker may publish frames.')
        payload = json.dumps(metadata, separators=(',', ':'), allow_nan=False).encode('utf-8')
        size = len(rgba_bytes)
        if len(payload) > JSON_CAPACITY or size > SIZE - PIXEL_OFFSET:
            raise ValueError('Frame exceeds bridge capacity.')
        self.sequence += 2
        self.memory[:HEADER.size] = HEADER.pack(MAGIC, self.sequence - 1, len(payload), size)
        self.memory[HEADER.size:HEADER.size + len(payload)] = payload
        self.memory[PIXEL_OFFSET:PIXEL_OFFSET + size] = rgba_bytes
        struct.pack_into('<Q', self.memory, 8, self.sequence)

    def read(self):
        magic, sequence, json_size, pixel_size = HEADER.unpack_from(self.memory)
        if magic != MAGIC or not sequence or sequence % 2:
            return None
        if not 0 < json_size <= JSON_CAPACITY or not 0 < pixel_size <= SIZE - PIXEL_OFFSET:
            return None
        payload = bytes(self.memory[HEADER.size:HEADER.size + json_size])
        pixels = bytes(self.memory[PIXEL_OFFSET:PIXEL_OFFSET + pixel_size])
        if struct.unpack_from('<Q', self.memory, 8)[0] != sequence:
            return None
        try:
            meta = json.loads(payload)
            if not (1 <= meta['width'] <= 1280 and 1 <= meta['height'] <= 720):
                return None
            if meta['width'] * meta['height'] * 4 != pixel_size:
                return None
            return meta, pixels
        except (ValueError, KeyError, TypeError):
            return None

    def close(self):
        if hasattr(self, 'memory'):
            self.memory.close()
        if self.file:
            self.file.close()
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
