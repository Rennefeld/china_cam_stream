import 'dart:async';
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/foundation.dart';

class UdpStreamReceiver extends ChangeNotifier {
  final String camIp;
  final int camPort;
  final ValueNotifier<Uint8List?> frame = ValueNotifier(null);
  RawDatagramSocket? _socket;
  Timer? _keepAliveTimer;
  final BytesBuilder _buffer = BytesBuilder();
  bool _collecting = false;

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
