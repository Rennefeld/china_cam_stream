import 'dart:typed_data';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/status.dart' as status;
import 'settings.dart';

typedef FrameCallback = void Function(Uint8List frame);

class UdpStreamReceiver {
  final Settings settings;
  WebSocketChannel? _channel;
  FrameCallback? onFrame;

  UdpStreamReceiver(this.settings) {
    settings.addListener(_reconnect);
    _connect();
  }

  void _connect() {
    final uri = Uri.parse('ws://${settings.camIp}:8081');
    _channel = WebSocketChannel.connect(uri);
    _channel!.stream.listen((data) {
      if (data is Uint8List) {
        onFrame?.call(data);
      }
    }, onDone: _onDone, onError: (_) => _onDone());
  }

  void _onDone() {
    _channel = null;
  }

  void _reconnect() {
    _channel?.sink.close(status.goingAway);
    _connect();
  }

  void dispose() {
    settings.removeListener(_reconnect);
    _channel?.sink.close(status.goingAway);
  }
}
