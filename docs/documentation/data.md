# Modulo Data

I dati censuari risultano essere differenti tra anno ed anno non solo per il loro contenuto ma anche per la struttura 
dati con cui sono stati condivisi da ISTAT.
In particolare gli anni 1991 e 2001 risultano avere una struttura dati uguale, mentre nel 2011 si ha una struttura 
totalmente differente. Per il 2021 invece c'è un totale cambio di nomenclatura dei file oltre che di url per il 
download dei soli dati.
Si è scelto dunque di normalizzare tutti dati secondo la struttura dati del 2011 perchè per questo anno abbiamo i dati 
censuari pubblicati come `csv`, [formato](https://en.wikipedia.org/wiki/Comma-separated_values#Data_exchange) file più adatto alla condivisione dei dati rispetto a `xls`.

## Anni 1991-2001

::: istatcelldata.data.census_1991_2001

## Anno 2011

::: istatcelldata.data.manage_data
