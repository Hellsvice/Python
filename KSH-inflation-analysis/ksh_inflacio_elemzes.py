import argparse
import csv
from pathlib import Path
from statistics import mean, median, stdev

import matplotlib.pyplot as plt


# A CSV-fejlécek és a diagramon megjelenő magyar címkék összerendelése.
KATEGORIAK = {
    "osszesen_index": "Összes fogyasztói ár",
    "elelmiszerek_index": "Élelmiszerek",
    "haztartasi_energia_index": "Háztartási energia",
    "szolgaltatasok_index": "Szolgáltatások",
}
FORRAS_URL = "https://www.ksh.hu/stadat_files/ara/hu/ara0002.html"
ALAPMAPPA = Path(__file__).resolve().parent


def adatok_beolvasasa(csv_utvonal):
    #sorok beolvasása
    rekordok = []
    with Path(csv_utvonal).open("r", encoding="utf-8-sig", newline="") as fajl:
        olvaso = csv.DictReader(fajl, delimiter=";")
        szukseges = {"ev", *KATEGORIAK}
        if not olvaso.fieldnames or not szukseges.issubset(olvaso.fieldnames):
            raise ValueError("A CSV fejlécében hiányzik egy szükséges oszlop.")

        for sor_szam, sor in enumerate(olvaso, start=2):
            try:
                ev = int(sor["ev"])
                indexek = {kulcs: float(sor[kulcs].replace(",", "."))
                           for kulcs in KATEGORIAK}
            except (ValueError, TypeError, AttributeError) as hiba:
                raise ValueError(f"Hibás érték a CSV {sor_szam}. sorában.") from hiba
            if not 1900 <= ev <= 2100 or any(ertek <= 0 for ertek in indexek.values()):
                raise ValueError(f"Érvénytelen év vagy árindex: {sor_szam}. sor.")
            inflacio = {kulcs: index - 100 for kulcs, index in indexek.items()}
            rekordok.append({"ev": ev, "indexek": indexek, "inflacio": inflacio})

    rekordok.sort(key=lambda rekord: rekord["ev"])
    evek = [rekord["ev"] for rekord in rekordok]
    if len(rekordok) < 3:
        raise ValueError("A statisztikához legalább 3 éves adatsor kell.")
    if len(evek) != len(set(evek)):
        raise ValueError("A CSV azonos éveket többször tartalmaz.")
    if any(kovetkezo - elozo != 1 for elozo, kovetkezo in zip(evek, evek[1:])):
        raise ValueError("Az adatsorban hiányzó évek vannak.")
    return rekordok


def leiro_statisztika(ertekek):
    #Alap leíró statisztika egy százalékos idősorra.
    return {
        "atlag": mean(ertekek),
        "median": median(ertekek),
        "minimum": min(ertekek),
        "maximum": max(ertekek),
        "szoras": stdev(ertekek),  # mintaszórás
    }


def linearis_regresszio(x_adatok, y_adatok):
    #Legkisebb négyzetek módszere: y ≈ meredekseg*x + tengelymetszet.

    if len(x_adatok) != len(y_adatok) or len(x_adatok) < 3:
        raise ValueError("A regresszióhoz legalább 3 illeszkedő pont szükséges.")
    x_atlag = mean(x_adatok)
    y_atlag = mean(y_adatok)
    szamlalo = sum((x - x_atlag) * (y - y_atlag)
                   for x, y in zip(x_adatok, y_adatok))
    nevezo = sum((x - x_atlag) ** 2 for x in x_adatok)
    if nevezo == 0:
        raise ValueError("Az összes x érték azonos, nem lehet regressziót számolni.")
    meredekseg = szamlalo / nevezo
    tengelymetszet = y_atlag - meredekseg * x_atlag
    becsult = [meredekseg * x + tengelymetszet for x in x_adatok]
    teljes_negyzetosszeg = sum((y - y_atlag) ** 2 for y in y_adatok)
    hiba_negyzetosszeg = sum((y - y_becsult) ** 2
                            for y, y_becsult in zip(y_adatok, becsult))
    r_negyzet = (1 - hiba_negyzetosszeg / teljes_negyzetosszeg
                if teljes_negyzetosszeg > 0 else 1.0)
    return meredekseg, tengelymetszet, r_negyzet


