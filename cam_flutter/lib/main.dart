import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'services/log_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await LogService.init();
  LogService.instance.info('Application started');
  runApp(const CamApp());
}

class CamApp extends StatefulWidget {
  const CamApp({super.key});

  @override
  State<CamApp> createState() => _CamAppState();
}

class _CamAppState extends State<CamApp> {
  late final WebSocketChannel _channel;
  Uint8List? _frame;

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
      ),
    );
  }

  @override
  void dispose() {
    LogService.instance.info('Disposing app');
    _channel.sink.close();
    super.dispose();
  }
}
