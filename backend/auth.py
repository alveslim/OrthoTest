import os 
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "colar_secret") # fzr na vercel

def validar(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token,
                             SUPABASE_JWT_SECRET,
                             algorithms=["HS256"],
                             options={"verify_aud": False} # supabase lida com aud internamente
                             )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
def requer_professor(payload: dict = Depends(validar)):
    """Verifica se o utilizador possui a role 'professor'."""
    app_metadata = payload.get("app_metadata", {})
    papel = app_metadata.get("role")
    
    if papel != "professor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: apenas professores podem acessar este recurso.",
        )
    return payload