def halmozott_aremeles(indexek):
    #Több év összetett árváltozása (%), nem az éves ráták összege.
    szorzo = 1.0
    for index in indexek:
        szorzo *= index / 100.0
    return (szorzo - 1.0) * 100.0


def abra_beallitas():
    #Egységes, jól olvasható diagrambeállítások.
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titlesize": 15,
        "axes.titleweight": "bold",
        "axes.labelsize": 11,
        "figure.dpi": 120,
        "savefig.dpi": 180,
    })


def vonaldiagram(rekordok, celmappa):
    #A négy árindexből számolt éves infláció idősoros vonaldiagramja.
    evek = [rekord["ev"] for rekord in rekordok]
    szinek = ["#144FA1", "#DA6A2C", "#2E8B75", "#8A59A8"]
    fig, ax = plt.subplots(figsize=(12.4, 6.4), layout="constrained")
    for (kulcs, nev), szin in zip(KATEGORIAK.items(), szinek):
        ertekek = [rekord["inflacio"][kulcs] for rekord in rekordok]
        ax.plot(evek, ertekek, label=nev, color=szin,
                linewidth=2.6 if kulcs == "osszesen_index" else 1.8,
                marker="o", markersize=4)
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_title("Fogyasztói árak éves változása Magyarországon, 2010–2025")
    ax.set_xlabel("Év")
    ax.set_ylabel("Árváltozás az előző évhez képest (%)")
    ax.set_xticks(evek[::2])
    ax.grid(alpha=0.19)
    ax.legend(ncols=2, loc="upper left", frameon=False)
    fig.text(0.01, -0.015, "Forrás: KSH STADAT 1.1.1.2  •  saját számítás, előző év = 100", fontsize=9)
    fig.savefig(celmappa / "01_vonaldiagram_inflacio.png", bbox_inches="tight")
    return fig


def pontdiagram_regresszioval(rekordok, celmappa):
    #Éves inflációs pontok és lineáris regressziós trendvonal.
    evek = [rekord["ev"] for rekord in rekordok]
    x = [ev - evek[0] for ev in evek]  # olvasható regressziós egyenlet
    y = [rekord["inflacio"]["osszesen_index"] for rekord in rekordok]
    meredekseg, tengelymetszet, r2 = linearis_regresszio(x, y)
    trend = [meredekseg * xi + tengelymetszet for xi in x]
    fig, ax = plt.subplots(figsize=(11.4, 6.1), layout="constrained")
    ax.scatter(evek, y, s=75, color="#245B9A", alpha=0.88,
               edgecolor="white", linewidth=1.0, label="KSH éves megfigyelés", zorder=3)
    ax.plot(evek, trend, linewidth=2.5, color="#D97732",
            label="Legkisebb négyzetes lineáris regresszió", zorder=2)
    for ev in (2022, 2023):
        if ev in evek:
            j = evek.index(ev)
            ax.annotate(f"{ev}: {y[j]:.1f}%", (ev, y[j]),
                        textcoords="offset points", xytext=(6, 12), fontsize=10)
    ax.set_title("Éves összesített infláció és a lineáris regresszió")
    ax.set_xlabel("Év")
    ax.set_ylabel("Éves infláció (%)")
    ax.set_xticks(evek[::2])
    ax.grid(alpha=0.18)
    ax.legend(loc="upper left", frameon=False)
    ax.text(0.02, 0.84,
            f"Becsült érték = {tengelymetszet:.2f} + {meredekseg:.2f} × (év − {evek[0]})\nR² = {r2:.3f}",
            transform=ax.transAxes, va="top", fontsize=10,
            bbox={"facecolor": "white", "edgecolor": "#dddddd", "alpha": 0.95, "pad": 9})
    fig.text(0.01, -0.015,
             "Forrás: KSH STADAT 1.1.1.2  •  Leíró trend, nem infláció-előrejelzés.", fontsize=9)
    fig.savefig(celmappa / "02_pontdiagram_regresszio.png", bbox_inches="tight")
    return fig, (meredekseg, tengelymetszet, r2)


