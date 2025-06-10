import 'dart:async';
import 'dart:io';
import 'dart:typed_data';
import 'package:shelf/shelf.dart';
import 'package:shelf/shelf_io.dart' as io;
import 'package:shelf_web_socket/shelf_web_socket.dart';

class CameraServer {
  final String camIp;
  final int camPort;
  final List<int> keepAlivePorts;
  late RawDatagramSocket _udp;
  final _clients = <WebSocket>[];
  bool _running = false;

  CameraServer({
    required this.camIp,
    required this.camPort,
    this.keepAlivePorts = const [8070, 8080],
  });

  Future<void> start({InternetAddress address = InternetAddress.anyIPv4, int port = 8081}) async {
    _udp = await RawDatagramSocket.bind(InternetAddress.anyIPv4, 0);
    _running = true;
    _keepAliveLoop();
    _streamLoop();
    final handler = webSocketHandler((WebSocket ws) {
      _clients.add(ws);
      ws.done.whenComplete(() => _clients.remove(ws));
    });
    final pipeline = const Pipeline().addMiddleware(logRequests()).addHandler(handler);
    await io.serve(pipeline, address, port);
    print('HTTP stream on http://${address.address}:$port');
  }

  void _keepAliveLoop() {
    Timer.periodic(const Duration(seconds: 1), (t) {
      if (!_running) return;
      for (final port in keepAlivePorts) {
        final payload = port == 8080 ? [0x42, 0x76] : [0x30, 0x66];
        _udp.send(Uint8List.fromList(payload), InternetAddress(camIp), port);
      }
    });
  }

  void _streamLoop() {
    final buffer = BytesBuilder();
    bool collecting = false;
    _udp.listen((event) {
      if (event == RawSocketEvent.read) {
        final datagram = _udp.receive();
        if (datagram == null) return;
        final data = datagram.data;
        if (data.length < 8) return;
        final payload = data.sublist(8);
        if (payload.length >= 2 && payload[0] == 0xff && payload[1] == 0xd8) {
          buffer.clear();
          buffer.add(payload);
          collecting = true;
        } else if (collecting) {
          buffer.add(payload);
        }
        if (collecting && payload.contains(0xd9)) {
          final frame = buffer.toBytes();
          collecting = false;
          _broadcastFrame(frame);
        }
      }
    });
  }

  void _broadcastFrame(List<int> jpeg) {
    for (final ws in _clients) {
      if (ws.readyState == WebSocket.open) {
        ws.add(jpeg);
      }
    }
  }
}

Future<void> main(List<String> args) async {
  final server = CameraServer(camIp: '192.168.4.153', camPort: 8080);
  await server.start();
}
