import json
import pandas as pd
from openai import OpenAI
import random


class CommentSampler:
    def __init__(self, max_samples=100):
        self.max_samples = max_samples

    def sample(self, comentarios):
        if len(comentarios) > self.max_samples:
            return random.sample(comentarios, self.max_samples)
        return comentarios


class PromptBuilder:
    def __init__(self, contexto):
        self.contexto = contexto

    def build(self, comentarios_pos, comentarios_neu, comentarios_neg):
        
        self.sampler = CommentSampler()

        pos = self.sampler.sample(comentarios_pos)
        neu = self.sampler.sample(comentarios_neu)
        neg = self.sampler.sample(comentarios_neg)

        return f"""
        Contexto:
        {self.contexto}

        Distribuição:
        - Positivos: {len(comentarios_pos)}
        - Neutros: {len(comentarios_neu)}
        - Negativos: {len(comentarios_neg)}
        
        Aqui estão uma amostra dos comentários que foram classificados: 
        
        ### Positivos:
        {chr(10).join(pos)}

        ### Neutros:
        {chr(10).join(neu)}

        ### Negativos:
        {chr(10).join(neg)}

        Tarefa:
        1. Faça uma análise geral dos comentários sem falar de polarização, de maneira direta sem muitas interpretações
        2. Identifique padrões de discurso
        3. Destaque temas principais
        4. Analise separadamente positivos, neutros e negativos
        5. Faça uma separação clara do que é positivo, neutro e negativos
        
        Então quando temos termos como "urgência","aprove" eles partem do sentimento de cobrança para algo e estão situados na categoria neutra, eles não devem estar inclusos 
        em análises de comentários positivos
        
        Caso haja repetições de comentários, pontue isso.

        Seja objetivo e analítico.
        """


class CommentAnalyzer:
    def __init__(self, api_key, schema, model="gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key)
        self.schema = schema
        self.model = model

    def analyze(self, prompt):
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={
                "type": "json_schema",
                "json_schema": self.schema
            }
        )

        return json.loads(completion.choices[0].message.content)


class SentimentAnalysisPipeline:
    def __init__(self, api_key, schema, contexto, max_samples=100):
        self.sampler = CommentSampler(max_samples)
        self.prompt_builder = PromptBuilder(contexto)
        self.analyzer = CommentAnalyzer(api_key, schema)

    def run(self, df):
        # separação
        pos = df[df['classificacao']=='positivo']['comentario'].astype(str).tolist()
        neu = df[df['classificacao']=='neutro']['comentario'].astype(str).tolist()
        neg = df[df['classificacao']=='negativo']['comentario'].astype(str).tolist()

        # amostragem
        pos = self.sampler.sample(pos)
        neu = self.sampler.sample(neu)
        neg = self.sampler.sample(neg)

        # prompt
        prompt = self.prompt_builder.build(pos, neu, neg)

        # análise
        resultado = self.analyzer.analyze(prompt)

        return pd.DataFrame(resultado["respostas"])