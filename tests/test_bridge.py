import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from galaxy.bridge import FrameBridge, HEADER, MAGIC, JSON_CAPACITY, PIXEL_OFFSET


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.writer=FrameBridge(writer=True,backing_file=Path(self.directory.name)/'bridge.bin')

    def tearDown(self):
        self.writer.close()
        self.directory.cleanup()

    def test_roundtrip_and_dimensions(self):
        pixels=bytes([1,2,3,255])*4
        self.writer.write({'width':2,'height':2,'center_x':.3},pixels)
        metadata,read_pixels=self.writer.read()
        self.assertEqual(pixels,read_pixels)
        self.assertEqual(metadata['center_x'],.3)

    def test_in_progress_frame_rejected(self):
        self.writer.write({'width':1,'height':1},b'1234')
        struct.pack_into('<Q',self.writer.memory,8,3)
        self.assertIsNone(self.writer.read())

    def test_incorrect_payload_size_rejected(self):
        self.writer.write({'width':2,'height':2},b'1234')
        self.assertIsNone(self.writer.read())

    def test_invalid_magic_and_json_rejected(self):
        self.writer.write({'width':1,'height':1},b'1234')
        self.writer.memory[HEADER.size:HEADER.size+1]=b'!'
        self.assertIsNone(self.writer.read())
        self.writer.memory[:8]=b'WRONG000'
        self.assertIsNone(self.writer.read())

    def test_metadata_overflow_rejected(self):
        with self.assertRaises(ValueError):
            self.writer.write({'large':'x'*JSON_CAPACITY},b'1234')

    def test_reader_does_not_publish(self):
        path=Path(self.directory.name)/'bridge.bin'
        with FrameBridge(backing_file=path) as reader:
            with self.assertRaises(RuntimeError):
                reader.write({},b'1234')


if __name__=='__main__':
    unittest.main()
