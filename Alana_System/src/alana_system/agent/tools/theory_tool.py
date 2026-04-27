import logging
import asyncio
from .base_tool import BaseTool
from .code_runners.python_runner import PythonRunnerTool
from .file_system import WriteCodeTool

logger = logging.getLogger(__name__)

class TheoryValidationTool(BaseTool):
    name = "validate_theory"
    description = (
        "Protocolo Cient\u00edfico S\u00eanior. Valida uma teoria técnica atrav\u00e9s de simula\u00e7\u00e3o e confronto de dados. "
        "Argumentos: 'theory' (str), 'simulation_code' (str)."
    )
    
    def __init__(self):
        # Usa as ferramentas existentes como sub-componentes (Composição)
        self.writer = WriteCodeTool()
        self.runner = PythonRunnerTool()
        
    def execute(self, theory: str, simulation_code: str) -> str:
        """
        Executa o ciclo: Hipótese -> Experimento -> Verificação.
        """
        filename = "experiment_validation.py"
        
        # 1. Prepara o ambiente de laboratório
        # Injeta o import do helper se não existir
        if "import alana_lab" not in simulation_code:
            simulation_code = "import alana_lab\n\n" + simulation_code
            
        logger.info(f"🔬 Alana iniciando validação de teoria: {theory[:50]}...")
        
        # 2. Escreve o código
        write_res = self.writer.execute(filename, simulation_code)
        if "[ERRO]" in write_res:
            return write_res
            
        # 3. Executa a simulação
        run_res = self.runner.execute(filename)
        
        # 4. Sintetiza o relatório científico
        report = (
            f"--- PROTOCOLO DE VALIDAÇÃO CIENTÍFICA ---\n"
            f"TEORIA ANALISADA: {theory}\n\n"
            f"RESULTADO DO EXPERIMENTO:\n{run_res}\n\n"
            f"VEREDITO: Analise os dados acima e confirme se a teoria se sustenta ou se há anomalias."
        )
        
        return report
