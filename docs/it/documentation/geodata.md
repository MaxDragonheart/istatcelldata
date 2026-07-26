# Modulo GeoData
Il modulo Geodata fornisce strumenti per la gestione e il preprocessing dei dati geografici, inclusi confini 
amministrativi e dati censuari. Le funzioni di questo modulo facilitano la lettura, il filtraggio e la conversione 
dei dati in formati utilizzabili per l'analisi geografica, come GeoDataFrame e GeoPackage.

Il codice nuovo dovrebbe importare da `istat_census_data`. Il riferimento qui sotto
è generato dal modulo di implementazione per mantenere visibile la documentazione
completa delle funzioni.

## Stime censuarie H3

Usa `estimate_h3_census_indexes()` dopo aver creato il file finale
`census_data.gpkg` con `finalize_census_data()`. Per impostazione predefinita la
funzione legge il layer `census<year>`, usa il catalogo censuario incluso nel
pacchetto per selezionare gli indicatori additivi presenti nel layer, genera le
celle H3 di livello 11 per l'AOI e distribuisce i valori delle sezioni censuarie sorgenti con
interpolazione pesata per area.

```python
from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

from istat_census_data import estimate_h3_census_indexes

aoi = gpd.GeoDataFrame(
    geometry=[box(12.0, 41.0, 12.2, 41.2)],
    crs="EPSG:4326",
)

h3_estimates = estimate_h3_census_indexes(
    census_data_path=Path("census_data.gpkg"),
    year=2021,
    aoi=aoi,
    h3_resolution=11,
    indexes=["P1", "P2"],
    workers=4,
    chunk_size=5000,
    output_path=Path("h3_census_2021.gpkg"),
)
```

Lo stimatore usa obbligatoriamente la risoluzione H3 11. L'argomento
`h3_resolution` puo essere omesso perché il livello 11 e il valore predefinito,
ma qualsiasi altro valore viene rifiutato.

Lo stesso workflow e disponibile come script di esempio modificabile in
`scripts/estimate_h3_census.py`. Imposta i valori di modulo come
`census_data_path`, `aoi_path`, `selected_year`, `selected_indexes`, `workers` e
`chunk_size`, poi esegui lo script. Usa `selected_indexes = []` per stimare tutti
gli indicatori additivi del catalogo presenti nel layer sorgente.

## Esecuzione parallela e benchmark

La stima H3 e seriale per impostazione predefinita: `workers=1`. Per AOI piu
grandi puoi impostare `workers` a un valore maggiore di 1 e scegliere un
`chunk_size` per dividere la griglia H3 in chunk deterministici. Ogni cella H3 e
elaborata da un solo chunk, quindi i risultati paralleli contengono le stesse
celle del percorso seriale e devono corrispondere ai totali seriali entro la
tolleranza dello stimatore.

```python
h3_estimates = estimate_h3_census_indexes(
    census_data_path=Path("census_data.gpkg"),
    year=2021,
    aoi=aoi,
    indexes=["P1", "P2"],
    workers=4,
    chunk_size=5000,
)
```

Il valore predefinito `parallel_backend="thread"` condivide i GeoDataFrame
preparati tra i worker ed evita di copiare un layer sorgente grande in piu
processi. Usa `parallel_backend="process"` solo dopo un benchmark sulla tua
macchina: puo aiutare negli overlay dominati dalla CPU, ma serializza i
GeoDataFrame e di solito richiede piu memoria.

Usa il backend opzionale Dask quando vuoi che Dask pianifichi localmente gli stessi
chunk H3 deterministici:

```bash
pip install "istat-census-data[dask]"
```

```python
h3_estimates = estimate_h3_census_indexes(
    census_data_path=Path("census_data.gpkg"),
    year=2021,
    aoi=aoi,
    indexes=["P1", "P2"],
    workers=4,
    chunk_size=5000,
    parallel_backend="dask",
)
```

