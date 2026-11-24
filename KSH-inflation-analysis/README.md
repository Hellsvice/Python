# KSH-inflációelemzés (2010–2025)

Egyetemi Python-projekt a magyarországi fogyasztói árak éves változásának elemzésére. A program CSV-adatokat ellenőriz és dolgoz fel, leíró statisztikákat és lineáris regressziót számít, valamint három diagramot, szöveges összefoglalót és feldolgozott CSV-t készít.

## Futtatás

Python 3.10+ ajánlott.

```bash
python -m pip install -r requirements.txt
python ksh_inflacio_elemzes.py
```

A diagramablakok megjelenítéséhez: `python ksh_inflacio_elemzes.py --megnyitas`.

A `--adat` és `--kimenet` kapcsolókkal megadható a bemeneti CSV és a kimeneti mappa. A program a mellékelt 2010–2025-ös adatsorra készült.

## Adatforrás

[KSH STADAT – fogyasztóiár-indexek](https://www.ksh.hu/stadat_files/ara/hu/ara0002.html). A lineáris regresszió leíró elemzés, nem előrejelzés.
