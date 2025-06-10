import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

/// Sends periodic keep-alive packets to the camera using the provided UDP socket.
///
/// The service does not own the [RawDatagramSocket]; it simply uses it to
/// transmit small payloads every second. Call [start] once a valid socket is
/// available and [stop] to cancel the timer when the socket should no longer be
/// used.
class KeepAliveService {
  KeepAliveService(this.socket, this.address);

  /// UDP socket shared with the stream receiver.
  final RawDatagramSocket socket;

  /// Target camera address.
  final InternetAddress address;

  Timer? _timer;

  /// Begin sending keep-alive messages to ports 8070 and 8080.
  void start() {
    _timer ??= Timer.periodic(const Duration(seconds: 1), (_) {
      socket.send(Uint8List.fromList([0x30, 0x66]), address, 8070);
      socket.send(Uint8List.fromList([0x42, 0x76]), address, 8080);
    });
  }

  /// Stop sending keep-alive packets.
  void stop() {
    _timer?.cancel();
    _timer = null;
  }
}
