import json
from openai import OpenAI


class CaptionClassifier:

    def __init__(self, api_key, model="gpt-5-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def classify(self, caption):

        prompt = f"""
Você é um classificador de legendas de redes sociais de políticos e instituições públicas.

Classifique a legenda em apenas UMA categoria:

- realizacoes_gestao
- posicionamento_politico
- agenda_institucional
- atuacao_politica
- participacao_cidada
- homenagens_datas
- resposta_criticas

Legenda:
{caption}
"""

        schema = {
            "name": "ClassificacaoLegenda",
            "schema": {
                "type": "object",
                "properties": {
                    "categoria": {
                        "type": "string",
                        "enum": [
                            "realizacoes_gestao",
                            "posicionamento_politico",
                            "agenda_institucional",
                            "atuacao_politica",
                            "participacao_cidada",
                            "homenagens_datas",
                            "resposta_criticas"
                        ]
                    }
                },
                "required": ["categoria"],
                "additionalProperties": False
            },
            "strict": True
        }

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": schema
            }
        )

        return json.loads(
            completion.choices[0].message.content
        )
