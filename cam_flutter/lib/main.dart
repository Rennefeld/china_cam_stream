import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'snapshot_service.dart';
import 'package:provider/provider.dart';
import 'udp_stream_receiver.dart';

void main() {
  runApp(const CamApp());
}

class CamApp extends StatelessWidget {
  const CamApp({super.key});

  @override
  State<CamApp> createState() => _CamAppState();
}

class _CamAppState extends State<CamApp> {
  final _channel = WebSocketChannel.connect(Uri.parse('ws://localhost:8081'));
  Uint8List? _frame;
  late final SnapshotService _snapshotService;

  @override
  void initState() {
    super.initState();
    _snapshotService = SnapshotService();
    _channel.stream.listen((data) {
      _frameNotifier.value = data as Uint8List;
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: Scaffold(
        appBar: AppBar(title: const Text('Cam Stream')),
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
    _channel.sink.close();
    _frameNotifier.dispose();
    super.dispose();
  }
}
