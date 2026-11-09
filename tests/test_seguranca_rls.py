import pytest

# ==========================================
# 1. SIMULADOR DO MOTOR RLS (PostgreSQL)
# ==========================================
banco_ficticio = [
    {"id": 101, "avaliador_id": "aluno_joao", "dado": "Ficha do Paciente X"},
    {"id": 102, "avaliador_id": "aluno_maria", "dado": "Ficha do Paciente Y"},
]

def simular_rls_select(usuario_id: str, role: str) -> list:
    """Simula a política do Supabase: 'USING (auth.uid() = avaliador_id OR role = 'professor')'"""
    if role == "professor":
        return banco_ficticio  # Professor tem visão global
    
    # Aluno é bloqueado de ver as linhas que não têm o seu ID exato
    return [linha for linha in banco_ficticio if linha["avaliador_id"] == usuario_id]

def simular_rls_insert(usuario_id: str, role: str, nova_linha: dict) -> bool:
    """Simula a política do Supabase: 'WITH CHECK (auth.uid() = avaliador_id)'"""
    if role != "professor" and nova_linha["avaliador_id"] != usuario_id:
        # A base de dados aborta a transação antes da inserção[cite: 13]
        raise PermissionError("RLS Violation: Acesso negado pela base de dados. Identidade não corresponde.")
    
    banco_ficticio.append(nova_linha)
    return True

# ==========================================
# 2. SUÍTE DE TESTES (Identidades Distintas)
# ==========================================
class TestIsolamentoRLS:
    
    # --- TESTES DE LEITURA (SELECT) ---
    def test_aluno_so_consegue_ler_os_seus_dados(self):
        """Garante que o João não vê os dados da Maria (Isolamento)[cite: 13]."""
        resultados = simular_rls_select(usuario_id="aluno_joao", role="aluno")
        
        assert len(resultados) == 1
        assert resultados[0]["avaliador_id"] == "aluno_joao"
        # Garante que não há vestígios da Maria
        assert not any(r["avaliador_id"] == "aluno_maria" for r in resultados)

    def test_professor_consegue_ler_todos_os_dados(self):
        """Garante que as permissões de professor abrangem todo o espetro[cite: 13]."""
        resultados = simular_rls_select(usuario_id="prof_silva", role="professor")
        assert len(resultados) == 2  # Vê tanto o João como a Maria

    # --- TESTES DE ESCRITA (INSERT/UPDATE) ---
    def test_aluno_escrevendo_no_proprio_nome_permitido(self):
        """Garante o comportamento base de inserção autorizada[cite: 13]."""
        nova_ficha = {"id": 103, "avaliador_id": "aluno_joao", "dado": "Ficha Z"}
        assert simular_rls_insert("aluno_joao", "aluno", nova_ficha) is True

    def test_aluno_escrevendo_no_nome_de_outro_bloqueado(self):
        """Verifica se o bloqueio de base de dados impede a falsificação de identidade[cite: 13]."""
        nova_ficha_falsa = {"id": 104, "avaliador_id": "aluno_maria", "dado": "Ficha Inválida"}
        
        # O João tenta gravar usando o ID da Maria. O RLS tem de gritar "PermissionError"
        with pytest.raises(PermissionError, match="RLS Violation"):
            simular_rls_insert(usuario_id="aluno_joao", role="aluno", nova_linha=nova_ficha_falsa)