Il backend Dask usa attualmente lo scheduler locale a thread di Dask. E un percorso
runtime opzionale, non una dipendenza richiesta per le installazioni normali del
pacchetto.

Inizia con `workers` non superiore ai core fisici disponibili per il processo.
Per H3 livello 11, valori di `chunk_size` tra 2.000 e 10.000 celle sono un primo
intervallo pratico. Chunk piu piccoli danno aggiornamenti di avanzamento piu
frequenti ma aumentano l'overhead; chunk piu grandi riducono l'overhead ma
possono lasciare worker inattivi verso la fine dell'elaborazione.

Usa `scripts/benchmark_h3_estimation.py` su dati gia finalizzati per confrontare
le impostazioni prima di eseguire una grande AOI di produzione. Modifica
`worker_counts`, `chunk_sizes`, `parallel_backend` e `runs` nello script. Mantieni
`selected_indexes = []` quando vuoi stimare tutti gli indicatori additivi presenti
nel layer sorgente.

L'output del benchmark riporta secondi trascorsi, numero di celle H3 e stato
della validazione dei totali per ogni combinazione worker/chunk. Usa i tempi di
AOI piccole come controllo di correttezza e overhead; AOI medie o grandi sono piu
utili per decidere se l'esecuzione parallela conviene davvero.

## Workflow H3 end-to-end

Usa `run_h3_census_workflow()` o `scripts/run_h3_census_analysis.py` quando vuoi
che gli anni censuari scelti guidino l'intera pipeline. Il workflow scarica solo
gli anni richiesti, li preprocessa, finalizza `census_data.gpkg` e poi scrive un
layer H3 di livello 11 per ogni anno.

Lo script di esempio modificabile `scripts/run_h3_census_analysis.py` espone lo
stesso workflow con valori di modulo. Imposta `list_year`, `main_path`,
`aoi_path`, `list_region`, `municipalities_code` e i controlli di performance
nello script. Usa `selected_indexes = []` per stimare tutti gli indicatori
additivi disponibili in ogni anno selezionato. Il livello H3 e fisso a 11 e la
policy sulle sezioni speciali/fittizie ha valore predefinito `exclude`.

Il workflow end-to-end espone gli stessi controlli di performance di PRP-012
disponibili nello stimatore su dati finalizzati. Modifica `workers`,
`chunk_size` e `parallel_backend` nello script per tarare elaborazioni grandi.
Dopo aver installato `istat-census-data[dask]`, imposta
`parallel_backend = "dask"` per usare il backend Dask locale opzionale.

Se i dati esistono gia, salta gli stadi completati impostando `run_download`,
`run_preprocess` o `run_finalize` a `False` nello script.

Quando usi `--skip-finalize`, `<data-dir>/census_data.gpkg` deve gia esistere.

Lo stesso processo e disponibile da Python:

```python
from pathlib import Path

import geopandas as gpd

from istat_census_data import run_h3_census_workflow

aoi = gpd.read_file("aoi.gpkg", layer="aoi")

result = run_h3_census_workflow(
    years=[2021],
    data_folder=Path("./census"),
    aoi=aoi,
    indexes=["P1", "P2"],
    municipality_codes=[58091],
    workers=4,
    chunk_size=5000,
    parallel_backend="thread",
)

print(result.output_path)
print(result.layers)
```

Il metodo assume densita uniforme dentro ogni sezione censuaria sorgente. Questa
scelta e trasparente e conserva i totali additivi rispetto al totale delle celle
sorgenti tagliate sull'AOI, ma non e un modello dasimetrico e non va interpretata
come localizzazione esatta a livello di edificio o famiglia.

## Sezioni censuarie speciali e fittizie

`estimate_h3_census_indexes()` segnala le sezioni censuarie sorgenti il cui codice
contiene uno di questi marker:

