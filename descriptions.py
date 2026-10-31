"""Opisy: za co odpowiada dany sterownik (dopasowanie po nazwie, potem po klasie urządzenia)."""
import re

BY_NAME = [
    (r"geforce|nvidia.*(gtx|rtx)|radeon", "Karta graficzna (GPU). Odpowiada za gry, wideo, grafikę 3D i przyspieszanie obrazu. Nowsze sterowniki poprawiają wydajność w grach i stabilność."),
    (r"intel.*(hd|uhd|iris).*graphics", "Zintegrowana grafika Intela. Wyświetla obraz na ekranie laptopa i na co dzień współpracuje z kartą NVIDIA (grafika hybrydowa)."),
    (r"high definition audio|realtek.*audio|audio", "Karta dźwiękowa. Odpowiada za głośniki, słuchawki i mikrofon."),
    (r"nvidia.*audio|hdmi|display audio", "Dźwięk przez HDMI/DisplayPort do monitora lub telewizora."),
    (r"wireless|wi-?fi|802\.11|wlan", "Karta Wi-Fi. Odpowiada za połączenie z siecią bezprzewodową."),
    (r"bluetooth", "Moduł Bluetooth. Łączy słuchawki, myszy, klawiatury i telefony."),
    (r"ethernet|gbe|family controller|lan\b", "Karta sieciowa przewodowa (Ethernet, kabel LAN)."),
    (r"management engine|\bmei\b|heci", "Intel Management Engine. Zarządza sprzętem na niskim poziomie (zasilanie, zdalne zarządzanie, bezpieczeństwo)."),
    (r"serial io|gpio|i2c|spi\b|uart", "Intel Serial IO. Obsługuje panel dotykowy, czujniki i drobne układy na płycie głównej."),
    (r"thermal|dptf|dynamic platform", "Zarządzanie temperaturą i wydajnością. Pilnuje, żeby laptop się nie przegrzewał."),
    (r"sata|ahci|rapid storage|nvme|storage controller", "Kontroler dysków. Odpowiada za komunikację płyty głównej z dyskami SSD i HDD."),
    (r"usb.*(3\.|xhci|extensible)|xhci", "Kontroler USB 3.x. Obsługuje porty USB, pendrive'y i urządzenia zewnętrzne."),
    (r"usb.*(root hub|hub)", "Koncentrator USB. Rozdziela porty USB na urządzenia."),
    (r"pci express root port|pci bridge|pci bus|lpc controller|smbus|pmc|shared sram|p2sb|isa bridge", "Element chipsetu płyty głównej. Łączy podzespoły (procesor, pamięć, dyski, porty). Zwykle nie wymaga ręcznej aktualizacji."),
    (r"chipset|watchdog|wdt", "Sterownik chipsetu. Zapewnia poprawną współpracę procesora z płytą główną i zasilaniem."),
    (r"camera|webcam|integrated camera|easycamera", "Kamera internetowa laptopa."),
    (r"touchpad|synaptics|elan|trackpad", "Panel dotykowy (touchpad). Obsługuje gesty i przewijanie."),
    (r"card reader|sd host|rts", "Czytnik kart pamięci SD."),
    (r"acpi|power controller|lenovo.*(system|power|vantage|interface)", "Zarządzanie zasilaniem i funkcjami producenta (klawisze funkcyjne, tryby zasilania, bateria)."),
    (r"battery|akumulator", "Bateria. Odczyt poziomu naładowania i zarządzanie ładowaniem."),
    (r"keyboard|klawiatur", "Klawiatura."),
    (r"mouse|mysz|hid-compliant", "Mysz lub urządzenie wskazujące."),
    (r"3dconnexion", "Mysz 3D (3Dconnexion). Sterowanie widokiem w programach CAD i 3D."),
    (r"emulator", "Wirtualne urządzenie wejścia (emulator). Zwykle pozostałość po sterowniku sprzętu 3D."),
]

BY_CLASS = {
    "DISPLAY": "Karta graficzna lub ekran. Odpowiada za obraz.",
    "NET": "Urządzenie sieciowe (Wi-Fi, Ethernet).",
    "MEDIA": "Urządzenie dźwiękowe lub multimedialne.",
    "SYSTEM": "Komponent systemowy lub chipsetu płyty głównej.",
    "BLUETOOTH": "Moduł Bluetooth.",
    "HDC": "Kontroler dysków.",
    "SCSIADAPTER": "Kontroler pamięci masowej (dyski, NVMe).",
    "USB": "Kontroler lub urządzenie USB.",
    "HIDCLASS": "Urządzenie wejścia (klawiatura, mysz, panel dotykowy).",
    "BIOS": "Oprogramowanie układowe (BIOS/UEFI).",
    "FIRMWARE": "Oprogramowanie układowe urządzenia.",
}


def describe(name: str, cls: str) -> str:
    n = (name or "").lower()
    for pat, text in BY_NAME:
        if re.search(pat, n):
            return text
    return BY_CLASS.get((cls or "").upper(), "Sterownik urządzenia systemowego.")
