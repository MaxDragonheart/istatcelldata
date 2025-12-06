# Documentation

The developed functions allow managing both census data and geodata in their entirety. You can download data and geodata and then process them.

## Census Cell Data Over the Years

Census data differs from year to year not only in content but especially in the data structure used by ISTAT itself.

In particular, the years 1991 and 2001 have the same data structure but different from that of the years 2011 and 2021, which are similar to each other.

For 2021, there is also a complete change in file nomenclature as well as download URLs for data only.

## Region Code
Starting from version `0.6.0`, it is possible to process data not necessarily for all of Italy but also for one or more regions, as the user chooses. The choice of region(s) to process is made using the code of the region of interest.

| **Code** | **Region**                   |
|----------|------------------------------|
| 01       | Piemonte                     |
| 02       | Valle d'Aosta/Vallée d'Aoste |
| 03       | Lombardia                    |
| 04       | Trentino-Alto Adige/Südtirol |
| 05       | Veneto                       |
| 06       | Friuli-Venezia Giulia        |
| 07       | Liguria                      |
| 08       | Emilia-Romagna               |
| 09       | Toscana                      |
| 10       | Umbria                       |
| 11       | Marche                       |
| 12       | Lazio                        |
| 13       | Abruzzo                      |
| 14       | Molise                       |
| 15       | Campania                     |
| 16       | Puglia                       |
| 17       | Basilicata                   |
| 18       | Calabria                     |
| 19       | Sicilia                      |
| 20       | Sardegna                     |

