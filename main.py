
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:path_provider/path_provider.dart';
import 'services/log_service.dart';
import 'snapshot_service.dart';
import 'udp_stream_receiver.dart';
import 'settings.dart';
import 'settings_page.dart';
import 'frame_processor.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await LogService.init();
  final settings = await Settings.load();
  runApp(ChangeNotifierProvider.value(value: settings, child: const CamApp()));
}

class CamApp extends StatelessWidget {
  const CamApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      home: const CamStreamPage(),
    );
  }
}

class CamStreamPage extends StatefulWidget {
  const CamStreamPage({super.key});

  @override
  State<CamStreamPage> createState() => _CamStreamPageState();
}

class _CamStreamPageState extends State<CamStreamPage> {
  Uint8List? _rawFrame;
  Uint8List? _processedFrame;
  late final UdpStreamReceiver _receiver;
  late final SnapshotService _snapshotService;
  bool _recording = false;
  final List<Uint8List> _recordedFrames = [];
  Directory? _storageDir;

  // Bildverarbeitung
  bool _rotate = false;
  bool _flipH = false;
  bool _flipV = false;
  bool _grayscale = false;

  @override
  void initState() {
    super.initState();
    _snapshotService = SnapshotService();
    _initStorage();
    _initReceiver();
  }

  void _initReceiver() {
    final settings = context.read<Settings>();
    _receiver = UdpStreamReceiver(settings);
    _receiver.onFrame = (frame) {
      setState(() {
        _rawFrame = frame;
        _processedFrame = FrameProcessor(
          rotate90: _rotate,
          flipH: _flipH,
          flipV: _flipV,
          grayscale: _grayscale,
        ).process(frame);

        if (_recording && _processedFrame != null) {
          _recordedFrames.add(Uint8List.fromList(_processedFrame!));
        }
      });
    };
    _receiver.start();
  }

  Future<void> _initStorage() async {
    _storageDir = await getApplicationDocumentsDirectory();
  }

  @override
  void dispose() {
    _receiver.stop();
    super.dispose();
  }

  void _toggleRecording() {
    setState(() {
      _recording = !_recording;
    });
    LogService.instance.info(_recording ? "Recording started" : "Recording stopped");
    if (!_recording) {
      _snapshotService.saveVideo(_recordedFrames, _storageDir!);
      _recordedFrames.clear();
    }
  }

  void _takeSnapshot() {
    if (_processedFrame != null && _storageDir != null) {
      _snapshotService.saveSnapshot(_processedFrame!, _storageDir!);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('H4R1 Cam Streamer')),
      body: Column(
        children: [
          Expanded(
            child: _processedFrame == null
                ? const Center(child: Text('Waiting for stream...'))
                : Image.memory(_processedFrame!),
          ),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              IconButton(
                icon: Icon(_recording ? Icons.stop : Icons.fiber_manual_record),
                color: _recording ? Colors.red : Colors.black,
                onPressed: _toggleRecording,
              ),
              IconButton(
                icon: const Icon(Icons.camera),
                onPressed: _takeSnapshot,
              ),
              IconButton(
                icon: const Icon(Icons.settings),
                onPressed: () => Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const SettingsPage()),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