def kumulalt_diagram(rekordok, celmappa):
    #2021=100 árszint-bázison a 2022–2025 közti kumulált drágulás.
    valasztott = [rekord for rekord in rekordok if rekord["ev"] >= 2022]
    evek = [2021] + [rekord["ev"] for rekord in valasztott]
    fig, ax = plt.subplots(figsize=(11.4, 6.2), layout="constrained")
    for kulcs, szin in (("osszesen_index", "#144FA1"),
                       ("elelmiszerek_index", "#DA6A2C")):
        szint = 100.0
        ertekek = [szint]
        for rekord in valasztott:
            szint *= rekord["indexek"][kulcs] / 100.0
            ertekek.append(szint)
        ax.plot(evek, ertekek, color=szin, linewidth=2.8, marker="o",
                label=KATEGORIAK[kulcs])
        ax.annotate(f"{ertekek[-1]:.1f}", (evek[-1], ertekek[-1]),
                    textcoords="offset points", xytext=(8, 1), color=szin)
    ax.set_xlim(2020.8, 2025.40)  # legyen hely a jobb oldali értékcímkéknek
    ax.set_title("Az infláció összeadódó hatása: 2021 = 100")
    ax.set_ylabel("Árszintindex, 2021 = 100")
    ax.set_xlabel("Év")
    ax.set_xticks(evek)
    ax.grid(alpha=0.18)
    ax.legend(frameon=False, loc="upper left")
    fig.text(0.01, -0.015,
             "Forrás: KSH STADAT 1.1.1.2  •  láncolt éves árindexekből számítva.", fontsize=9)
    fig.savefig(celmappa / "03_kumulalt_arszint_2021_bazis.png", bbox_inches="tight")
    return fig


def eredmenyek_szovege(rekordok, regresszio):
    #Közérthető kimutatás és módszertani korlátok.
    evek = [r["ev"] for r in rekordok]
    m, b, r2 = regresszio
    sorok = [
        "KSH-INFLÁCIÓELEMZÉS | PROGRAMOZÁSI ALAPOK",
        "=" * 57,
        f"Vizsgált időszak: {evek[0]}–{evek[-1]} ({len(evek)} év)",
        "Adatforrás: KSH STADAT, 1.1.1.2; az előző év = 100,0%.",
        FORRAS_URL,
        "Átváltás: éves infláció (%) = KSH árindex − 100.",
        "",
        "LEÍRÓ STATISZTIKA – ÉVES ÁRVÁLTOZÁS (%)",
    ]
    for kulcs, nev in KATEGORIAK.items():
        ertekek = [r["inflacio"][kulcs] for r in rekordok]
        st = leiro_statisztika(ertekek)
        min_ev = evek[ertekek.index(st["minimum"])]
        max_ev = evek[ertekek.index(st["maximum"])]
        sorok.extend([
            f"\n{nev}:",
            f"  Átlag: {st['atlag']:.2f}%  |  Medián: {st['median']:.2f}%  |  Mintaszórás: {st['szoras']:.2f} százalékpont",
            f"  Minimum: {st['minimum']:.1f}% ({min_ev})  |  Maximum: {st['maximum']:.1f}% ({max_ev})",
        ])
    ertekek = [r["inflacio"]["osszesen_index"] for r in rekordok]
    indexek_2022 = [r for r in rekordok if 2022 <= r["ev"] <= 2025]
    osszes_kum = halmozott_aremeles([r["indexek"]["osszesen_index"] for r in indexek_2022])
    etel_kum = halmozott_aremeles([r["indexek"]["elelmiszerek_index"] for r in indexek_2022])
    sorok.extend([
        "",
        "REGRESSZIÓ – ÉV ÉS ÖSSZESÍTETT ÉVES INFLÁCIÓ",
        f"Becsült infláció (%) = {b:.3f} + {m:.3f} × (év − {evek[0]})",
        f"Meredekség: {m:.3f} százalékpont/év; R²: {r2:.4f}",
        "A regresszió leíró közelítés, nem alkalmas megbízható előrejelzésre.",
        "A kiugró 2022–2023-as évek a teljes időszakra illesztett trendet jelentősen befolyásolják.",
        "",
        "GAZDASÁGI KÖVETKEZTETÉSEK",
        f"1. 2022-ben az éves infláció {ertekek[evek.index(2022)]:.1f}%, 2023-ban {ertekek[evek.index(2023)]:.1f}% volt.",
        f"2. 2024-ben {ertekek[evek.index(2024)]:.1f}%, 2025-ben {ertekek[evek.index(2025)]:.1f}% volt az infláció.",
        "   A kisebb pozitív infláció az áremelkedés lassulása, nem általános árcsökkenés.",
        f"3. 2021-hez képest 2025-re az összesített árszint a láncolt index alapján {osszes_kum:.1f}%-kal,",
        f"   az élelmiszerek árszintje {etel_kum:.1f}%-kal emelkedett (2022–2025 indexei alapján).",
        "4. Az élelmiszerárak gyorsabb növekedése az élelmiszerre nagyobb arányban költő",
        "   háztartásokat erősebben érintheti; az egyéni hatás a fogyasztási kosártól függ.",
        "",
        "MÓDSZERTANI KORLÁTOK",
        "- Éves átlagos árváltozásokat elemzünk, nem havi inflációt.",
        "- A főcsoportok indexe nem adható egyszerűen össze az összes indexévé:",
        "  a hivatalos összesített mutató fogyasztási súlyokkal készül.",
        "- A regresszió összefüggést ír le, okságot nem bizonyít.",
        "- A múltbeli lineáris trend nem jelzi megbízhatóan a jövőbeli inflációt.",
        "",
        "ÁBRÁK",
        "01_vonaldiagram_inflacio.png – éves változások",
        "02_pontdiagram_regresszio.png – pontok és lineáris regresszió",
        "03_kumulalt_arszint_2021_bazis.png – árszintváltozás 2021-hez képest",
    ])
    return "\n".join(sorok) + "\n"


