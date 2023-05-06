# Documentazione

Le funzioni sviluppate consentono di gestire sia i dati che i geodati censuari nella loro interezza.
È possibile infatti effettuare il download del dato e del geodato e successivamente processarlo.

## Codice Regione
A partire dalla versione `0.6.0` è possibile elaborare i dati non per forza di tutta l'Italia ma anche solo di una o più 
regioni, l'utente può scegliere. La scelta della o delle regioni da elaborare va fatta usado il codice della Regione di 
interesse.

| **Codice** | **Regione**                  |
|------------|------------------------------|
| 01         | Piemonte                     |
| 02         | Valle d’Aosta/Vallée d’Aoste |
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


## Shared data
Analizzando i tracciati dei censimenti 1991, 2001 e 2011 si è evidenziata la presenza di campi che hanno mantenuto
il loro codice. Questi campi sono stati definiti `SHARED_DATA` ed è possibile ottenerli scartando quelli che
negli anni hanno cambiato codice. I campi condivisi sono i seguenti:
```
SHARED_DATA = {
    'pop_tot': {
        'descrizione': 'Popolazione residente - TOTALE',
        'codice': 'P1'
    },
    'pop_tot_m': {
        'descrizione': 'Popolazione residente - Maschi',
        'codice': 'P2'
    },
    'pop_tot_f': {
        'descrizione': 'Popolazione residente - Femmine',
        'codice': 'P3'
    },
    'pop_meno_5_anni': {
        'descrizione': 'Popolazione residente - età < 5 anni',
        'codice': 'P14'
    },
    'pop_5_9_anni': {
        'descrizione': 'Popolazione residente - età 5 - 9 anni',
        'codice': 'P15'
    },
    'pop_10_14_anni': {
        'descrizione': 'Popolazione residente - età 10 - 14 anni',
        'codice': 'P16'
    },
    'pop_15_19_anni': {
        'descrizione': 'Popolazione residente - età 15 - 19 anni',
        'codice': 'P17'
    },
    'pop_20_24_anni': {
        'descrizione': 'Popolazione residente - età 20 - 24 anni',
        'codice': 'P18'
    },
    'pop_25_29_anni': {
        'descrizione': 'Popolazione residente - età 25 - 29 anni',
        'codice': 'P19'
    },
    'pop_30_34_anni': {
        'descrizione': 'Popolazione residente - età 30 - 34 anni',
        'codice': 'P20'
    },
    'pop_35_39_anni': {
        'descrizione': 'Popolazione residente - età 35 - 39 anni',
        'codice': 'P21'
    },
    'pop_40_44_anni': {
        'descrizione': 'Popolazione residente - età 40 - 44 anni',
        'codice': 'P22'
    },
    'pop_45_49_anni': {
        'descrizione': 'Popolazione residente - età 15 - 19 anni',
        'codice': 'P23'
    },
    'pop_50_54_anni': {
        'descrizione': 'Popolazione residente - età 20 - 24 anni',
        'codice': 'P24'
    },
    'pop_55_59_anni': {
        'descrizione': 'Popolazione residente - età 25 - 29 anni',
        'codice': 'P25'
    },
    'pop_60_64_anni': {
        'descrizione': 'Popolazione residente - età 30 - 34 anni',
        'codice': 'P26'
    },
    'pop_65_69_anni': {
        'descrizione': 'Popolazione residente - età 35 - 39 anni',
        'codice': 'P27'
    },
    'pop_70_74_anni': {
        'descrizione': 'Popolazione residente - età 40 - 44 anni',
        'codice': 'P28'
    },
    'pop_maggiore_74_anni': {
        'descrizione': 'Popolazione residente - età > 74 anni',
        'codice': 'P29'
    },
    'pop_meno_5_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età < 5 anni',
        'codice': 'P30'
    },
    'pop_5_9_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età 5 - 9 anni',
        'codice': 'P31'
    },
    'pop_10_14_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età 10 - 14 anni',
        'codice': 'P32'
    },
    'pop_15_19_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età 15 - 19 anni',
        'codice': 'P33'
    },
    'pop_20_24_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età 20 - 24 anni',
        'codice': 'P34'
    },
    'pop_25_29_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età 25 - 29 anni',
        'codice': 'P35'
    },
    'pop_30_34_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età 30 - 34 anni',
        'codice': 'P36'
    },
    'pop_35_39_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età 35 - 39 anni',
        'codice': 'P37'
    },
    'pop_40_44_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età 40 - 44 anni',
        'codice': 'P38'
    },
    'pop_45_49_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età 15 - 19 anni',
        'codice': 'P39'
    },
    'pop_50_54_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età 20 - 24 anni',
        'codice': 'P40'
    },
    'pop_55_59_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età 25 - 29 anni',
        'codice': 'P41'
    },
    'pop_60_64_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età 30 - 34 anni',
        'codice': 'P42'
    },
    'pop_65_69_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età 35 - 39 anni',
        'codice': 'P43'
    },
    'pop_70_74_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età 40 - 44 anni',
        'codice': 'P44'
    },
    'pop_maggiore_74_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età > 74 anni',
        'codice': 'P45'
    },
    'lavoratori_tot': {
        'descrizione': 'Forze lavoro - TOTALE',
        'codice': 'P60'
    },
    'lavoratori_occupati': {
        'descrizione': 'Forze lavoro - Occupati',
        'codice': 'P61'
    },
    'lavoratori_disoccupati': {
        'descrizione': 'Forze lavoro - Disoccupati e altre persone in cerca di occupazione',
        'codice': 'P62'
    },
    'famiglie_tot': {
        'descrizione': 'Famiglie totale',
        'codice': 'PF1'
    },
    'famiglie_componenti_tot': {
        'descrizione': 'Totale componenti delle famiglie',
        'codice': 'PF2'
    },
    'famiglie_1_componente': {
        'descrizione': 'Famiglie 1 componente',
        'codice': 'PF3'
    },
    'famiglie_2_componenti': {
        'descrizione': 'Famiglie 2 componenti',
        'codice': 'PF4'
    },
    'famiglie_3_componenti': {
        'descrizione': 'Famiglie 3 componenti',
        'codice': 'PF5'
    },
    'famiglie_4_componenti': {
        'descrizione': 'Famiglie 4 componenti',
        'codice': 'PF6'
    },
    'famiglie_5_componenti': {
        'descrizione': 'Famiglie 5 componenti',
        'codice': 'PF7'
    },
    'famiglie_6_componenti_e_oltre': {
        'descrizione': 'Famiglie 6 e oltre componenti',
        'codice': 'PF8'
    },
    'famiglie_residenti_oltre_6_componenti': {
        'descrizione': 'Componenti delle famiglie residenti di 6 e oltre componenti',
        'codice': 'PF9'
    },
}
```