import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'keep_alive_service.dart';

/// Receives MJPEG frames over UDP.
class UdpStreamReceiver {
  UdpStreamReceiver({required this.camIp, required this.camPort});

  final String camIp;
  final int camPort;

  RawDatagramSocket? _socket;
  late final KeepAliveService _keepAlive;

  final _controller = StreamController<Uint8List>.broadcast();
  BytesBuilder? _buffer;
  bool _collecting = false;

  /// Stream of raw JPEG frames.
  Stream<Uint8List> get stream => _controller.stream;

  /// Open the socket and begin listening.
  Future<void> start() async {
    _socket = await RawDatagramSocket.bind(InternetAddress.anyIPv4, 0);
    _keepAlive = KeepAliveService(_socket!, InternetAddress(camIp));
    _keepAlive.start();
    _socket!.listen(_onData);
  }

  void _onData(RawSocketEvent event) {
    if (event != RawSocketEvent.read || _socket == null) return;
    final datagram = _socket!.receive();
    if (datagram == null) return;
    final data = datagram.data;
    if (data.length < 8) return;
    final payload = data.sublist(8);
    _buffer ??= BytesBuilder();
    if (payload.length >= 2 && payload[0] == 0xff && payload[1] == 0xd8) {
      _buffer!.clear();
      _buffer!.add(payload);
      _collecting = true;
    } else if (_collecting) {
      _buffer!.add(payload);
    }
    if (_collecting && payload.contains(0xd9)) {
      final frame = _buffer!.toBytes();
      _controller.add(frame);
      _collecting = false;
      _buffer = BytesBuilder();
    }
  }

  /// Stop listening and close the socket.
  Future<void> stop() async {
    _keepAlive.stop();
    _socket?.close();
    _socket = null;
    await _controller.close();
  }
}
