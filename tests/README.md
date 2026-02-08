# Tests Directory

Projenin birim testleri (Unit Tests) burada bulunur.

## Yapı
*   **`test_grades.py`**: Not parse etme mantığını test eder. HTML örnekleri (fixtures) kullanarak `parser.py` fonksiyonlarının doğru çalışıp çalışmadığını doğrular.
*   **`test_terms.py`**: Dönem listesi çekme ve parse etme testleri.

## Testleri Çalıştırma
Proje kök dizininde şu komutu çalıştırın:
```bash
python -m unittest discover tests
```
