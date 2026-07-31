schema_classifier = {
    "name": "ClassificacaoComentariosLote",
    "schema": {
        "type": "object",
        "properties": {
            "respostas": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "numero": {"type": "integer",
                                   "description": "Número exato do comentário que está sendo classificado"},
                        "comentario": {
                          "type": "string",
                          "maxLength": 500,
                          "description": "Texto original."
                        },
                        "classificacao": {
                            "type": "string",
                            "enum": ["positivo", "negativo", "neutro"]
                        },
                        "motivo": {"type": "string"}
                    },
                    "required": [
                        "numero",
                        "comentario",
                        "classificacao",
                        "motivo"

                    ],
                    "additionalProperties": False
                }
            }
        },
        "required": ["respostas"],
        "additionalProperties": False
    },
    "strict": True
}