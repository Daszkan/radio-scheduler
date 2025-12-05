# RadioScheduler

RadioScheduler to aplikacja desktopowa do planowania i automatycznego odtwarzania internetowych stacji radiowych. Składa się z demona działającego w tle oraz interfejsu graficznego (GUI) do zarządzania.

![screenshot](https://i.imgur.com/your_screenshot.png) <!-- Placeholder for a screenshot -->

## Główne funkcje

*   **Graficzny interfejs użytkownika**: Intuicyjne zarządzanie stacjami, harmonogramem i ustawieniami.
*   **Demon działający w tle**: Zapewnia nieprzerwane odtwarzanie zgodnie z harmonogramem, nawet po zamknięciu GUI.
*   **Zaawansowany harmonogram**: Definiuj reguły odtwarzania dla konkretnych dni tygodnia i przedziałów czasowych.
*   **Przerwy na wiadomości**: Automatyczne przełączanie na stację informacyjną o określonych porach.
*   **Integracja z zasobnikiem systemowym (tray)**: Szybki dostęp do ulubionych stacji, kontrola głośności i statusu odtwarzania.
*   **Wsparcie dla wielu języków**: Interfejs dostępny w języku polskim i angielskim.
*   **Personalizacja**: Możliwość edycji skrótów klawiszowych.
*   **Import i eksport konfiguracji**: Łatwe tworzenie kopii zapasowych i przenoszenie ustawień.

## Wymagania

*   **Python 3.8+**
*   Biblioteki Pythona: `PySide6`, `PyYAML`
*   **Music Player Daemon (MPD)** oraz `mpc` (klient wiersza poleceń)

## Instalacja

1.  **Sklonuj repozytorium:**
    ```bash
    git clone https://github.com/Daszkan/radio-scheduler.git
    cd radio-scheduler
    ```

2.  **Zainstaluj zależności Pythona:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Zainstaluj MPD i MPC:**

    *   **Debian / Ubuntu:**
        ```bash
        sudo apt update && sudo apt install mpd mpc
        ```
    *   **Arch Linux:**
        ```bash
        sudo pacman -Syu mpd mpc
        ```
    *   **Fedora:**
        ```bash
        sudo dnf install mpd mpc
        ```

4.  **Skonfiguruj MPD:**
    Upewnij się, że masz podstawową konfigurację MPD w swoim katalogu domowym, np. w `~/.config/mpd/mpd.conf`. Aplikacja posiada wbudowany edytor tego pliku. MPD musi być uruchomiony, aby aplikacja działała poprawnie.
    ```bash
    mpd
    ```

## Użycie

Aby uruchomić interfejs graficzny, wykonaj polecenie w głównym katalogu projektu:

```bash
python radio-scheduler-gui.py
```

Demon harmonogramu (`radio-scheduler.py`) zostanie uruchomiony automatycznie w tle przy pierwszym starcie GUI.

## Konfiguracja

Wszystkie ustawienia aplikacji, w tym lista stacji i harmonogram, są przechowywane w pliku `~/.config/radio-scheduler/config.yaml`. Plik ten jest tworzony i zarządzany automatycznie przez interfejs graficzny.

## Licencja

Ten projekt jest udostępniany na licencji MIT. Zobacz plik LICENSE, aby uzyskać więcej informacji.