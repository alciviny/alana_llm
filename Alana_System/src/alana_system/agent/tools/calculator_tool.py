import logging
import numpy as np
import scipy
from .base_tool import BaseTool

logger = logging.getLogger("alana.agent.tool.calculator")

class EngineeringCalculatorTool(BaseTool):
    name = "calculate"
    description = "Executa cálculos matemáticos e de engenharia complexos usando NumPy e SciPy. Use para validar impedâncias, frequências, dissipação ou qualquer fórmula técnica. Argumento: 'expression' (ex: 'np.sqrt(10**2 + 5**2)')"
    
    def __init__(self):
        # Namespace seguro para o Agente usar
        self.safe_dict = {
            'np': np,
            'numpy': np,
            'scipy': scipy,
            'sqrt': np.sqrt,
            'log': np.log10,
            'ln': np.log,
            'sin': np.sin,
            'cos': np.cos,
            'pi': np.pi,
            'e': np.e
        }
        
    async def execute(self, expression: str = None, **kwargs) -> str:
        # Tenta pegar a expressão de qualquer forma (argumento nomeado ou kwargs)
        expr = expression or kwargs.get("expression")
        
        if not expr:
            return "[ERRO DE CÁLCULO]: Nenhuma expressão fornecida. DICA: Use o argumento 'expression', ex: {'expression': '2 + 2'}"
            
        try:
            logger.info(f"🧮 Alana calculando: {expr}")
            # Avalia a expressão no contexto seguro
            result = eval(expr, {"__builtins__": {}}, self.safe_dict)
            return f"[CÁLCULO EXECUTADO]\nEXPRESSÃO: {expr}\nRESULTADO: {result}"
        except Exception as e:
            logger.error(f"Erro no cálculo: {e}")
            return f"[ERRO DE CÁLCULO]: '{str(e)}'. DICA: Certifique-se de usar prefixo 'np.' para funções NumPy e que a sintaxe Python esteja correta."