| Marker | Significato | Dati consegnati in quelle righe | Interpretazione H3 |
|---|---|---|---|
| `888888` | Sezioni fittizie per persone senza alloggio o senza fissa dimora iscritte in anagrafe. ISTAT documenta anche l'uso per persone iscritte tramite associazioni o strutture di accoglienza. | Le righe possono contenere le stesse variabili dei file censuari a livello di sezione. Per queste sezioni gli indicatori di popolazione e persona/famiglia possono essere significativi, mentre gli indicatori su abitazioni o edifici non vanno letti come condizioni fisiche del poligono disegnato. | La geometria e convenzionale. ISTAT indica che queste sezioni sono disegnate in aree disabitate, preferibilmente vicino alla casa comunale. Le densita H3 su quel poligono sono quindi un meccanismo di allocazione, non una stima della localizzazione residenziale. |
| `999999` | Sezioni fittizie collegate a zone in contestazione rivendicate da due o piu comuni. | Le righe possono contenere individui residenti nel comune a cui la zona contestata non e assegnata ai fini censuari. Quando presenti nel layer finale, passano comunque attraverso il normale tracciato delle variabili a sezione. | Tratta il risultato come allocazione amministrativa. Non interpretare la cella H3 come localizzazione precisa della residenza se la geometria della zona contestata non e appropriata per l'analisi. |
| `7777777` | Sezioni fittizie presenti solo nei dati 2011 dell'Abruzzo per comuni colpiti dal sisma dell'aprile 2009. | ISTAT documenta queste sezioni per collocare le famiglie che alla data del censimento erano temporaneamente domiciliate in un comune diverso da quello di iscrizione anagrafica. Gli indicatori additivi di popolazione/famiglia possono quindi essere presenti, ma la geometria non e una normale geografia di residenza. | Usa cautela in mappe di densita e overlay locali: le righe conservano la contabilita censuaria, ma la geometria codifica una convenzione amministrativa post-sisma. |

Questi marker non sono trattati come dati mancanti, ma la stima H3 li esclude per
impostazione predefinita perché le loro geometrie convenzionali possono produrre
densita locali fuorvianti. Con `special_section_policy="exclude"`, lo stimatore
rimuove queste righe sorgenti prima dell'overlay pesato per area; i totali del
risultato quindi escludono quei record.

Usa `special_section_policy="include"` solo quando devi conservare l'intera
contabilita censuaria dentro l'AOI e accetti che poligoni convenzionali possano
ricevere persone che non sono fisicamente distribuite in quel luogo. In questa
modalita, lo stimatore include i loro valori nell'overlay pesato per area e imposta
`intersects_special_section=True` per ogni cella H3 che riceve area da una di
queste sezioni.

Usa una policy piu restrittiva quando questa convenzione non e accettabile:

```python
h3_estimates = estimate_h3_census_indexes(
    census_data_path=Path("census_data.gpkg"),
    year=2021,
    aoi=aoi,
    indexes=["P1"],
    special_section_policy="raise",
)
```

- `exclude`: valore predefinito per i processi H3; rimuove queste righe sorgenti
  prima della stima, quindi i totali le escludono.
- `include`: mantiene le righe e segnala le celle H3 interessate.
- `raise`: interrompe l'elaborazione con errore se una sezione speciale o fittizia
  interseca l'AOI.

Puoi ispezionare le celle H3 segnalate con:

```python
flagged_cells = h3_estimates[h3_estimates["intersects_special_section"]]
```

Lo script di esempio espone la stessa policy tramite l'argomento
`special_section_policy` passato a `run()`.

Fonti: ISTAT documenta `888888x` e `999999x` in
[Dati per sezioni di censimento](https://www.istat.it/notizia/dati-per-sezioni-di-censimento/).
ISTAT documenta zone in contestazione, sezioni per persone senza dimora e la
convenzione `7777777` del 2011 in Abruzzo in
[Basi territoriali: anni 1991, 2001, 2011 e 2021](https://www.istat.it/wp-content/uploads/2024/07/Descrizione-dei-dati-Basi-territoriali.pdf).

::: istat_census_data.geodata

::: istat_census_data.h3_estimation
