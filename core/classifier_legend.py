import json
from openai import OpenAI


class CaptionClassifier:

    CATEGORIAS = {
        "campanha_eleitoral": "candidatura, convenção partidária, comício, pedido de voto, alianças eleitorais, filiação",
        "realizacoes_gestao": "obras, entregas, resultados de mandato ou governo",
        "posicionamento_politico": "opinião sobre pauta em debate (PEC, projeto de lei, tema nacional)",
        "agenda_institucional": "compromissos oficiais, reuniões, sessões, viagens de trabalho",
        "atuacao_politica": "articulação, bastidores, negociação política sem ser sobre eleição",
        "participacao_cidada": "interação com população, ouvidoria, eventos com comunidade",
        "homenagens_datas": "datas comemorativas, luto, aniversários, efemérides",
        "resposta_criticas": "reação a ataques, fake news, oposição",
    }

    def __init__(self, api_key, model="gpt-5-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def _lista_categorias_formatada(self):
        return "\n".join(
            f"- {chave}: {descricao}"
            for chave, descricao in self.CATEGORIAS.items()
        )

    def classify(self, caption):
        """Classifica uma única legenda (sem contexto de outras postagens)."""

        prompt = f"""
Você é um classificador de legendas de redes sociais de políticos e instituições públicas.

Classifique a legenda em apenas UMA categoria:

{self._lista_categorias_formatada()}

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
                        "enum": list(self.CATEGORIAS.keys())
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

    def classify_batch(self, captions):
        """
        Classifica um grupo de legendas, dando ao modelo o contexto do
        conjunto para reduzir a oscilação entre categorias próximas
        (ex: campanha vs atuação política).
        """

        legendas_numeradas = "\n\n".join(
            f"[{i}] {caption}" for i, caption in enumerate(captions)
        )

        prompt = f"""
Você é um classificador de legendas de redes sociais de políticos e instituições públicas.

As legendas abaixo podem pertencer ao mesmo evento ou contexto. Use o
conjunto para entender o contexto compartilhado antes de classificar cada
uma individualmente.

Categorias disponíveis:

{self._lista_categorias_formatada()}

Classifique CADA legenda numerada em exatamente UMA categoria, mesmo que
pareçam relacionadas entre si.

Legendas:
{legendas_numeradas}
"""

        schema = {
            "name": "ClassificacaoLote",
            "schema": {
                "type": "object",
                "properties": {
                    "classificacoes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "indice": {"type": "integer"},
                                "categoria": {
                                    "type": "string",
                                    "enum": list(self.CATEGORIAS.keys())
                                }
                            },
                            "required": ["indice", "categoria"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["classificacoes"],
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

        resultado = json.loads(completion.choices[0].message.content)

        # Reordena pelo índice para garantir alinhamento com a lista original
        classificacoes_ordenadas = sorted(
            resultado["classificacoes"], key=lambda x: x["indice"]
        )
        return [item["categoria"] for item in classificacoes_ordenadas]

    @staticmethod
    def agrupar_em_lotes(itens, tamanho_lote=10):
        """
        Divide uma lista de itens (ex: índices do DataFrame) em lotes de
        tamanho fixo, para envio ao classify_batch.
        """
        return [
            itens[i:i + tamanho_lote]
            for i in range(0, len(itens), tamanho_lote)
        ]