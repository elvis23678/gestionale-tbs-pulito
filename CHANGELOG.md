# TBS Gestionale — Changelog

## v35.1.0 LTS · Notification Center

Base: v35.0.2 ENTERPRISE con correzioni di stabilità della v35.0.3.

### Consolidato
- Centro notifiche personale con campanella e contatore.
- Notifiche non lette, lette e archiviate.
- Dettaglio delle notifiche di vendita e autorizzazione sconto.
- Raggruppamento delle notifiche di vendita.
- Aggiornamento automatico del contatore.
- Notifiche separate per Admin, Gestore e Venditore.
- Motore di richiesta, approvazione e rifiuto degli sconti già integrato.

### Correzioni
- Nessun redirect circolare tra Home, Dashboard e Cassa.
- Venditore indirizzato alla Cassa; Admin e Gestore alla Dashboard.
- Messaggi di permesso duplicati eliminati con `flash_once`.
- Le richieste API/AJAX ricevono 401/403 JSON senza redirect HTML.
- Redirect POST/GET effettuati con codice HTTP 303.

### Compatibilità
- Render
- Chrome / Android
- Safari / iPhone e iPad
- Firefox
