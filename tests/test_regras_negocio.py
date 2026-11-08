import pytest
from pydantic import BaseModel, Field, ValidationError

# ==========================================
# 1. SIMULAÇÃO DAS FUNÇÕES DE NEGÓCIO
# ==========================================
# AULA: Em projetos reais, importaríamos estas funções do 'backend'. 
# Aqui, isolamo-las para garantir que a lógica matemática pura está a ser testada.

def calcular_imc(peso_kg: float, altura_m: float) -> float | None:
    """Calcula o IMC e previne divisões por zero."""
    if not peso_kg or not altura_m or altura_m <= 0:
        return None
    return round(peso_kg / (altura_m ** 2), 2)

def aplicar_k_anonimato(grupos: list[dict]) -> list[dict]:
    """Aplica a regra n < 3 (ORT-27) a uma lista de dicionários."""
    resultado = []
    ocultos_total = 0
    for grupo in grupos:
        if grupo["total"] < 3:
            ocultos_total += grupo["total"]
        else:
            resultado.append(grupo)
            
    if ocultos_total > 0:
        resultado.append({"regiao": "Outros", "total": ocultos_total})
    return resultado

# AULA: Usamos o Pydantic para validar os limites (Boundaries) dos dados de entrada[cite: 11].
class ParticipanteEsquema(BaseModel):
    idade: int = Field(..., ge=18, le=120, description="Idade deve ser entre 18 e 120 anos.")
    peso_kg: float = Field(..., gt=0, description="Peso deve ser estritamente maior que zero.")

# ==========================================
# 2. SUÍTE DE TESTES AUTOMATIZADOS (pytest)
# ==========================================

class TestRegrasDeNegocio:
    
    # --- TESTES DE CÁLCULO DE IMC ---
    def test_imc_cenario_positivo(self):
        """Testa o cálculo do IMC com dados perfeitamente válidos (Cenário Positivo)[cite: 11]."""
        imc = calcular_imc(peso_kg=70.0, altura_m=1.75)
        assert imc == 22.86 # 70 / (1.75 * 1.75)

    def test_imc_cenario_limite_zero(self):
        """Testa o comportamento quando a altura é zero para evitar crash 'ZeroDivisionError' (Caso de Borda)[cite: 11]."""
        imc = calcular_imc(peso_kg=70.0, altura_m=0.0)
        assert imc is None

    def test_imc_cenario_negativo(self):
        """Testa o comportamento com dados ausentes (Cenário Negativo)[cite: 11]."""
        assert calcular_imc(None, 1.75) is None
        assert calcular_imc(70.0, None) is None

    # --- TESTES DE K-ANONIMATO (n < 3) ---
    def test_k_anonimato_oculta_menores_que_tres(self):
        """Garante que grupos com n=1 ou n=2 são removidos e somados em 'Outros'[cite: 11]."""
        dados_entrada = [
            {"regiao": "Joelho", "total": 5}, # Maior que 3 (Mantém)
            {"regiao": "Ombro", "total": 2},  # Menor que 3 (Oculta)
            {"regiao": "Punho", "total": 1},  # Menor que 3 (Oculta)
        ]
        resultado = aplicar_k_anonimato(dados_entrada)
        
        # AULA: O resultado esperado é ter apenas 2 itens: "Joelho" e "Outros".
        assert len(resultado) == 2
        # O total em "Outros" deve ser a soma de Ombro (2) e Punho (1) = 3.
        item_outros = next(g for g in resultado if g["regiao"] == "Outros")
        assert item_outros["total"] == 3

    # --- TESTES DE VALIDAÇÃO PYDANTIC ---
    def test_pydantic_limite_idade_valida(self):
        """Testa a criação de um participante no limite inferior exato (18 anos)[cite: 11]."""
        participante = ParticipanteEsquema(idade=18, peso_kg=60.5)
        assert participante.idade == 18

    def test_pydantic_limite_idade_invalida(self):
        """Garante que o sistema rejeita idades abaixo de 18 anos levantando um ValidationError[cite: 11]."""
        # AULA: O 'pytest.raises' verifica se a nossa aplicação "grita" um erro quando fazemos algo proibido.
        with pytest.raises(ValidationError):
            ParticipanteEsquema(idade=17, peso_kg=60.5)

    def test_pydantic_peso_negativo(self):
        """Garante que pesos negativos ou zero são rejeitados[cite: 11]."""
        with pytest.raises(ValidationError):
            ParticipanteEsquema(idade=25, peso_kg=-5.0)