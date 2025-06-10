import 'dart:io';
import 'dart:async';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'udp_stream_receiver.dart';

void main() {
  runApp(const CamApp());
}

class CamApp extends StatelessWidget {
  const CamApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => UdpStreamReceiver(camIp: '192.168.4.153', camPort: 8080),
      child: MaterialApp(
        home: Scaffold(
          appBar: AppBar(title: const Text('Cam Stream')),
          body: const Center(child: _CamView()),
        ),
      ),
    );
  }
}

class _CamView extends StatelessWidget {
  const _CamView();

  @override
  Widget build(BuildContext context) {
    final receiver = context.watch<UdpStreamReceiver>();
    return ValueListenableBuilder<Uint8List?>(
      valueListenable: receiver.frame,
      builder: (context, data, _) {
        if (data == null) {
          return const Text('Waiting for stream...');
        }
        return Image.memory(data);
      },
    );
  }
}
