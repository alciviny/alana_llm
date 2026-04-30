import logging
from .base_tool import BaseTool
from ...memory.intelligence import GraphIntelligence

logger = logging.getLogger("alana.agent.tools.catalyst")

class KnowledgeCatalystTool(BaseTool):
    name = "knowledge_catalyst"
    description = (
        "Analisa o estado atual do conhecimento e sugere o que ler ou pesquisar "
        "em seguida para maximizar a conexao entre conceitos (Efeito Anti-Borboleta). "
        "Identifica 'pontes' tecnicas que unificam ilhas de conhecimento isoladas."
    )
    
    def __init__(self, intelligence: GraphIntelligence = None):
        # Injetado pelo motor de agentes
        self.intelligence = intelligence
        
    async def execute(self, **kwargs) -> str:
        if not self.intelligence:
            return "[ERRO]: Modulo de inteligencia de grafo nao inicializado."
            
        try:
            # O namespace vem do contexto injetado na BaseTool pelo AgentEngine
            namespace = self.current_namespace or "global"
            
            logger.info(f"🌱 Alana buscando catalisadores de conhecimento para [{namespace}]...")
            
            # Chama a inteligencia para identificar os gaps (pontes sugeridas)
            gaps = await self.intelligence.identify_knowledge_gaps(namespace=namespace)
            
            if not gaps:
                return "✅ O conhecimento atual no namespace '{}' esta altamente integrado. Nao ha ilhas isoladas detectadas.".format(namespace)
            
            report = f"--- RELATÓRIO CATALISADOR DE CONHECIMENTO [{namespace}] ---\n"
            report += "Objetivo: Maximizar a densificacao do grafo e reduzir a fragmentacao do saber.\n"
            
            for i, gap in enumerate(gaps, 1):
                report += f"\n🌉 PONTE #{i}: {gap['missing_link']}\n"
                report += f"   - IMPACTO: {gap['potential_impact']}\n"
                report += f"   - CONECTA: Cluster '{gap['source_cluster']}' ↔️ Cluster '{gap['target_cluster']}'\n"
                report += f"   - Raciocinio: Esta ponte unifica subdominios fragmentados.\n"
            
            report += "\n🌱 ESTRATÉGIA: Priorize o estudo ou a ingestao de documentos sobre as PONTES sugeridas."
            return report
            
        except Exception as e:
            logger.error(f"Erro na KnowledgeCatalystTool: {e}")
            return f"[ERRO NO CATALISADOR]: {str(e)}"
