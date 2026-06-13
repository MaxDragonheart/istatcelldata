# Pubblicazione Release

Le release PyPI vengono pubblicate da GitHub Actions con PyPI Trusted Publishing. Questo
evita token PyPI permanenti nella config locale di Poetry, nelle sessioni shell o nei
GitHub secrets.

## Configurazione PyPI Trusted Publisher

Prima della prima pubblicazione, crea su PyPI un pending Trusted Publisher che
corrisponda al workflow di rilascio del repository. Usa un environment GitHub protetto
per il passaggio di pubblicazione, così i maintainer possono approvare la release prima
dell'upload su PyPI.

I maintainer devono verificare progetto PyPI, repository, nome del workflow ed
environment esatti confrontandoli con il workflow di rilascio prima di pubblicare.

I pending publisher di PyPI creano il progetto alla prima pubblicazione riuscita. Non
riservano il nome del progetto prima di quella prima pubblicazione.

## Flusso GitHub Release

1. Verifica che `pyproject.toml` contenga la versione da pubblicare.
2. Verifica che il tag Git sia esattamente la versione oppure la versione preceduta da
   `v`, per esempio `1.5.0` o `v1.5.0`.
3. Crea e pubblica una GitHub Release per quel tag.
4. GitHub Actions esegue il workflow di rilascio.
5. Il workflow costruisce source distribution e wheel, li verifica con Twine e li
   pubblica su PyPI tramite l'environment GitHub protetto per la pubblicazione.

Il workflow fallisce se il tag della GitHub Release non corrisponde alla versione in
`pyproject.toml`.

## Script Locale Pre-Rilascio

`release.sh` è ora solo una verifica locale pre-rilascio. Controlla versione e tag,
installa le dipendenze, esegue opzionalmente i test e costruisce artifact locali in
`dist/`.

Non pubblica su PyPI e non effettua il deploy della documentazione.

```bash
./release.sh
RUN_TESTS=1 ./release.sh
```

Usa il flusso GitHub Release per il vero upload su PyPI.
