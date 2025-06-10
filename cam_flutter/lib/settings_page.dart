import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'settings.dart';

class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key});

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  final _ipCtrl = TextEditingController();
  final _portCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    final settings = context.read<Settings>();
    _ipCtrl.text = settings.camIp;
    _portCtrl.text = settings.camPort.toString();
  }

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<Settings>();
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            TextField(
              controller: _ipCtrl,
              decoration: const InputDecoration(labelText: 'Camera IP'),
              onChanged: (v) => settings.update(camIp: v),
            ),
            TextField(
              controller: _portCtrl,
              decoration: const InputDecoration(labelText: 'Camera Port'),
              keyboardType: TextInputType.number,
              onChanged: (v) => settings.update(camPort: int.tryParse(v) ?? settings.camPort),
            ),
            const SizedBox(height: 20),
            DropdownButton<int>(
              value: settings.width,
              items: const [
                DropdownMenuItem(value: 640, child: Text('640x480')),
                DropdownMenuItem(value: 800, child: Text('800x600')),
                DropdownMenuItem(value: 1280, child: Text('1280x720')),
                DropdownMenuItem(value: 1920, child: Text('1920x1080')),
              ],
              onChanged: (v) {
                if (v == null) return;
                final h = v == 640
                    ? 480
                    : v == 800
                        ? 600
                        : v == 1280
                            ? 720
                            : 1080;
                settings.update(width: v, height: h);
              },
            ),
            const SizedBox(height: 20),
            Row(
              children: [
                const Text('Brightness'),
                Expanded(
                  child: Slider(
                    value: settings.brightness,
                    min: 0.0,
                    max: 2.0,
                    onChanged: (v) => settings.update(brightness: v),
                  ),
                ),
              ],
            ),
            SwitchListTile(
              title: const Text('Grayscale'),
              value: settings.grayscale,
              onChanged: (v) => settings.update(grayscale: v),
            ),
          ],
        ),
      ),
    );
  }

  @override
  void dispose() {
    _ipCtrl.dispose();
    _portCtrl.dispose();
    super.dispose();
  }
}
