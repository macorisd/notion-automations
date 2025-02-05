from fastapi import Request, HTTPException

class APIUtils:
    @classmethod
    def check_accept_json(cls, request: Request):
        """Verificar si la cabecera Accept contiene 'application/json'."""
        accepted = request.headers.get("Accept", "")
        if "application/json" not in accepted and "*/*" not in accepted:
            raise HTTPException(status_code=406, detail="La cabecera Accept debe incluir 'application/json'")