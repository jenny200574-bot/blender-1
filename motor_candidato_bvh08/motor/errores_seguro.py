"""Errores íntegros, sin credenciales ni cabeceras de autenticación."""
import os,re
class ArgonTransportError(RuntimeError):
 def __init__(self,message,usage_usd=None,retryable=False,log_path=None):
  super().__init__(message);self.usage_usd=usage_usd;self.retryable=retryable;self.log_path=log_path

def mensaje_seguro(exc):
 chain=[];seen=set();current=exc
 while current is not None and id(current) not in seen:
  seen.add(id(current));chain.append(type(current).__name__+': '+str(current));current=current.__cause__ or current.__context__
 text='\nCausa: '.join(chain)
 for name,value in sorted(os.environ.items(),key=lambda x:len(x[1]),reverse=True):
  if re.search(r'KEY|TOKEN|PASSWORD|SECRET',name,re.I) and len(value)>=8:text=text.replace(value,'[SECRETO_OCULTO]')
 text=re.sub(r'-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----','[CLAVE_PRIVADA_OCULTA]',text,flags=re.S)
 text=re.sub(r'(?i)(Bearer\s+)[A-Za-z0-9._~+/-]+=*',r'\1[OCULTO]',text)
 text=re.sub(r"""(?ix)(["']?(?:private_key|access_token|refresh_token|api_key|apikey|password|authorization|x-n8n-api-key)["']?\s*[:=]\s*)(["'])(?:\\.|(?!\2).)*?\2""",lambda m:m.group(1)+'"[OCULTO]"',text)
 text=re.sub(r'(?i)([?&](?:key|api_key|token|access_token|auth)=)[^&\s]+',r'\1[OCULTO]',text)
 text=re.sub(r'(?i)(https?://)[^\s/@:]+:[^\s/@]+@',r'\1[OCULTO]@',text)
 return text
