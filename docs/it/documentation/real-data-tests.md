# Test su dati reali su Ubuntu

I workflow su dati reali possono durare ore e usare molta memoria, soprattutto
le elaborazioni H3 su AOI grandi. Eseguili da un normale terminale Ubuntu e usa
un IDE solo come editor. I terminali integrati degli IDE sono comodi per
controlli brevi, ma un crash dell'IDE puo' interrompere un processo lungo o
nascondere l'ultimo output utile.

## Modalita' consigliata: tmux

Installa `tmux` una volta se non e' gia' disponibile:

```bash
sudo apt update
sudo apt install tmux procps coreutils
```

Avvia una sessione con nome:

```bash
tmux new -s h3-census
```

Spostati nella directory del progetto e lancia lo script su dati reali:

```bash
cd /path/to/istat-census-data
poetry run python scripts/run_h3_census_analysis.py
```

Nel layout locale usato dal maintainer del repository, la directory del progetto
di solito e':

```bash
cd /home/max/Desktop/DEV/PyProcess/istatcelldata_agentic/istat-census-data
```

Lo script configura gia' il proprio file di log. Se vuoi conservare anche tutto
lo stream del terminale in un log separato, usa `tee`:

```bash
poetry run python scripts/run_h3_census_analysis.py 2>&1 | tee -a /home/max/Desktop/census/logs/run_h3_census_analysis_tmux_$(date +%Y%m%dT%H%M%S).log
```

Scollegati dalla sessione senza fermare il processo:

```text
Ctrl-b
d
```

Rientra nella sessione:

```bash
tmux attach -t h3-census
```

Elenca le sessioni:

```bash
tmux ls
```

Se un output compare nel terminale ma non nel log timestamped del workflow,
identifica il pane e cattura lo scrollback prima di chiudere la sessione:

```bash
tmux list-panes -a -F '#{session_name}:#{window_index}.#{pane_index} #{pane_pid} #{pane_current_command} #{pane_current_path} #{pane_active}'
tmux capture-pane -p -S - -t h3-census:0.0 > /home/max/Desktop/census/logs/tmux_capture_$(date +%Y%m%dT%H%M%S).log
```

Sostituisci `h3-census:0.0` con il target restituito da `tmux list-panes` se il
run si trova in una sessione, finestra o pane diverso.

## Monitorare il run

Trova il PID da un altro terminale:

```bash
pgrep -af run_h3_census_analysis.py
```

Monitora il processo. `RSS` e' la memoria residente in KB:

```bash
ps -p <PID> -o pid,ppid,stat,etime,lstart,%cpu,%mem,rss,cmd
```

Monitora la memoria del sistema:

```bash
free -h
```

Monitora la dimensione della directory degli intermedi:

```bash
du -sh /home/max/Desktop/census/h3_intermediates
```

Segui il log H3 piu' recente:

```bash
tail -f "$(ls -t /home/max/Desktop/census/logs/run_h3_census_analysis_*.log | head -n 1)"
```

Segui un file di log noto:

```bash
tail -f /home/max/Desktop/census/logs/run_h3_census_analysis_YYYYMMDDTHHMMSS.log
```

## Impostazioni H3 per dati reali

Per AOI grandi, parti in modo conservativo:

- `workers = 1`
- `parallel_backend = DEFAULT_PARALLEL_BACKEND`
- `max_in_flight_chunks = None`
- `intermediate_storage = DEFAULT_INTERMEDIATE_STORAGE`
- `keep_intermediates = True`
- `retain_results = False`

Usa piu' worker solo dopo che un run conservativo ha dimostrato di avere margine
di memoria stabile. Mantieni `retain_results = False` nei run multi-anno, a meno
che il chiamante abbia davvero bisogno di conservare in memoria tutti i
GeoDataFrame annuali dopo la scrittura.

Con lo storage intermedio Parquet predefinito, `retain_results = False` fa
scrivere al workflow H3 end-to-end i `result_chunks/` finalizzati direttamente
nel GeoPackage. Il workflow non esegue una `pd.concat` globale di tutti i chunk
risultato prima di scrivere il layer; conserva comunque conteggi righe e tabelle
di validazione annuali nel risultato del workflow.

Non cancellare `h3_intermediates` finche' l'output finale non e' stato verificato.
Se un run si ferma dopo aver scritto i chunk, quegli intermedi sono la migliore
base per la diagnosi e possono permettere un rilancio piu' sicuro quando le
impostazioni non sono cambiate.

