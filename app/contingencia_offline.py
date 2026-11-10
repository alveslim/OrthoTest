import json
import os
from pathlib import Path

import requests

# Fila no disco, ao lado do projeto (não depende da pasta onde o app foi iniciado).
ARQUIVO_FILA = str(Path(__file__).resolve().parent.parent / "fila_offline.json")

def salvar_rascunho_local(item_avaliacao: dict) -> bool:
    """
    AULA: Persiste o resultado localmente em disco caso a internet caia.
    Usa uma chave única (avaliacao_id + teste_id + lado) para evitar duplicar no rascunho.
    """
    fila = carregar_fila_local()
    chave_nova = f"{item_avaliacao.get('avaliacao_id')}_{item_avaliacao.get('teste_id')}_{item_avaliacao.get('lado')}"
    
    # Atualiza se já existir na fila local (evita duplicidade) ou adiciona novo
    atualizado = False
    for i, item in enumerate(fila):
        chave_existente = f"{item.get('avaliacao_id')}_{item.get('teste_id')}_{item.get('lado')}"
        if chave_existente == chave_nova:
            fila[i] = item_avaliacao
            atualizado = True
            break
            
    if not atualizado:
        fila.append(item_avaliacao)
        
    with open(ARQUIVO_FILA, "w", encoding="utf-8") as f:
        json.dump(fila, f, ensure_ascii=False, indent=2)
    return True

def carregar_fila_local() -> list[dict]:
    """Lê os rascunhos pendentes do disco."""
    if not os.path.exists(ARQUIVO_FILA):
        return []
    try:
        with open(ARQUIVO_FILA, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def sincronizar_rascunhos(api_url: str, headers: dict, post_fn=requests.post) -> dict:
    """
    AULA: Tenta reenviar os itens da fila local para o servidor quando a conexão volta.
    Mantém na fila apenas os itens que falharem por erro de rede, reportando conflitos.
    """
    fila = carregar_fila_local()
    if not fila:
        return {"sincronizados": 0, "pendentes": 0, "conflitos": 0, "erros": []}

    restantes = []
    sincronizados = 0
    conflitos = 0
    erros = []

    for item in fila:
        try:
            url = f"{api_url}/avaliacoes/{item['avaliacao_id']}/resultados"
            resp = post_fn(url, headers=headers, json=item, timeout=8)
            if resp.status_code in (200, 201):
                sincronizados += 1
            elif resp.status_code == 409:
                # 409 Conflict: O registro já existe no banco, descartamos da fila para não duplicar!
                conflitos += 1
            else:
                erros.append(f"Erro {resp.status_code} no teste {item.get('teste_id')}")
                restantes.append(item)
        except Exception as e:
            erros.append(f"Falha de rede: {str(e)}")
            restantes.append(item)

    with open(ARQUIVO_FILA, "w", encoding="utf-8") as f:
        json.dump(restantes, f, ensure_ascii=False, indent=2)

    return {
        "sincronizados": sincronizados,
        "pendentes": len(restantes),
        "conflitos": conflitos,
        "erros": erros
    }