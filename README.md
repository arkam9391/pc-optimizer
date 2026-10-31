# PC Optimizer

Aplikacja dla Windows 10/11 do przeglądu komputera: sterowniki z najnowszymi wersjami z Microsoft Update Catalog, dane techniczne podzespołów, dyski i foldery zajmujące miejsce, autostart, programy, pliki zbędne, ustawienia wpływające na wydajność. Skany tylko odczytują dane. Narzędzia systemowe uruchamiają się wyłącznie na żądanie i po potwierdzeniu.

## Instalacja

Pobierz `PCOptimizer-Setup-<wersja>.exe` z zakładki Releases i wybierz folder w kreatorze. Domyślnie instalacja jest per użytkownik (bez UAC).

## Aktualizacje

Po starcie program sprawdza w tle najnowsze wydanie w tym repozytorium. Gdy jest nowsze, w panelu bocznym pojawia się przycisk z numerem wersji. Instalacja rusza dopiero po potwierdzeniu, a instalator jest sprawdzany sumą SHA-256 z pliku `.sha256` dołączonego do wydania.

## Uruchomienie ze źródeł

```
pip install -r requirements.txt
python main.py
```

## Wydanie nowej wersji

1. Zmień `__version__` w `version.py`.
2. `powershell -File build.ps1` (wymaga PyInstaller i Inno Setup 6) tworzy `dist\PCOptimizer-Setup-<wersja>.exe` i `.sha256`.
3. `gh release create v<wersja> dist\PCOptimizer-Setup-<wersja>.exe dist\PCOptimizer-Setup-<wersja>.exe.sha256`
