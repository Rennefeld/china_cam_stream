from dataclasses import dataclass, asdict
import json
import os


@dataclass
class Settings:
    cam_ip: str = "192.168.4.153"
    cam_port: int = 8080
    brightness: float = 1.0
    contrast: float = 1.0
    saturation: float = 1.0
    width: int = 640
    height: int = 480

    PATH = "settings.json"

    @classmethod
    def load(cls) -> "Settings":
        if os.path.exists(cls.PATH):
            with open(cls.PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(**data)
        inst = cls()
        inst.save()
        return inst

    def save(self) -> None:
        with open(self.PATH, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)
