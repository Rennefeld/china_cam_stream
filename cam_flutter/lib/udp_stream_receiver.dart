import 'dart:typed_data';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/status.dart' as status;
import 'settings.dart';
import 'dart:async';
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/foundation.dart';

typedef FrameCallback = void Function(Uint8List frame);

class UdpStreamReceiver extends ChangeNotifier {
  final String camIp;
  final int camPort;
  final ValueNotifier<Uint8List?> frame = ValueNotifier(null);
  RawDatagramSocket? _socket;
  Timer? _keepAliveTimer;
  final BytesBuilder _buffer = BytesBuilder();
  bool _collecting = false;

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
    
  UdpStreamReceiver({required this.camIp, this.camPort = 8080}) {
    _bindSocket();
  }

  Future<void> _bindSocket() async {
    _socket = await RawDatagramSocket.bind(InternetAddress.anyIPv4, 0);
    _socket!.listen(_onEvent);
    _keepAliveTimer =
        Timer.periodic(const Duration(seconds: 1), (_) => _sendKeepAlive());
  }

  void _sendKeepAlive() {
    _socket?.send(Uint8List.fromList([0x42, 0x76]), InternetAddress(camIp), camPort);
  }

  void _onEvent(RawSocketEvent event) {
    if (event != RawSocketEvent.read) return;
    final datagram = _socket!.receive();
    if (datagram == null) return;
    final data = datagram.data;
    if (data.length <= 8) return;
    final payload = data.sublist(8);
    if (payload.length >= 2 && payload[0] == 0xff && payload[1] == 0xd8) {
      _buffer.clear();
      _buffer.add(payload);
      _collecting = true;
    } else if (_collecting) {
      _buffer.add(payload);
    }
    if (_collecting && _endsWithEoi(payload)) {
      frame.value = _buffer.takeBytes();
      _collecting = false;
      notifyListeners();
    }
  }

  bool _endsWithEoi(Uint8List data) {
    for (var i = 0; i < data.length - 1; i++) {
      if (data[i] == 0xff && data[i + 1] == 0xd9) return true;
    }
    return false;
  }

  @override
  void dispose() {
    _keepAliveTimer?.cancel();
    _socket?.close();
    frame.dispose();
    super.dispose();
  }
}
