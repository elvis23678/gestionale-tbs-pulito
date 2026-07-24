# TBS ONE v35.1.0 — Android Safe RC1

Questa release è progettata per essere caricata da GitHub usando solo Android.

## File da caricare sul branch `main-v2-clean`

- `app.py`
- `legacy.py`
- `requirements.txt`
- `README.md`

Tutti i file vanno nella radice del repository. Non sono necessarie cartelle nuove in questa prima fase.

## Perché è sicura

- `legacy.py` contiene l'applicazione completa esistente.
- `app.py` è soltanto il punto di avvio compatibile con `gunicorn app:app`.
- I percorsi delle immagini, del database e degli asset restano invariati perché `legacy.py` si trova nella radice.
- Non modifica il database.

## Test

Dopo il commit sul branch `main-v2-clean`, eseguire un deploy manuale sul servizio Render `tbs-one-dev` e verificare login, dashboard, cassa, catalogo, ordini e database.
