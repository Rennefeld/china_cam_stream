import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import 'frame_processor.dart';

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
  Uint8List? _rawFrame;
  Uint8List? _frame;

  bool _rotate = false;
  bool _flipH = false;
  bool _flipV = false;
  bool _grayscale = false;

  @override
  void initState() {
    super.initState();
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
    });
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
