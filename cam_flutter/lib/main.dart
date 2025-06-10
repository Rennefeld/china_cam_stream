import 'dart:typed_data';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:path_provider/path_provider.dart';
import 'package:ffmpeg_kit_flutter/ffmpeg_kit.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'services/log_service.dart';
import 'snapshot_service.dart';
import 'package:provider/provider.dart';
import 'udp_stream_receiver.dart';
import 'settings.dart';
import 'udp_stream_receiver.dart';
import 'settings_page.dart';
import 'frame_processor.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await LogService.init();
  LogService.instance.info('Application started');
  runApp(const CamApp());
  
void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final settings = await Settings.load();
  runApp(ChangeNotifierProvider.value(value: settings, child: const CamApp()));
}

class CamApp extends StatelessWidget {
  const CamApp({super.key});

  @override
  State<CamApp> createState() => _CamAppState();
}

class _CamAppState extends State<CamApp> {
  //warum 8081 ?? muss da nicht der ephemeral port hin ?
  final _channel = WebSocketChannel.connect(Uri.parse('ws://localhost:8081'));
  Uint8List? _rawFrame;
  late final WebSocketChannel _channel;
  late UdpStreamReceiver _receiver;
  Uint8List? _frame;
  bool _recording = false;
  final List<Uint8List> _buffer = [];
  Directory? _storeDir;
  late final SnapshotService _snapshotService;

  bool _rotate = false;
  bool _flipH = false;
  bool _flipV = false;
  bool _grayscale = false;

  @override
  void initState() {
    super.initState();
    LogService.instance.info('Connecting to stream');
    _channel = WebSocketChannel.connect(Uri.parse('ws://localhost:8081'));
    _channel.stream.listen(
      (data) {
        setState(() {
          _frame = data as Uint8List;
        });
      },
      onError: (error) {
        LogService.instance.error('WebSocket error: $error');
      },
      onDone: () {
        LogService.instance.info('WebSocket closed');
      },
    );
    
    final settings = context.read<Settings>();
    _receiver = UdpStreamReceiver(settings)..onFrame = (f) {
      setState(() => _frame = f);
    };
    _initStorage();
    _channel.stream.listen((data) {
      _rawFrame = data as Uint8List;
      _applyProcessing();
    });
  }

  void _applyProcessing() {
    if (_rawFrame == null) return;
    final processor = FrameProcessor(
      rotate90: _rotate,
      flipH: _flipH,
      flipV: _flipV,
      grayscale: _grayscale,
    );
    setState(() {
      _frame = processor.process(_rawFrame!);
      setState(() {
        _frame = data as Uint8List;
        if (_recording) {
          _buffer.add(Uint8List.fromList(_frame!));
        }
      });
    _snapshotService = SnapshotService();
    _channel.stream.listen((data) {
      _frameNotifier.value = data as Uint8List;
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
        body: Column(
          children: [
            Padding(
              padding: const EdgeInsets.all(8),
              child: ToggleButtons(
                isSelected: [_rotate, _flipH, _flipV, _grayscale],
                onPressed: (index) {
                  setState(() {
                    switch (index) {
                      case 0:
                        _rotate = !_rotate;
                        break;
                      case 1:
                        _flipH = !_flipH;
                        break;
                      case 2:
                        _flipV = !_flipV;
                        break;
                      case 3:
                        _grayscale = !_grayscale;
                        break;
                    }
                  });
                  _applyProcessing();
                },
                children: const [
                  Icon(Icons.rotate_90_degrees_ccw),
                  Icon(Icons.swap_horiz),
                  Icon(Icons.swap_vert),
                  Icon(Icons.filter_b_and_w),
                ],
              ),
            ),
            Expanded(
              child: Center(
                child: _frame == null
                    ? const Text('Waiting for stream...')
                    : Image.memory(_frame!),
              ),
            ),
          ],
        appBar: AppBar(
          title: const Text('Cam Stream'),
          actions: [
            IconButton(
              icon: const Icon(Icons.settings),
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const SettingsPage()),
              ),
            )
          ],
        ),
        body: Center(
          child: ValueListenableBuilder<Uint8List?>(
            valueListenable: _frameNotifier,
            builder: (context, frame, _) {
              return frame == null
                  ? const Text('Waiting for stream...')
                  : Image.memory(frame);
            },
          ),
        ),
        floatingActionButton: FloatingActionButton(
          onPressed: _toggleRecord,
          child: Icon(_recording ? Icons.stop : Icons.fiber_manual_record),
        ),
        floatingActionButton: _frame == null
            ? null
            : FloatingActionButton(
                onPressed: () async {
                  await _snapshotService.save(_frame!);
                  if (!mounted) return;
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Snapshot saved')),
                  );
                },
                child: const Icon(Icons.camera_alt),
              ),
      ),
    );
  }
}

class _CamView extends StatelessWidget {
  const _CamView();

  @override
  void dispose() {
    LogService.instance.info('Disposing app');
    _receiver.dispose();
    _channel.sink.close();
    _frameNotifier.dispose();
    super.dispose();
  }
}
