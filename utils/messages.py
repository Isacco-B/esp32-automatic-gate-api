DEFAULT_USER = "Qualcuno"

MESSAGES = {
    "gate": {
        "success": {
            "2": "{user} ha fermato il cancello",
            "3": "{user} sta aprendo il cancello",
            "4": "{user} sta chiudendo il cancello",
        },
        "error": "Errore nell'apertura del cancello richiesta da {user}",
    },
    "gate_partial": {
        "success": "{user} sta aprendo il cancello pedonabile",
        "error": "Errore nell'apertura pedonabile richiesta da {user}",
    },
    "small_gate": {
        "success": "{user} sta aprendo il cancellino",
        "error": "Errore nell'apertura del cancellino richiesta da {user}",
    },
    "garage_light": {
        "success": "{user} ha acceso la luce del garage",
        "error": "Errore nell'accensione luce garage richiesta da {user}",
    },
}

STATE_DESCRIPTIONS = {
    "0": "chiuso",
    "1": "aperto",
    "2": "stop",
    "3": "in apertura",
    "4": "in chiusura",
    "unknown": "sconosciuto",
}

OPTION_DESCRIPTIONS = {"0": "disattivo", "1": "attivo", "unknown": "sconosciuto"}