Imposta `reuse_intermediates = True` solo quando AOI, anno, selezione degli
indici, chunking, risoluzione H3, boundary ring e directory degli intermedi
appartengono allo stesso run previsto. In caso di dubbio, controlla prima i log.

## Verifiche di completamento

Un workflow H3 completato deve scrivere il path di output configurato, per
esempio:

```text
/home/max/Desktop/census/h3_census_analysis.gpkg
```

Il log deve includere anche il riepilogo finale emesso dallo script:

```text
H3 census workflow completed.
H3 output: /home/max/Desktop/census/h3_census_analysis.gpkg
```

Per i run H3 a chunk, un log che termina con una riga come questa indica che la
fase pesante dei chunk e' finita, ma non prova da sola che il GeoPackage finale
sia stato scritto:

```text
Completed H3 estimation chunk 1156/1156.
```

Se il processo non esiste piu', il file di output finale manca e il log non ha il
riepilogo di completamento workflow, considera il run interrotto prima
dell'export finale. Conserva gli intermedi e ispeziona le ultime righe del log
prima di rilanciare.

## Traceback degli errori e recupero dagli intermedi

Lo script editabile `scripts/run_h3_census_analysis.py` scrive le eccezioni
fatali ordinarie e le interruzioni dell'utente nel file di log ufficiale
timestamped con il traceback Python completo. Lo stesso errore puo' comparire
anche in `tmux` o su stderr. Se il log ufficiale si ferma prima del traceback
del terminale, cattura il pane tmux con `tmux capture-pane` prima di chiuderlo.

Se un run completa tutti i result chunk e poi fallisce durante la finalizzazione,
conserva la directory degli intermedi e riprova solo dopo aver verificato che le
impostazioni puntino ancora allo stesso AOI, anno, insieme di indici, chunk size,
risoluzione H3, boundary ring e directory degli intermedi.

Per il workflow con script editabile, di solito il recupero significa mantenere:

```python
keep_intermediates = True
intermediate_dir = main_path / "h3_intermediates"
```

e cambiare solo:

```python
reuse_intermediates = True
```

Il finalizzatore H3 con backend Parquet puo' riusare i result chunk conservati e,
per l'output a celle H3 intere (`clip_output = False`), ricostruire durante il
merge finale singole geometrie H3 non leggibili partendo da `h3_index`. Se
l'output ritagliato e' attivo e una geometria ritagliata non puo' essere
decodificata o riparata, il workflow fallisce con una diagnostica che indica path
del chunk, numero di riga, H3 index ed errore geometrico.

Quando i `result_chunks/` sono completi ma il processo viene terminato prima
dell'export, puoi finalizzare senza rifare la stima H3:

```bash
cd /path/to/istat-census-data
poetry run python scripts/finalize_h3_result_chunks.py \
  --intermediate-workspace /path/to/h3_intermediates/<fingerprint> \
  --output-path /path/to/h3_census_analysis.gpkg
```

Lo script legge `metadata.json`, `prepared_source.parquet` e
`result_chunks/result_chunk_*.parquet`, calcola le validazioni dei totali,
integerizza gli indicatori additivi a batch e scrive il layer GeoPackage in
append per chunk. Il layer di output predefinito e'
`h3_census<year>_r<h3_resolution>`; se il layer esiste gia', lo script fallisce
prima di scrivere per evitare duplicati.

Ogni layer annuale H3 tratta `h3_index` come chiave progettuale. Durante
l'export lo script rifiuta chunk con `h3_index` null o duplicati, crea un
`UNIQUE INDEX` GeoPackage su `h3_index`, e verifica che lo spatial index RTree
del layer sia presente. Anni diversi devono essere scritti in layer separati, non
nella stessa tabella.

## Alternative

Usa `screen` se `tmux` non e' disponibile:

```bash
screen -S h3-census
cd /path/to/istat-census-data
poetry run python scripts/run_h3_census_analysis.py
```

Scollegati da `screen` con `Ctrl-a`, poi `d`, e rientra con:

```bash
screen -r h3-census
```

Usa `nohup` solo quando non ti serve una sessione interattiva:

```bash
cd /path/to/istat-census-data
nohup poetry run python scripts/run_h3_census_analysis.py > /home/max/Desktop/census/logs/run_h3_census_analysis_nohup.log 2>&1 &
echo $!
```

`tmux` resta la modalita' preferita per i test su dati reali perche' mantiene il
run interattivo, osservabile e indipendente dal processo dell'IDE.
