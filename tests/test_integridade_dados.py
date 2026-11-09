import pytest
from pydantic import BaseModel, Field, ValidationError

# ==========================================
# 1. MODELOS DE INTEGRIDADE (Pydantic)
# ==========================================
class ResultadoTesteSchema(BaseModel):
    """
    AULA: O 'avaliacao_id' é obrigatório. Isto garante a regra: 'nenhum resultado sem avaliação'.
    """
    avaliacao_id: str = Field(..., description="ID da avaliação pai obrigatório.")
    teste_id: int
    lado: str
    resultado: str
    
    # AULA: A restrição ge=0 e le=10 garante fisicamente que o Python rejeite erros de digitação[cite: 12].
    dor_0_10: int = Field(..., ge=0, le=10, description="A dor deve estar estritamente entre 0 e 10.")

# ==========================================
# 2. SIMULADOR DO BANCO DE DADOS (Restrição de Duplicidade)
# ==========================================
banco_de_dados_mock = []

def salvar_resultado(novo_resultado: ResultadoTesteSchema):
    """
    AULA: Simula a 'Unique Constraint' do banco de dados relacional.
    Evita duplicidade pela chave composta: (avaliacao, teste, lado)[cite: 12].
    """
    for res in banco_de_dados_mock:
        if (res.avaliacao_id == novo_resultado.avaliacao_id and
            res.teste_id == novo_resultado.teste_id and
            res.lado == novo_resultado.lado):
            raise ValueError("Erro de Integridade: Duplicidade de teste detectada para o mesmo lado.")
            
    banco_de_dados_mock.append(novo_resultado)
    return True

# ==========================================
# 3. SUÍTE DE TESTES (pytest)
# ==========================================
class TestIntegridadeDados:
    
    def setup_method(self):
        """Limpa o banco de dados falso antes de cada teste para evitar contaminação."""
        banco_de_dados_mock.clear()

    # --- TESTES DE LIMITE DE DOR ---
    def test_dor_dentro_do_limite_valido(self):
        """Testa se valores de dor normais (ex: 5) são aceites[cite: 12]."""
        res = ResultadoTesteSchema(avaliacao_id="A1", teste_id=1, lado="Direito", resultado="Positivo", dor_0_10=5)
        assert res.dor_0_10 == 5

    def test_dor_acima_do_limite_rejeitada(self):
        """Testa a blindagem contra dor inválida (ex: 11). Deve lançar ValidationError[cite: 12]."""
        with pytest.raises(ValidationError):
            ResultadoTesteSchema(avaliacao_id="A1", teste_id=1, lado="Direito", resultado="Positivo", dor_0_10=11)

    def test_dor_negativa_rejeitada(self):
        """Testa a blindagem contra dor abaixo de zero[cite: 12]."""
        with pytest.raises(ValidationError):
            ResultadoTesteSchema(avaliacao_id="A1", teste_id=1, lado="Direito", resultado="Positivo", dor_0_10=-1)

    # --- TESTES DE INTEGRIDADE ESTRUTURAL ---
    def test_resultado_sem_avaliacao_rejeitado(self):
        """Garante que não existem dados órfãos[cite: 12]."""
        with pytest.raises(ValidationError):
            # Omitimos o avaliacao_id propositadamente
            ResultadoTesteSchema(teste_id=1, lado="Direito", resultado="Positivo", dor_0_10=5) 

    # --- TESTES DE DUPLICIDADE (UNIQUE CONSTRAINT) ---
    def test_duplicidade_teste_lado_rejeitada(self):
        """Testa se o sistema impede duas gravações do mesmo teste no mesmo lado da mesma avaliação[cite: 12]."""
        # 1. Registamos o primeiro teste (Sucesso)
        res1 = ResultadoTesteSchema(avaliacao_id="A1", teste_id=1, lado="Esquerdo", resultado="Positivo", dor_0_10=2)
        salvar_resultado(res1)

        # 2. Tentamos registar o MESMO teste no MESMO lado. O sistema deve lançar ValueError.
        res2 = ResultadoTesteSchema(avaliacao_id="A1", teste_id=1, lado="Esquerdo", resultado="Negativo", dor_0_10=0)
        with pytest.raises(ValueError, match="Duplicidade de teste detectada"):
            salvar_resultado(res2)
            
    def test_lados_diferentes_permitidos(self):
        """Garante que testes iguais em lados diferentes (Direito vs Esquerdo) são permitidos[cite: 12]."""
        res_esq = ResultadoTesteSchema(avaliacao_id="A1", teste_id=1, lado="Esquerdo", resultado="Positivo", dor_0_10=2)
        salvar_resultado(res_esq)
        
        res_dir = ResultadoTesteSchema(avaliacao_id="A1", teste_id=1, lado="Direito", resultado="Negativo", dor_0_10=0)
        assert salvar_resultado(res_dir) is True # Diferente lado, deve ser permitido!