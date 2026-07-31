import json
from openai import OpenAI
from typing import List
from datetime import datetime


class CommentClassifier:
    def __init__(
        self,
        api_key: str,
        schema: dict,
        contexto: str,
        model: str = "gpt-5-mini",
        batch_size: int = 100
    ):
        self.client = OpenAI(api_key=api_key)
        self.schema = schema
        self.contexto = contexto
        self.model = model
        self.batch_size = batch_size

    def _build_prompt(self,comments: List[str]) -> str:
        prompt = f"""
                
                {self.contexto}. O que as pessoas estão achando nos comentários?
                
                Você é um classificador de comentários em redes sociais, e devem classificar comentários categoricamente entre positivo|neutro|negativo seguindo os seguintes comandos:
                
                Classificações positivas:
                - Associações de Flávio Bolsonaro ao Banco Master
                - Galego, é um apelido carinhoso para Jaques Wagner
                - criticas a opositores
                - Intitular alguém de bolsonarista
                - Elogios ao governo atual
                - Critica ao governo de Bolsonaro
                - Apoio ao número 13 é positivo 
                - Criticar congresso (como falar que o congresso é inimigo do povo)
                - Criticar senado
                - Criticar o bolsonarismo
                - Elogio, prestigio e celebração a aliados (Lula, Rui Costa, Otto Alencar,Jerônimo, Jaques Wagner,Caetano,Ivoneide)
                - Listar aliados como uma equipe
                - Adjetivos como "bombando", "em alta"
                - Ironizar o ex-presidente
                - Critica ao ex-presidente
                - Ironiza o ex-presidente e critica sua gestão.
                - Crítica ao ex-presidente, insinuando que não deixou nada.
                - Emojis de apoio
                
                Classifações neutras:
                - pedidos para aprovação de alguma PL (Projeto de Lei), emenda, PEC
                - coisas falando como "urgencia", "aprove",
                - Apoio a categorias de trabalhadores
                - "SEMENTE CAMAÇARI MOBILIZA"
                
                Classificações negativas:
                - Associações de Lula ao caso Master/ Filme
                - Associações com "terreno" (envolvimento em uma operação)
                - Associação com Vorcaro
                - Associação ao Master / CREDCESTA
                - Elogios ao ex-prefeito, gestão anterior
                - Cobranças de dinheiro como "cadê xx milhões?" devem ser considerada negativas
                - apoio a opositores como ACM Neto, Bolsonaro, João Roma, número 22, Flávio devem ser classificados estritamente como negativo
                - Criticas ao PT
                - Referencia a "nora"
                - Referencia a sumiços ou roubo
                
                Em caso de criticas, movimentos orquestrados seja mais direto sobre a pauta, e identifique ironias para consigar classificar corretamente os comentários
                
                Sendo os seguintes {len(comments)}:

                """
        for i, c in enumerate(comments, 1):
            prompt += f"{i}. {c}\n"

        return prompt

    def classify(self, comments: List[str]) -> dict:
        resultados = []
    
        total_batches = (len(comments) + self.batch_size - 1) // self.batch_size
    
        for batch_idx, i in enumerate(
            range(0, len(comments), self.batch_size),
            start=1
        ):
            batch = comments[i:i + self.batch_size]
    
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] "
                f"Processando lote {batch_idx}/{total_batches} "
                f"(comentários {i + 1}–{i + len(batch)})"
            )
    
            prompt = self._build_prompt(batch)
    
            completion = self.client.chat.completions.create(
                model=self.model,
#                temperature=0.0,
                messages=[{"role": "system", "content": prompt}],
                response_format={
                    "type": "json_schema",

                    "json_schema": self.schema
                }
            )

            resposta = json.loads(
                completion.choices[0].message.content
            )
    
            resultados.extend(resposta["respostas"])
        return {"respostas": resultados}
