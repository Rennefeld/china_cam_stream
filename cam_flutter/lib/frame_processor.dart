
import 'dart:typed_data';
import 'package:image/image.dart' as img;

class FrameProcessor {
  final bool rotate90;
  final bool flipH;
  final bool flipV;
  final bool grayscale;

  FrameProcessor({
    this.rotate90 = false,
    this.flipH = false,
    this.flipV = false,
    this.grayscale = false,
  });

  Uint8List process(Uint8List input) {
    final image = img.decodeImage(input);
    if (image == null) return input;

    img.Image processed = image;

    if (flipH) processed = img.flipHorizontal(processed);
    if (flipV) processed = img.flipVertical(processed);
    if (rotate90) processed = img.copyRotate(processed, 90);
    if (grayscale) processed = img.grayscale(processed);

    return Uint8List.fromList(img.encodeJpg(processed));
  }
}
