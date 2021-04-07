import os
import sys
import lzma
import lzham
import hashlib
import argparse
import zstandard

from PIL import Image
from Writer import BinaryWriter


class Packer(BinaryWriter):

    def __init__(self, use_lzma, use_lzham, use_zstd, splitting, header, outputName):
        self.settings = {
                         'use_lzma': use_lzma,
                         'use_lzham': use_lzham,
                         'use_zstd': use_zstd,
                         'splitting': splitting,
                         'header': header,
                         'outputname': outputName
                         }
        self.image_list = []
        super().__init__()

    def load_image(self, path, pixelFormat):
        if pixelFormat in (0, 1, 2, 3, 4, 6, 10):
            self.image_list.append({
                                    "Image": Image.open(path),
                                    "Path": path,
                                    "PixelFormat": pixelFormat
                                    })

        else:
            print('[*] Unsupported pixelformat ({}) ! '.format(pixelFormat))
            sys.exit()

    def pack(self):
        pixelSizeList = {
                         0: 4,
                         1: 4,
                         2: 2,
                         3: 2,
                         4: 2,
                         6: 2,
                         10: 1
                         }

        if self.settings['splitting']:
            fileType = 28

        else:
            fileType = 1

        for image in self.image_list:
            pixelFormat = image['PixelFormat']
            pixelSize = pixelSizeList[pixelFormat]
            imageWidth = image['Image'].width
            imageHeight = image['Image'].height
            texureSize = imageWidth * imageHeight * pixelSize + 5

            print('[INFO] Packing {}, width: {}, height: {}, pixelformat: {}'.format(image['Path'], imageHeight, imageWidth, pixelFormat))

            # Texture header
            self.write_uint8(fileType)
            self.write_uint32(texureSize)
            self.write_uint8(pixelFormat)
            self.write_uint16(imageWidth)
            self.write_uint16(imageHeight)

            if self.settings['splitting']:
                self.split_image(image['Image'])

            pixels = image['Image'].load()

            for y in range(imageHeight):
                for x in range(imageWidth):
                    colors = pixels[x, y]
                    self.write_pixel(pixelFormat, colors)

        self.write(5)

        if True in (self.settings['use_lzma'], self.settings['use_lzham'], self.settings['use_zstd']):
            self.compress_data()

        if self.settings['outputname']:
            outputName = self.settings['outputname']

        else:
            outputName = os.path.splitext(self.image_list[0]['Path'])[0].rstrip('_') + '.sc'

        with open(outputName, 'wb') as f:
            f.write(self.buffer)

    def split_image(self, image):
        imageWidth = image.width
        imageHeight = image.height
        imgl = image.load()
        pixels = []

        print('[*] Splitting texture')

        for l in range(imageHeight // 32):
            for k in range(imageWidth // 32):
                for j in range(32):
                    for h in range(32):
                        pixels.append(imgl[h + (k * 32), j + (l * 32)])

            for j in range(32):
                for h in range(imageWidth % 32):
                    pixels.append(imgl[h + (imageWidth - (imageWidth % 32)), j + (l * 32)])

        for k in range(imageWidth // 32):
            for j in range(int(imageHeight % 32)):
                for h in range(32):
                    pixels.append(imgl[h + (k * 32), j + (imageHeight - (imageHeight % 32))])

        for j in range(imageHeight % 32):
            for h in range(imageWidth % 32):
                pixels.append(imgl[h + (imageWidth - (imageWidth % 32)), j + (imageHeight - (imageHeight % 32))])

        image.putdata(pixels)
        print('[*] Splitting done !')

    def write_pixel(self, pixelFormat, colors):
        red, green, blue, alpha = colors

        if pixelFormat in (0, 1):
            # RGBA8888
            self.write_uint8(red)
            self.write_uint8(green)
            self.write_uint8(blue)
            self.write_uint8(alpha)

        elif pixelFormat == 2:
            # RGBA8888 to RGBA4444
            r = (red >> 4) << 12
            g = (green >> 4) << 8
            b = (blue >> 4) << 4
            a = alpha >> 4

            self.write_uint16(a | b | g | r)

        elif pixelFormat == 3:
            # RGBA8888 to RGBA5551
            r = (red >> 3) << 11
            g = (green >> 3) << 6
            b = (blue >> 3) << 1
            a = alpha >> 7

            self.write_uint16(a | b | g | r)

        elif pixelFormat == 4:
            # RGBA8888 to RGBA565
            r = (red >> 3) << 11
            g = (green >> 2) << 5
            b = blue >> 3

            self.write_uint16(b | g | r)

        elif pixelFormat == 6:
            # RGBA8888 to LA88 (Luminance Alpha)
            self.write_uint8(alpha)
            self.write_uint8(red)

        elif pixelFormat == 10:
            # RGBA8888 to L8 (Luminance)
            self.write_uint8(red)

    def compress_data(self):
        if self.settings['use_lzma']:
            print('[*] Compressing texture with lzma')

            filters = [
                       {
                        "id": lzma.FILTER_LZMA1,
                        "dict_size": 256 * 1024,
                        "lc": 3,
                        "lp": 0,
                        "pb": 2,
                        "mode": lzma.MODE_NORMAL
                        },
                       ]

            compressed = lzma.compress(self.buffer, format=lzma.FORMAT_ALONE, filters=filters)
            compressed = compressed[0:5] + len(self.buffer).to_bytes(4, 'little') + compressed[13:]

        elif self.settings['use_lzham']:
            print('[*] Compressing texture with lzham')

            dict_size = 18

            compressed = lzham.compress(self.buffer, {'dict_size_log2': dict_size})
            compressed = 'SCLZ'.encode('utf-8') + dict_size.to_bytes(1, 'big') + len(self.buffer).to_bytes(4, 'little') + compressed

        else:
            print('[*] Compressing texture with zstandard')
            compressed = zstandard.compress(self.buffer, level=zstandard.MAX_COMPRESSION_LEVEL)

        fileMD5 = hashlib.md5(self.buffer).digest()

        # Flush the previous buffer
        self.buffer = b''

        if self.settings['header']:
            self.write('SC'.encode('utf-8'))

            if self.settings['use_zstd']:
                self.write_uint32(3, 'big')

            else:
                self.write_uint32(1, 'big')

            self.write_uint32(len(fileMD5), 'big')
            self.write(fileMD5)

            print('[*] Header wrote !')

        self.write(compressed)

        print('[*] Compression done !')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="scPacker is a tool that allows you to convert PNG files to _tex.sc files")
    parser.add_argument('files', help='.png file(s) to pack', nargs='+')
    parser.add_argument('-lzma', '--lzma', help='enable LZMA compression', action='store_true')
    parser.add_argument('-lzham', '--lzham', help='enable LZHAM compression', action='store_true')
    parser.add_argument('-zstd', '--zstd', help='enable Zstandard compression', action='store_true')
    parser.add_argument('-header', '--header', help='add SC header to the beginning of the compressed _tex.sc', action='store_true')
    parser.add_argument('-o', '--outputname', help='define an output name for the _tex.sc file (if not specified the output filename is set to <first_packed_filename> + _tex.sc')
    parser.add_argument('-p', '--pixelformat', help='pixelformat(s) to be used to pack .png to _tex.sc', nargs='+', type=int)
    parser.add_argument('-s', '--splitting', help='enable 32x32 block splitting', action='store_true')

    args = parser.parse_args()

    if args.pixelformat:
        if len(args.files) == len(args.pixelformat):
            if (args.lzham, args.lzma, args.zstd).count(True) == 1:
                scPacker = Packer(args.lzma, args.lzham, args.zstd, args.splitting, args.header, args.outputname)

                for file, pixelFormat in zip(args.files, args.pixelformat):
                    if file.endswith('.png'):
                        if os.path.exists(file):
                            scPacker.load_image(file, pixelFormat)

                        else:
                            print('[*] {} doesn\'t exists !'.format(file))
                            sys.exit()

                    else:
                        print('[*] Only .png are supported !')
                        sys.exit()

                scPacker.pack()

            else:
                print('[*] You cannot set many compression at a time !')

        else:
            print('[*] Files count and pixelformats count don\'t match !')

    else:
        print('[*] PixelFormat args is empty !')
