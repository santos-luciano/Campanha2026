import json
from openai import OpenAI


class CaptionClassifier:

    CATEGORIAS = {
        # Eleitoral / político-partidário
        "campanha_eleitoral": "candidatura, convenção partidária, comício, pedido de voto, alianças eleitorais",
        "posicionamento_politico": "opinião sobre pauta em debate (PEC, projeto de lei, tema nacional)",
        "atuacao_politica": "articulação, bastidores, negociação política sem ser sobre eleição",
        "resposta_criticas": "reação a ataques, fake news, oposição",
        "discurso_mobilizacao": "discurso motivacional de continuidade e engajamento (força, união, 'seguir em frente', 'vamos juntos'), sem pedido de voto, sem pauta específica e sem entrega/resultado concreto citado",


        # Gestão / governo
        "realizacoes_gestao": "obras, entregas, resultados concretos de mandato ou governo",
        "servico_publico": "informes operacionais: vacinação, mutirões, horários de atendimento, alertas, mudanças de trânsito, editais",
        "agenda_institucional": "compromissos oficiais, reuniões, sessões, viagens de trabalho, visitas",

        # Sociedade / comunicação institucional
        "campanha_conscientizacao": "datas temáticas de conscientização com apelo social (Agosto Lilás, Setembro Amarelo, Outubro Rosa, campanhas de saúde pública, combate a doenças)",
        "participacao_cidada": "interação direta com população, ouvidoria, consulta pública, eventos com a comunidade",
        "homenagens_datas": "datas comemorativas, luto, aniversários de cidade/instituição, efemérides sem apelo de campanha",
    }

    TEMAS = {
        "saude": "SUS, hospitais, vacinação, doenças, saúde pública ou privada",
        "educacao": "escolas, universidades, professores, matrículas, merenda, alfabetização",
        "seguranca": "polícia, criminalidade, violência, segurança pública, guarda municipal",
        "infraestrutura": "obras públicas, pavimentação, saneamento, iluminação, construção civil",
        "meio_ambiente": "sustentabilidade, clima, desmatamento, resíduos, áreas verdes, desastres ambientais",
        "economia": "emprego, inflação, impostos, orçamento público, desenvolvimento econômico",
        "assistencia_social": "programas sociais, combate à pobreza, CRAS, benefícios, população vulnerável",
        "cultura": "eventos culturais, patrimônio histórico, artes, festivais",
        "esporte": "eventos esportivos, incentivo à prática esportiva, equipamentos esportivos",
        "direitos_humanos": "igualdade, combate à discriminação, direitos de minorias, violência de gênero",
        "administracao_publica": "gestão interna, transparência, concursos, servidores públicos",
        "turismo": "atrativos turísticos, promoção de destinos, eventos turísticos",
        "habitacao": "moradia popular, regularização fundiária, programas habitacionais",
        "mobilidade_urbana": "transporte público, trânsito, ciclovias, mobilidade urbana",
        "outros": "não se enquadra claramente em nenhum tema acima",
    }

    def __init__(self, api_key, model="gpt-5-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def _lista_categorias_formatada(self):
        return "\n".join(
            f"- {chave}: {descricao}"
            for chave, descricao in self.CATEGORIAS.items()
        )

    def _lista_temas_formatada(self):
        return "\n".join(
            f"- {chave}: {descricao}"
            for chave, descricao in self.TEMAS.items()
        )

    def classify(self, caption):
        """Classifica uma única legenda (sem contexto de outras postagens)
        em categoria e tema."""

        prompt = f"""
Você é um classificador de legendas de redes sociais de políticos e instituições públicas.

Classifique a legenda em duas dimensões:

1) categoria (escolha apenas UMA):
{self._lista_categorias_formatada()}

2) tema (escolha apenas UM, o assunto de fundo da publicação):
{self._lista_temas_formatada()}

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
                    },
                    "tema": {
                        "type": "string",
                        "enum": list(self.TEMAS.keys())
                    }
                },
                "required": ["categoria", "tema"],
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
        Classifica um grupo de legendas em categoria e tema, dando ao
        modelo o contexto do conjunto para reduzir a oscilação entre
        categorias/temas próximos (ex: campanha vs atuação política).
        """

        legendas_numeradas = "\n\n".join(
            f"[{i}] {caption}" for i, caption in enumerate(captions)
        )

        prompt = f"""
Você é um classificador de legendas de redes sociais de políticos e instituições públicas.

As legendas abaixo podem pertencer ao mesmo evento ou contexto. Use o
conjunto para entender o contexto compartilhado antes de classificar cada
uma individualmente.

Cada legenda deve ser classificada em duas dimensões:

1) categoria (escolha apenas UMA):
{self._lista_categorias_formatada()}

2) tema (escolha apenas UM, o assunto de fundo da publicação):
{self._lista_temas_formatada()}

Classifique CADA legenda numerada em exatamente UMA categoria e UM tema,
mesmo que pareçam relacionadas entre si.

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
                                },
                                "tema": {
                                    "type": "string",
                                    "enum": list(self.TEMAS.keys())
                                }
                            },
                            "required": ["indice", "categoria", "tema"],
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
        return [
            {"categoria": item["categoria"], "tema": item["tema"]}
            for item in classificacoes_ordenadas
        ]

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