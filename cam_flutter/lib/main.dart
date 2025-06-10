import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
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

  @override
  void initState() {
    super.initState();
    _channel.stream.listen((data) {
      setState(() {
        _frame = data as Uint8List;
      });
    });
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
    _channel.sink.close();
    super.dispose();
  }
}
