import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'settings.dart';
import 'udp_stream_receiver.dart';
import 'settings_page.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final settings = await Settings.load();
  runApp(ChangeNotifierProvider.value(value: settings, child: const CamApp()));
}

class CamApp extends StatefulWidget {
  const CamApp({super.key});

  @override
  State<CamApp> createState() => _CamAppState();
}

class _CamAppState extends State<CamApp> {
  late UdpStreamReceiver _receiver;
  Uint8List? _frame;

  @override
  void initState() {
    super.initState();
    final settings = context.read<Settings>();
    _receiver = UdpStreamReceiver(settings)..onFrame = (f) {
      setState(() => _frame = f);
    };
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: Scaffold(
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
          child: _frame == null
              ? const Text('Waiting for stream...')
              : Image.memory(_frame!),
        ),
      ),
    );
  }

  @override
  void dispose() {
    _receiver.dispose();
    super.dispose();
  }
}
