import 'dart:typed_data';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:ffmpeg_kit_flutter/ffmpeg_kit.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

void main() {
  runApp(const CamApp());
}

class CamApp extends StatefulWidget {
  const CamApp({super.key});

  @override
  State<CamApp> createState() => _CamAppState();
}

class _CamAppState extends State<CamApp> {
  final _channel = WebSocketChannel.connect(Uri.parse('ws://localhost:8081'));
  Uint8List? _frame;
  bool _recording = false;
  final List<Uint8List> _buffer = [];
  Directory? _storeDir;

  @override
  void initState() {
    super.initState();
    _initStorage();
    _channel.stream.listen((data) {
      setState(() {
        _frame = data as Uint8List;
        if (_recording) {
          _buffer.add(Uint8List.fromList(_frame!));
        }
      });
    });
  }

  Future<void> _initStorage() async {
    _storeDir = await getApplicationDocumentsDirectory();
  }

  Future<void> _toggleRecord() async {
    if (!_recording) {
      setState(() {
        _recording = true;
        _buffer.clear();
      });
    } else {
      setState(() {
        _recording = false;
      });
      await _saveRecording();
    }
  }

  Future<void> _saveRecording() async {
    if (_storeDir == null || _buffer.isEmpty) return;
    final dir = await Directory(
            '${_storeDir!.path}/${DateTime.now().millisecondsSinceEpoch}')
        .create();
    for (var i = 0; i < _buffer.length; i++) {
      final file = File('${dir.path}/frame_${i.toString().padLeft(6, '0')}.jpg');
      await file.writeAsBytes(_buffer[i]);
    }
    final outPath = '${dir.path}/output.mp4';
    final cmd =
        "-y -framerate 30 -i ${dir.path}/frame_%06d.jpg -c:v mpeg4 $outPath";
    await FFmpegKit.execute(cmd);
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: Scaffold(
        appBar: AppBar(title: const Text('Cam Stream')),
        body: Center(
          child: _frame == null
              ? const Text('Waiting for stream...')
              : Image.memory(_frame!),
        ),
        floatingActionButton: FloatingActionButton(
          onPressed: _toggleRecord,
          child: Icon(_recording ? Icons.stop : Icons.fiber_manual_record),
        ),
      ),
    );
  }

  @override
  void dispose() {
    _channel.sink.close();
    super.dispose();
  }
}
