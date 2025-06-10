
import 'dart:io';
import 'dart:typed_data';
import 'package:ffmpeg_kit_flutter/ffmpeg_kit.dart';

class SnapshotService {
  void saveSnapshot(Uint8List bytes, Directory dir) {
    final file = File("\${dir.path}/snapshot_\${DateTime.now().millisecondsSinceEpoch}.jpg");
    file.writeAsBytesSync(bytes);
  }

  void saveVideo(List<Uint8List> frames, Directory dir) async {
    final frameDir = Directory("\${dir.path}/temp_frames");
    if (!frameDir.existsSync()) frameDir.createSync();

    for (int i = 0; i < frames.length; i++) {
      final frameFile = File("\${frameDir.path}/frame_\${i.toString().padLeft(4, '0')}.jpg");
      frameFile.writeAsBytesSync(frames[i]);
    }

    final output = "\${dir.path}/recording_\${DateTime.now().millisecondsSinceEpoch}.mp4";
    final cmd = "-framerate 10 -i \${frameDir.path}/frame_%04d.jpg -c:v libx264 -pix_fmt yuv420p $output";
    await FFmpegKit.execute(cmd);

    frameDir.deleteSync(recursive: true);
  }
}
