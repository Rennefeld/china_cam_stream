import 'dart:io';
import 'dart:typed_data';

import 'package:path_provider/path_provider.dart';

/// Simple service responsible for storing JPEG frames on disk.
class SnapshotService {
  /// Saves [jpeg] with a timestamp based name into the app documents directory.
  ///
  /// Returns the path of the written file.
  Future<String> save(Uint8List jpeg) async {
    final dir = await getApplicationDocumentsDirectory();
    final timestamp = DateTime.now().millisecondsSinceEpoch;
    final path = '${dir.path}/snapshot_$timestamp.jpg';
    final file = File(path);
    await file.writeAsBytes(jpeg);
    return path;
  }
}

