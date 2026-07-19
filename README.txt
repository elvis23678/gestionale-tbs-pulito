TBS v5.0 - CATALOGO FOTO UNIFICATO

CONTENUTO
- app.py
- requirements.txt
- supplier_catalog_enriched.csv
- static/catalog/ (immagini estratte dal PDF fornitore)

RISULTATO DELL'ESTRAZIONE
- 3.267 referenze del listino importate
- 2.672 referenze associate automaticamente a una fotografia del PDF
- 595 referenze senza associazione fotografica automatica: restano nel catalogo con segnaposto e possono essere completate manualmente

NOVITA
- Boutique unica con prodotti in magazzino e articoli ordinabili
- Stato automatico:
  * quantità > 1: Disponibile
  * quantità = 1: Ultimo pezzo disponibile
  * quantità = 0 e codice presente nel catalogo: Ordinabile, 15-20 giorni
  * quantità = 0 e codice assente: Non disponibile
- Foto del catalogo fornitore usata automaticamente quando il prodotto non ha una foto propria
- Ricerca per codice, descrizione, misura, colore e pietra
- Modulo pubblico per richiedere articoli ordinabili
- Le richieste vengono registrate in Ordini catalogo
- Migrazione automatica del database esistente senza cancellare vendite, prodotti o utenti

DEPLOY
1. Conservare il backup della versione stabile.
2. Estrarre lo ZIP.
3. Caricare tutti i file e l'intera cartella static nella root del repository GitHub.
4. Attendere il deploy di Render.
5. Aprire la home della boutique e cercare il codice TA51208G-CL1608 per verificare foto e scheda.

IMPORTANTE
Non rinominare la cartella static/catalog e non caricare soltanto app.py: le immagini vengono lette da quella cartella.
Il raggruppamento automatico affidabile di colore/misura in un'unica scheda non è attivo in questa build: richiede una tabella di famiglie prodotto verificata, per evitare di unire modelli diversi. Questa versione completa prima l'integrazione foto e gli stati automatici.
