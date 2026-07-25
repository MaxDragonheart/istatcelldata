# Documentazione

Le funzioni sviluppate consentono di gestire sia i dati che i geodati censuari nella loro
interezza. È possibile effettuare il download del dato e del geodato e successivamente processarlo.

## Il dato sulle celle censuarie negli anni

I dati censuari risultano differenti tra anno e anno non solo per il loro contenuto ma anche per la
struttura dati con cui sono stati condivisi da ISTAT.

In particolare gli anni 1991 e 2001 hanno una struttura dati simile, ma diversa da quella degli anni
2011 e 2021, che a loro volta sono simili tra loro.

Per il 2021 inoltre c'è un cambio completo della nomenclatura dei file e degli URL di download per
i soli dati.

## Codice Regione

A partire dalla versione `0.6.0` è possibile elaborare i dati non per forza per tutta l'Italia ma
anche solo per una o più regioni. La scelta della regione o delle regioni da elaborare va fatta
usando il codice della Regione di interesse.

| **Codice** | **Regione**                  |
|------------|------------------------------|
| 01         | Piemonte                     |
| 02         | Valle d'Aosta/Vallée d'Aoste |
| 03         | Lombardia                    |
| 04         | Trentino-Alto Adige/Südtirol |
| 05         | Veneto                       |
| 06         | Friuli-Venezia Giulia        |
| 07         | Liguria                      |
| 08         | Emilia-Romagna               |
| 09         | Toscana                      |
| 10         | Umbria                       |
| 11         | Marche                       |
| 12         | Lazio                        |
| 13         | Abruzzo                      |
| 14         | Molise                       |
| 15         | Campania                     |
| 16         | Puglia                       |
| 17         | Basilicata                   |
| 18         | Calabria                     |
| 19         | Sicilia                      |
| 20         | Sardegna                     |

La fonte della tabella precedente è [questa](https://www.istat.it/it/archivio/104317).

## Catalogo degli indicatori censuari

Il pacchetto espone un catalogo leggibile da codice per gli indicatori delle sezioni di censimento
ISTAT. Il catalogo sostituisce il precedente elenco statico dei campi condivisi con un unico
catalogo JSON incluso nel pacchetto, generato dai tracciati locali di 1991, 2001, 2011 e 2021 e
arricchito da una mappatura semantica curata per i campi confrontabili.

```python
from istat_census_data import (
    get_census_index_catalog,
    get_comparable_indexes,
    list_census_indexes,
)

codici_2021 = list_census_indexes(year=2021)
catalogo_2021 = get_census_index_catalog(year=2021)
indicatori_popolazione = get_comparable_indexes(
    years=[1991, 2001, 2011, 2021],
    strict=True,
)
```

`get_census_index_catalog()` restituisce una riga per ogni coppia `(year, source_code)` con questi
campi:

- `canonical_id`
- `year`
- `source_code`
- `label_it`
- `theme`
- `measure_type`
- `is_additive`
- `is_population_count`
- `comparable_group`
- `comparability_note`
- `source`

Usare `is_additive` per identificare le variabili di conteggio che possono essere considerate nei
workflow con pesatura areale. Identificativi, colonne testuali e campi sconosciuti sono marcati
come non additivi.

## Avvertenze sulla comparabilità

L'uguaglianza del codice non è sufficiente per confrontare gli indicatori tra anni. Per esempio,
`P18` mantiene lo stesso significato di classe di età della popolazione residente in tutti gli anni
supportati, quindi è mappato nel gruppo stabile `resident_population_age_20_24`.

Altri codici hanno cambiato significato. Nel tracciato locale 2021, da `P67` a `P82` sono classi di
età femminili. Nei tracciati locali più vecchi, lo stesso intervallo di codici indicava variabili
sul lavoro o sull'occupazione. Il catalogo quindi mappa quei campi 2021 semanticamente e non li
confronta usando solo il codice.

I campi sulle forze di lavoro come `P60`, `P61` e `P62` sono mappati per 1991, 2001 e 2011, ma
riportano `2021` in `missing_years` quando si richiede la comparabilità non stretta su tutti e
quattro gli anni.

Il censimento 2021 appartiene al sistema del censimento permanente e usa un processo di
geocodifica diverso dai censimenti tradizionali precedenti. I gruppi confrontabili devono quindi
essere letti come metadati documentati, non come prova che ogni dettaglio metodologico sia
identico.

ISTAT ha pubblicato anche dati 2023 per sezione, ma il pacchetto attualmente supporta solo 1991,
2001, 2011 e 2021. L'aggiunta del supporto 2023 è fuori dallo scope attuale del pacchetto.
