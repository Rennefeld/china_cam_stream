import 'dart:typed_data';
import 'package:image/image.dart' as img;

/// Processes raw frame bytes applying optional transformations.
class FrameProcessor {
  final bool rotate90;
  final bool flipH;
  final bool flipV;
  final bool grayscale;

  const FrameProcessor({
    this.rotate90 = false,
    this.flipH = false,
    this.flipV = false,
    this.grayscale = false,
  });

  /// Applies the configured transformations to [bytes].
  Uint8List process(Uint8List bytes) {
    final img.Image? original = img.decodeImage(bytes);
    if (original == null) return bytes;
    img.Image frame = original;

    if (rotate90) {
      frame = img.copyRotate(frame, 90);
    }
    if (flipH) {
      frame = img.flipHorizontal(frame);
    }
    if (flipV) {
      frame = img.flipVertical(frame);
    }
    if (grayscale) {
      frame = img.grayscale(frame);
    }

    return Uint8List.fromList(img.encodeJpg(frame));
  }
}