The source of the previous table is [this](https://www.istat.it/it/archivio/104317).


## Shared data
*[TO BE REVIEWED FOR 2021 DATA](https://github.com/MaxDragonheart/istatcelldata/issues/42)*

Analyzing the trace records of the 1991, 2001, and 2011 censuses revealed the presence of fields that have maintained their code. These fields are defined as `SHARED_DATA` and can be obtained by discarding those that have changed their code over the years. The shared fields are as follows:
```
SHARED_DATA = {
    'pop_tot': {
        'descrizione': 'Resident population - TOTAL',
        'codice': 'P1'
    },
    'pop_tot_m': {
        'descrizione': 'Resident population - Males',
        'codice': 'P2'
    },
    'pop_tot_f': {
        'descrizione': 'Resident population - Females',
        'codice': 'P3'
    },
    'pop_meno_5_anni': {
        'descrizione': 'Resident population - age < 5 years',
        'codice': 'P14'
    },
    'pop_5_9_anni': {
        'descrizione': 'Resident population - age 5 - 9 years',
        'codice': 'P15'
    },
    'pop_10_14_anni': {
        'descrizione': 'Resident population - age 10 - 14 years',
        'codice': 'P16'
    },
    'pop_15_19_anni': {
        'descrizione': 'Resident population - age 15 - 19 years',
        'codice': 'P17'
    },
    'pop_20_24_anni': {
        'descrizione': 'Resident population - age 20 - 24 years',
        'codice': 'P18'
    },
    'pop_25_29_anni': {
        'descrizione': 'Resident population - age 25 - 29 years',
        'codice': 'P19'
    },
    'pop_30_34_anni': {
        'descrizione': 'Resident population - age 30 - 34 years',
        'codice': 'P20'
    },
    'pop_35_39_anni': {
        'descrizione': 'Resident population - age 35 - 39 years',
        'codice': 'P21'
    },
    'pop_40_44_anni': {
        'descrizione': 'Resident population - age 40 - 44 years',
        'codice': 'P22'
    },
    'pop_45_49_anni': {
        'descrizione': 'Resident population - age 45 - 49 years',
        'codice': 'P23'
    },
    'pop_50_54_anni': {
        'descrizione': 'Resident population - age 50 - 54 years',
        'codice': 'P24'
    },
    'pop_55_59_anni': {
        'descrizione': 'Resident population - age 55 - 59 years',
        'codice': 'P25'
    },
    'pop_60_64_anni': {
        'descrizione': 'Resident population - age 60 - 64 years',
        'codice': 'P26'
    },
    'pop_65_69_anni': {
        'descrizione': 'Resident population - age 65 - 69 years',
        'codice': 'P27'
    },
    'pop_70_74_anni': {
        'descrizione': 'Resident population - age 70 - 74 years',
        'codice': 'P28'
    },
    'pop_maggiore_74_anni': {
        'descrizione': 'Resident population - age > 74 years',
        'codice': 'P29'
    },
    'pop_meno_5_anni_m': {
        'descrizione': 'Resident population - Males - age < 5 years',
        'codice': 'P30'
    },
    'pop_5_9_anni_m': {
        'descrizione': 'Resident population - Males - age 5 - 9 years',
        'codice': 'P31'
    },
    'pop_10_14_anni_m': {
        'descrizione': 'Resident population - Males - age 10 - 14 years',
        'codice': 'P32'
    },
    'pop_15_19_anni_m': {
        'descrizione': 'Resident population - Males - age 15 - 19 years',
        'codice': 'P33'
    },
    'pop_20_24_anni_m': {
        'descrizione': 'Resident population - Males - age 20 - 24 years',
        'codice': 'P34'
    },
    'pop_25_29_anni_m': {
        'descrizione': 'Resident population - Males - age 25 - 29 years',
        'codice': 'P35'
    },
    'pop_30_34_anni_m': {
        'descrizione': 'Resident population - Males - age 30 - 34 years',
        'codice': 'P36'
    },
    'pop_35_39_anni_m': {
        'descrizione': 'Resident population - Males - age 35 - 39 years',
        'codice': 'P37'
    },
    'pop_40_44_anni_m': {
        'descrizione': 'Resident population - Males - age 40 - 44 years',
        'codice': 'P38'
    },
    'pop_45_49_anni_m': {
        'descrizione': 'Resident population - Males - age 45 - 49 years',
        'codice': 'P39'
    },
    'pop_50_54_anni_m': {
        'descrizione': 'Resident population - Males - age 50 - 54 years',
        'codice': 'P40'
    },
    'pop_55_59_anni_m': {
        'descrizione': 'Resident population - Males - age 55 - 59 years',
        'codice': 'P41'
    },
    'pop_60_64_anni_m': {
        'descrizione': 'Resident population - Males - age 60 - 64 years',
        'codice': 'P42'
    },
    'pop_65_69_anni_m': {
        'descrizione': 'Resident population - Males - age 65 - 69 years',
        'codice': 'P43'
    },
    'pop_70_74_anni_m': {
        'descrizione': 'Resident population - Males - age 70 - 74 years',
        'codice': 'P44'
    },
    'pop_maggiore_74_anni_m': {
        'descrizione': 'Resident population - Males - age > 74 years',
        'codice': 'P45'
    },
    'lavoratori_tot': {
        'descrizione': 'Labor force - TOTAL',
        'codice': 'P60'
    },
    'lavoratori_occupati': {
        'descrizione': 'Labor force - Employed',
        'codice': 'P61'
    },
    'lavoratori_disoccupati': {
        'descrizione': 'Labor force - Unemployed and other job seekers',
        'codice': 'P62'
    },
    'famiglie_tot': {
        'descrizione': 'Total families',
        'codice': 'PF1'
    },
    'famiglie_componenti_tot': {
        'descrizione': 'Total family members',
        'codice': 'PF2'
    },
    'famiglie_1_componente': {
        'descrizione': 'Families with 1 member',
        'codice': 'PF3'
    },
    'famiglie_2_componenti': {
        'descrizione': 'Families with 2 members',
        'codice': 'PF4'
    },
    'famiglie_3_componenti': {
        'descrizione': 'Families with 3 members',
        'codice': 'PF5'
    },
    'famiglie_4_componenti': {
        'descrizione': 'Families with 4 members',
        'codice': 'PF6'
    },
    'famiglie_5_componenti': {
        'descrizione': 'Families with 5 members',
        'codice': 'PF7'
    },
    'famiglie_6_componenti_e_oltre': {
        'descrizione': 'Families with 6 or more members',
        'codice': 'PF8'
    },
    'famiglie_residenti_oltre_6_componenti': {
        'descrizione': 'Resident family members of families with 6 or more members',
        'codice': 'PF9'
    },
}
```
