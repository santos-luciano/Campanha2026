schema_classifier_consolidado = { "name": "ClassificacaoComentariosLote",
                     "schema": { "type": "object", 
                                "properties": { "respostas": 
                                               { "type": "array",
                                                "items": { 
                              "type": "object", 
                              "properties": 
                                  {# "review_comments": {"type": "string",
                                   #                     "description": "Escreva um resumo direto dos comentários com aproximadamente 400 a 500 caracteres, abordando o ponto principal da classificação, sem mencionar polarização. Respostas curtas e diretas."},
                                   "main_topics": {
                                           "type": "array",
                                           "items": {"type": "string",
                                                     "description":"4 temas principais, cada tema definido em no máximo 2 termos"}
                                       },
                                   "review_comments_positives": { "type": "string",
                                                                 "description": "Os comentários positivos apontam que as pessoas pensam o quê? Seja direto e dê um exemplo" ,
                                                                 "maxLength": 500},
                                   "review_comments_neutral": { "type": "string",
                                                               "maxLength": 500,
                                                               "description": "Os comentários neutros apontam que as pessoas pensam o quê? Seja direto e dê um exemplo" }, 
                                   "review_comments_negative": {"type": "string",
                                                                "maxLength": 500,
                                                                "description": "Os comentários negativos apontam que as pessoas pensam o quê? Seja direto e dê um exemplo"} }, 
                                  "required": [ #"review_comments",
                                               "main_topics",
                                               "review_comments_positives",
                                               "review_comments_neutral", 
                                               "review_comments_negative" ], 
                                  "additionalProperties": False } } }, 
                            "required": ["respostas"], "additionalProperties": False }, "strict": True }
