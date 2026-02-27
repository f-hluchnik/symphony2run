# workflow

1. dowload data `python music_brainz_client.py --artist "<composer name>" --workers 5 --outdir ./output`
2. clean data, group child works `python mb_clean.py database/<composer_name>.csv --stat median --out database_clean/<composer>_clean.csv`
3. filter works with duration above 10 minutes `python mb_filter_durations.py database_clean/<composer>_clean.csv --min 10:00 --out database_clean_min10/<composer>_clean_min10.csv`

# artists
+ Ludwig van Beethoven
+ Johann Sebastian Bach
+ Wolfgang Amadeus Mozart
+ Antonio Vivaldi
+ George Frideric Handel
+ Joseph Haydn
+ Pyotr Ilyich Tchaikovsky
+ Antonín Dvořák
+ Richard Wagner
+ Philip Glass
+ Steve Reich
+ John Adams
+ Gustav Mahler
+ Anton Bruckner
