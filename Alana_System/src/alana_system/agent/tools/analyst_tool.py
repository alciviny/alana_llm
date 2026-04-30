import logging
from .base_tool import BaseTool
from ...memory.intelligence import GraphIntelligence

logger = logging.getLogger("alana.agent.tool.analyst")

class AutonomousAnalystTool(BaseTool):
    name = "autonomous_analyst"
    description = (
        "Ferramenta de auditoria topológica. Analisa padrões, centralidade e impacto de falhas no Grafo. "
        "Argumentos: 'mode' ('patterns' ou 'impact'), 'target' (nome da entidade para modo impact)."
    )
    
    def __init__(self, intelligence: GraphIntelligence = None):
        self.intelligence = intelligence
        
    async def execute(self, mode: str = "patterns", target: str = None, **kwargs) -> str:
        # Fallback para argumentos passados via kwargs
        m = mode or kwargs.get("mode", "patterns")
        t = target or kwargs.get("target")
        
        if not self.intelligence:
            return "[ERRO DE ANÁLISE]: Módulo de inteligência não inicializado. DICA: Use esta ferramenta apenas quando a Memória de Grafo estiver ativa."
            
        try:
            if m == "patterns":
                logger.info("🕵️ Alana executando Auditoria de Padrões Autônoma...")
                analysis = await self.intelligence.analyze_patterns()
                
                insights = "\n".join([f"- {i}" for i in analysis.get("insights", [])])
                authorities = ", ".join([f"{n} ({v:.2f})" for n, v in analysis.get("authorities", [])])
                
                return (
                    f"--- RELATÓRIO DE AUDITORIA DE PADRÕES ---\n\n"
                    f"PRINCIPAIS AUTORIDADES TÉCNICAS: {authorities}\n\n"
                    f"INSIGHTS COGNITIVOS:\n{insights}\n\n"
                    f"CONCLUSÃO: {analysis.get('clusters_count')} clusters identificados."
                )
                
            elif m == "impact":
                if not t:
                    return "[ERRO DE ANÁLISE]: Para o modo 'impact', você DEVE fornecer um 'target'. DICA: Use {'mode': 'impact', 'target': 'Nome do Componente'}"
                
                logger.info(f"💣 Alana analisando impacto de falha em: {t}")
                impact = await self.intelligence.analyze_propagation(t)
                
                if "error" in impact:
                    return f"[ERRO NO GRAFO]: {impact['error']}. DICA: Verifique se a entidade existe no mapa mental."
                    
                return (
                    f"--- ANÁLISE DE IMPACTO (TEORIA DO CAOS) ---\n\n"
                    f"ALVO: {impact['start_node']}\n"
                    f"ENTIDADES AFETADAS EM 3 SALTOS: {impact['total_impact_count']}\n\n"
                    f"AVALIAÇÃO DE RISCO:\n{impact['risk_assessment']}"
                )
            
            else:
                return f"[ERRO DE ARGUMENTO]: Modo '{m}' inválido. DICA: Use 'patterns' ou 'impact'."
                
        except Exception as e:
            logger.error(f"Erro na AutonomousAnalystTool: {e}")
            return f"[ERRO CRÍTICO NA ANÁLISE]: {str(e)}. DICA: Verifique a integridade do banco de dados de grafos."
