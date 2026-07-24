TBS ONE v35.1.0 - Structure Refactor

CARICAMENTO SU GITHUB
Caricare mantenendo esattamente questa struttura:

app.py
requirements.txt
templates/base.html
templates/login_base.html
static/css/tbs-one.css
static/js/tbs-one.js

Non caricare file .pyc o cartelle __pycache__.
Il database non viene incluso e non viene modificato dal refactor.

Questa release separa il layout condiviso e il CSS dal backend.
Le singole pagine interne restano temporaneamente generate dalle route esistenti, così le funzioni operative non vengono riscritte tutte insieme.
