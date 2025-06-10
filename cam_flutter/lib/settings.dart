import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

class Settings extends ChangeNotifier {
  String camIp;
  int camPort;
  int width;
  int height;
  bool grayscale;
  double brightness;
  bool flipHorizontal;
  bool flipVertical;

  Settings({
    required this.camIp,
    required this.camPort,
    required this.width,
    required this.height,
    this.grayscale = false,
    this.brightness = 1.0,
    this.flipHorizontal = false,
    this.flipVertical = false,
  });

  static const _camIpKey = 'camIp';
  static const _camPortKey = 'camPort';
  static const _widthKey = 'width';
  static const _heightKey = 'height';
  static const _grayKey = 'grayscale';
  static const _brightKey = 'brightness';
  static const _flipHKey = 'flipH';
  static const _flipVKey = 'flipV';

  static Future<Settings> load() async {
    final prefs = await SharedPreferences.getInstance();
    return Settings(
      camIp: prefs.getString(_camIpKey) ?? '192.168.4.153',
      camPort: prefs.getInt(_camPortKey) ?? 8080,
      width: prefs.getInt(_widthKey) ?? 640,
      height: prefs.getInt(_heightKey) ?? 480,
      grayscale: prefs.getBool(_grayKey) ?? false,
      brightness: prefs.getDouble(_brightKey) ?? 1.0,
      flipHorizontal: prefs.getBool(_flipHKey) ?? false,
      flipVertical: prefs.getBool(_flipVKey) ?? false,
    );
  }

  Future<void> _save() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_camIpKey, camIp);
    await prefs.setInt(_camPortKey, camPort);
    await prefs.setInt(_widthKey, width);
    await prefs.setInt(_heightKey, height);
    await prefs.setBool(_grayKey, grayscale);
    await prefs.setDouble(_brightKey, brightness);
    await prefs.setBool(_flipHKey, flipHorizontal);
    await prefs.setBool(_flipVKey, flipVertical);
  }

  void update({
    String? camIp,
    int? camPort,
    int? width,
    int? height,
    bool? grayscale,
    double? brightness,
    bool? flipHorizontal,
    bool? flipVertical,
  }) {
    this.camIp = camIp ?? this.camIp;
    this.camPort = camPort ?? this.camPort;
    this.width = width ?? this.width;
    this.height = height ?? this.height;
    this.grayscale = grayscale ?? this.grayscale;
    this.brightness = brightness ?? this.brightness;
    this.flipHorizontal = flipHorizontal ?? this.flipHorizontal;
    this.flipVertical = flipVertical ?? this.flipVertical;
    _save();
    notifyListeners();
  }
}
