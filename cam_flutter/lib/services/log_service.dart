import 'dart:io';
import 'package:path_provider/path_provider.dart';

/// A simple singleton log service writing entries to a file and console.
class LogService {
  LogService._internal();

  static final LogService instance = LogService._internal();

  late final File _logFile;

  /// Initializes the log file inside the application's document directory.
  static Future<void> init() async {
    final dir = await getApplicationDocumentsDirectory();
    instance._logFile = File('${dir.path}/app.log');
    if (!await instance._logFile.exists()) {
      await instance._logFile.create(recursive: true);
    }
  }

  /// Writes an info level entry.
  void info(String msg) => _write('INFO', msg);

  /// Writes an error level entry.
  void error(String msg) => _write('ERROR', msg);

  void _write(String level, String msg) {
    final entry = '${DateTime.now().toIso8601String()} [$level] $msg';
    // Print to console for quick feedback.
    // Also append to the log file for persistence.
    print(entry);
    _logFile.writeAsStringSync('$entry\n', mode: FileMode.append);
  }
}