def feldolgozott_csv_mentese(rekordok, utvonal):
    #A számított inflációs százalékok mentése új, strukturált CSV-be.
    with utvonal.open("w", encoding="utf-8-sig", newline="") as fajl:
        iro = csv.writer(fajl, delimiter=";")
        iro.writerow(["ev", "osszesen_pct", "elelmiszerek_pct",
                      "haztartasi_energia_pct", "szolgaltatasok_pct"])
        for rekord in rekordok:
            iro.writerow([rekord["ev"]] + [f"{rekord['inflacio'][kulcs]:.1f}"
                      for kulcs in KATEGORIAK])


def main():
    parser = argparse.ArgumentParser(description="KSH fogyasztóiár-index elemzése")
    parser.add_argument("--adat", type=Path,
                        default=ALAPMAPPA / "ksh_inflacio_2010_2025.csv",
                        help="Átstrukturált KSH-adatfájl útvonala")
    parser.add_argument("--kimenet", type=Path, default=ALAPMAPPA,
                        help="Eredmények célmappája")
    parser.add_argument("--megnyitas", action="store_true",
                        help="Diagramablakok megnyitása a mentés után")
    args = parser.parse_args()

    rekordok = adatok_beolvasasa(args.adat)
    args.kimenet.mkdir(parents=True, exist_ok=True)
    diagram_mappa = args.kimenet / "diagramok"
    diagram_mappa.mkdir(exist_ok=True)
    abra_beallitas()
    abrak = [vonaldiagram(rekordok, diagram_mappa)]
    pontabra, regres = pontdiagram_regresszioval(rekordok, diagram_mappa)
    abrak.append(pontabra)
    abrak.append(kumulalt_diagram(rekordok, diagram_mappa))

    eredmenyek = eredmenyek_szovege(rekordok, regres)
    (args.kimenet / "eredmenyek.txt").write_text(eredmenyek, encoding="utf-8")
    feldolgozott_csv_mentese(rekordok, args.kimenet / "feldolgozott_inflacio.csv")
    print(eredmenyek)
    print(f"A 3 diagram és az eredmények elmentve ide: {args.kimenet}")

    if args.megnyitas:
        plt.show()
    else:
        for abra in abrak:
            plt.close(abra)

    print("A program lefutott")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, csv.Error) as hiba:
        print(f"HIBA: {hiba}")
        raise SystemExit(1) from hiba
