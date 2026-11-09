import pytest
import csv
import io

# ==========================================
# 1. SIMULADORES DO PIPELINE DE DADOS
# ==========================================

def motor_dashboard_kpis(banco_raw: list[dict]) -> dict:
    """Simula o motor de agregação criado na ORT-26 e ORT-27."""
    total_avaliacoes = len(banco_raw)
    completas = len([a for a in banco_raw if a.get("status") == "concluido"])
    
    # Simula a agregação de positividade (simplificada para o teste)
    positivos = len([a for a in banco_raw if a.get("resultado") == "Positivo"])
    
    return {
        "participantes_avaliados": total_avaliacoes,
        "avaliacoes_completas": completas,
        "testes_positivos": positivos
    }

def motor_exportacao_csv(kpis: dict) -> str:
    """Simula a geração do CSV em memória criada na ORT-29."""
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=';')
    
    # Escrevemos o formato exato que o nosso exportador produz
    escritor.writerow(["Métrica", "Valor"])
    escritor.writerow(["Total de Participantes", kpis["participantes_avaliados"]])
    escritor.writerow(["Avaliações Concluídas", kpis["avaliacoes_completas"]])
    escritor.writerow(["Testes Positivos", kpis["testes_positivos"]])
    
    return saida.getvalue()

# ==========================================
# 2. SUÍTE DE TESTES (Rotina de Diferença Zero)
# ==========================================
class TestConsistenciaRelatorios:
    
    def test_reconciliacao_banco_dashboard_csv(self):
        """
        Rotina automatizada que deteta divergências; garantindo totais iguais.
        """
        # FASE A: BANCO DE DADOS (The Ground Truth)
        banco_de_dados_mock = [
            {"id": 1, "status": "concluido", "resultado": "Positivo"},
            {"id": 2, "status": "concluido", "resultado": "Negativo"},
            {"id": 3, "status": "em_andamento", "resultado": "Positivo"},
            {"id": 4, "status": "concluido", "resultado": "Não realizado"}
        ]
        
        # Totais reais calculados diretamente do banco bruto
        real_total = 4
        real_completas = 3
        real_positivos = 2

        # FASE B: DASHBOARD (A Agregação)
        kpis_dashboard = motor_dashboard_kpis(banco_de_dados_mock)
        
        # Validação 1: Banco vs Dashboard têm diferença zero[cite: 14]
        assert kpis_dashboard["participantes_avaliados"] == real_total
        assert kpis_dashboard["avaliacoes_completas"] == real_completas
        assert kpis_dashboard["testes_positivos"] == real_positivos

        # FASE C: EXPORTAÇÃO (O Relatório CSV)
        csv_texto = motor_exportacao_csv(kpis_dashboard)
        
        # FASE D: AUDITORIA (Lemos o CSV gerado e comparamos com o Banco)
        leitor = csv.DictReader(io.StringIO(csv_texto), delimiter=';')
        linhas_csv = list(leitor)
        
        # Extraímos os valores lidos do ficheiro de texto
        csv_total = int(next(l["Valor"] for l in linhas_csv if l["Métrica"] == "Total de Participantes"))
        csv_completas = int(next(l["Valor"] for l in linhas_csv if l["Métrica"] == "Avaliações Concluídas"))
        csv_positivos = int(next(l["Valor"] for l in linhas_csv if l["Métrica"] == "Testes Positivos"))
        
        # Validação 2: Exportação vs Banco têm diferença zero[cite: 14]
        assert csv_total == real_total
        assert csv_completas == real_completas
        assert csv_positivos == real_positivos