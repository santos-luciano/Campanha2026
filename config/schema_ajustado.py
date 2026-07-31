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
                        "numero": {
                            "type": "integer",
                            "description": "Número exato do comentário que está sendo classificado"
                        },
                        "comentario": {
                            "type": "string",
                            "description": "Texto original."
                        },

                        "traidor": {
                            "type": "boolean",
                            "description": "Tratando Jaques Wagner como traidor"
                        },
                        "motivo": {
                            "type": "string",
                            "description": "Justificativa curta da classificação"
                        }
                    },
                    "required": [
                        "numero",
                        "comentario",
                        "traidor",
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